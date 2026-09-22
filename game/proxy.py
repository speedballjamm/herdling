"""Run the Herdr client inside a pseudo-terminal we control.

    your terminal  <──►  proxy  <──►  herdr (client)  <──►  herdr server
                          │
                          ├─ draws the 3-line game HUD under Herdr
                          ├─ shows lesson cards over the whole screen
                          ├─ copies your keystrokes to the key watcher (keyin.py)
                          └─ spots clipboard copies Herdr sends to your terminal (OSC 52)

Every byte passes through unchanged; Herdr is simply told the terminal is three
rows shorter than it really is, and the HUD lives in those rows.
"""
import base64
import fcntl
import os
import pty
import queue
import re
import select
import signal
import struct
import sys
import termios
import threading
import time
import tty

from . import hud as hudmod
from .keyin import Decoder

ALT_RE = re.compile(rb"\x1b\[\?(?:1049|1047|47)([hl])")
SYNC_RE = re.compile(rb"\x1b\[\?2026([hl])")
ERASE_RE = re.compile(rb"\x1b\[[0-3]?J")
OSC52_RE = re.compile(rb"\x1b\]52;[^;\x07\x1b]*;([A-Za-z0-9+/=\s]*)(?:\x07|\x1b\\)")
SEQ_RE = re.compile(rb"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[P_^X][^\x1b]*\x1b\\|[^\[\]P_^X])")
DEBUG = open(os.environ["HERDLING_PROXY_DEBUG"], "a") if os.environ.get("HERDLING_PROXY_DEBUG") else None
TERM_RESET = (b"\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1015l\x1b[?2004l\x1b[?1004l"
              b"\x1b[<u\x1b[?7h\x1b[?25h\x1b[0m")


def term_size(fd=None):
    try:
        rows, cols, _, _ = struct.unpack("HHHH", fcntl.ioctl(fd if fd is not None else sys.stdout.fileno(),
                                                             termios.TIOCGWINSZ, b"\0" * 8))
        if rows and cols:
            return cols, rows
    except OSError:
        pass
    return 100, 30


def set_size(fd, cols, rows):
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


class Proxy:
    def __init__(self, argv, env, hud, on_event=None, cwd=None):
        self.argv = argv
        self.env = env
        self.cwd = cwd
        self.hud = hud
        self.on_event = on_event or (lambda ev: None)
        self.decoder = Decoder()
        self.master = None
        self.pid = None
        self.cols, self.rows = term_size()
        self.alt = False
        self.sync = False
        self.tail = b""
        self.hud_version = -1
        self.last_hud = 0
        self.card = None
        self.card_done = None
        self.cards = queue.Queue()
        self.injects = queue.Queue()
        self.wake_r, self.wake_w = os.pipe()
        self.running = False
        self.started = 0
        self.restore_at = 0
        self.settle_until = 0

    # ------------------------------------------------------------ called from other threads

    @property
    def child_size(self):
        return self.cols, max(5, self.rows - hudmod.ROWS)

    def wake(self):
        try:
            os.write(self.wake_w, b".")
        except OSError:
            pass

    def show_card(self, view, timeout=None):
        """Show a card over the screen; blocks until the player closes it (or Herdr exits)."""
        done = threading.Event()
        self.cards.put((view, done))
        self.wake()
        done.wait(timeout)
        return done.is_set()

    def inject(self, data):
        """Type bytes into Herdr as if the player had pressed them (used by `herdling show`)."""
        self.injects.put(data)
        self.wake()

    def quit(self):
        """End the Herdr client (the server keeps running)."""
        if self.pid and self.running:
            try:
                os.kill(self.pid, signal.SIGTERM)
            except OSError:
                pass

    # ------------------------------------------------------------ main loop

    def run(self):
        stdin = sys.stdin.fileno()
        stdout = sys.stdout.fileno()
        old = termios.tcgetattr(stdin)
        self.cols, self.rows = term_size(stdout)
        pid, master = pty.fork()
        if pid == 0:
            if self.cwd:
                try:
                    os.chdir(self.cwd)
                except OSError:
                    pass
            try:
                os.execvpe(self.argv[0], self.argv, self.env)
            finally:
                os._exit(127)
        self.pid, self.master = pid, master
        set_size(master, *self.child_size)
        prev_winch = signal.signal(signal.SIGWINCH, lambda *a: self.wake())
        self.hud.listeners.append(self.wake)
        self.running = True
        self.started = time.time()
        tty.setraw(stdin)
        status = 0
        try:
            status = self._loop(stdin, stdout, master)
        finally:
            self.running = False
            self.hud.listeners.remove(self.wake)
            signal.signal(signal.SIGWINCH, prev_winch)
            os.write(stdout, TERM_RESET + (b"\x1b[?1049l" if self.alt else b""))
            termios.tcsetattr(stdin, termios.TCSADRAIN, old)
            try:
                os.close(master)
            except OSError:
                pass
            if self.card_done:
                self.card_done.set()
            while not self.cards.empty():
                self.cards.get()[1].set()
        return status

    def _loop(self, stdin, stdout, master):
        while True:
            timeout = 0.05 if self.decoder.buf or self.restore_at else 0.5
            try:
                r, _, _ = select.select([stdin, master, self.wake_r], [], [], timeout)
            except InterruptedError:
                r = []
            if self.wake_r in r:
                try:
                    os.read(self.wake_r, 4096)
                except OSError:
                    pass
            if master in r:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    data = b""
                if not data:
                    _, st = os.waitpid(self.pid, 0)
                    return os.waitstatus_to_exitcode(st) if hasattr(os, "waitstatus_to_exitcode") else st
                self._output(stdout, data)
            if stdin in r:
                try:
                    data = os.read(stdin, 65536)
                except OSError:
                    data = b""
                if data:
                    self._input(master, stdout, data)
            elif self.decoder.buf:
                for ev in self.decoder.flush():
                    self.on_event(ev)
            self._housekeeping(stdout, master)

    def _housekeeping(self, stdout, master):
        cols, rows = term_size(stdout)
        if (cols, rows) != (self.cols, self.rows):
            self.cols, self.rows = cols, rows
            set_size(master, *self.child_size)
            if self.card:
                os.write(stdout, self.card.render(cols, rows).encode())
        if self.restore_at and time.time() >= self.restore_at:
            self.restore_at = 0
            set_size(master, *self.child_size)
        while not self.injects.empty():
            os.write(master, self.injects.get())
        if self.card is None and not self.cards.empty():
            self.card, self.card_done = self.cards.get()
            os.write(stdout, self.card.render(self.cols, self.rows).encode())
        if DEBUG and time.time() - self.last_hud > 2:
            DEBUG.write(f"{time.time():.1f} no hud: card={bool(self.card)} alt={self.alt} sync={self.sync} "
                        f"tail={self.tail[:40]!r}\n")
            DEBUG.flush()
        if self.card is None and self.alt and not self.sync and not self.tail:
            now = time.time()
            if self.hud.version != self.hud_version or now - self.last_hud > 1.0:
                self.draw_hud(stdout)

    # ------------------------------------------------------------ data paths

    def _input(self, master, stdout, data):
        if self.card:
            if self.card.feed(data):
                self.card = None
                self.card_done.set()
                self.card_done = None
                self.repaint(stdout, master)
            else:
                os.write(stdout, self.card.render(self.cols, self.rows).encode())
            return
        os.write(master, data)
        for ev in self.decoder.feed(data):
            self.on_event(ev)

    def _output(self, stdout, data):
        if not self.card:   # while a card owns the screen, Herdr repaints when it closes
            os.write(stdout, data)
        buf = self.tail + data
        erased = False
        for m in ALT_RE.finditer(buf):
            self.alt = m.group(1) == b"h"
            erased = True
        for m in SYNC_RE.finditer(buf):
            self.sync = m.group(1) == b"h"
        if ERASE_RE.search(buf):
            erased = True
        for m in OSC52_RE.finditer(buf):
            try:
                text = base64.b64decode(re.sub(rb"\s", b"", m.group(1))).decode("utf-8", "replace")
            except ValueError:
                text = ""
            self.on_event(("copy", text))
        j = buf.rfind(b"\x1b")
        if j >= 0 and not SEQ_RE.match(buf, j):
            self.tail = buf[j:] if len(buf) - j < (1 << 20) else b""
        else:
            self.tail = b""
        if erased:
            self.hud_version = -1

    def repaint(self, stdout, master):
        """Make Herdr redraw the whole screen: shrink it by a row for a moment.
        (Pane sizes wobble briefly; the engine ignores geometry until `settle_until`.)"""
        os.write(stdout, b"\x1b[0m\x1b[2J")
        cols, rows = self.child_size
        set_size(master, cols, rows - 1)
        self.restore_at = time.time() + 0.08
        self.settle_until = time.time() + 0.8
        self.hud_version = -1

    def draw_hud(self, stdout):
        self.hud_version = self.hud.version
        self.last_hud = time.time()
        cols, rows = self.cols, self.rows
        top = rows - hudmod.ROWS + 1
        parts = ["\x1b[?2026h\x1b7"]
        for i, line in enumerate(self.hud.lines(cols)):
            parts.append(f"\x1b[{top + i};1H{line}")
        parts.append("\x1b8\x1b[?2026l")
        os.write(stdout, "".join(parts).encode())
