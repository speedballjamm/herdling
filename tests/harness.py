"""Run the real game inside an 'outer' tmux, so tests can type real keystrokes into it
and capture exactly what the player would see (HUD, cards and all).

Each game gets its own HERDLING_HOME under /tmp (short, because Herdr's socket path
must fit in ~104 bytes), so its Herdr sandbox is separate from everything else.
"""
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def clip_get():
    if shutil.which("pbpaste"):
        return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
    return None


def clip_set(text):
    if text is not None and shutil.which("pbcopy"):
        subprocess.run(["pbcopy"], input=text, text=True)


class Game:
    def __init__(self, name, args=("play",), cols=120, rows=40, home=None, env=None, clipboard=False):
        self.name = name
        # copy missions overwrite the system clipboard; those games put it back afterwards
        self._clip = clip_get() if clipboard else None
        self.outer = f"hl-outer-{name}"
        self.home = home or tempfile.mkdtemp(prefix=f"hl-{name}-", dir="/tmp")
        self._own_home = home is None
        self.run_outer("kill-server")
        self.real_conf = os.path.join(self.home, "real-config.toml")
        # a plain shell with no history file, so test runs stay out of your own shell history
        env = {"HERDLING_SHELL": "/bin/sh", "HISTFILE": "/dev/null", **(env or {})}
        extra = " ".join(f"{k}={v}" for k, v in env.items())
        cmd = (f"env -u TMUX -u HERDR_ENV HERDLING_HOME={self.home} HERDLING_REAL_CONF={self.real_conf} {extra} "
               f"{ROOT}/herdling {' '.join(args)}; sleep 30")
        self.run_outer("-f", "/dev/null", "new-session", "-d", "-x", str(cols), "-y", str(rows), cmd)
        self.run_outer("set", "-g", "status", "off")
        self.run_outer("set", "-g", "escape-time", "0")

    # --- plumbing
    def run_outer(self, *a):
        return subprocess.run(["tmux", "-L", self.outer, *a], capture_output=True, text=True)

    @property
    def sock(self):
        return os.path.join(self.home, "x", "herdr", "herdr.sock")

    def call(self, method, **params):
        s = socket.socket(socket.AF_UNIX)
        s.settimeout(3)
        s.connect(self.sock)
        s.sendall((json.dumps({"id": "t", "method": method, "params": params}) + "\n").encode())
        buf = b""
        while not buf.endswith(b"\n"):
            d = s.recv(1 << 20)
            if not d:
                break
            buf += d
        s.close()
        msg = json.loads(buf)
        if "error" in msg:
            raise RuntimeError(msg["error"])
        return msg["result"]

    def snap(self):
        return self.call("session.snapshot")["snapshot"]

    def focused_tab(self):
        s = self.snap()
        return next(t for t in s["tabs"] if t["tab_id"] == s["focused_tab_id"])

    def layout(self):
        s = self.snap()
        return next(l for l in s["layouts"] if l["tab_id"] == s["focused_tab_id"])

    def layout_of(self, tab_id):
        return next(l for l in self.snap()["layouts"] if l["tab_id"] == tab_id)

    def pane_ids(self):
        return [p["pane_id"] for p in self.layout()["panes"]]

    def focused_pane(self):
        s = self.snap()
        return next(p for p in s["panes"] if p["pane_id"] == s["focused_pane_id"])

    def read(self, pane_id, lines=300):
        return self.call("pane.read", pane_id=pane_id, source="recent_unwrapped", lines=lines)["read"]["text"]

    # --- input
    def keys(self, *keys, delay=0.25):
        for k in keys:
            self.run_outer("send-keys", "-t", ":0.0", "\\;" if k == ";" else k)
            time.sleep(delay)

    def prefix(self, key, delay=0.3):
        """Press ctrl+b then key."""
        self.keys("C-b", delay=0.15)
        self.keys(key, delay=delay)

    def type(self, text, enter=True, delay=0.3):
        self.run_outer("send-keys", "-t", ":0.0", "-l", text)
        if enter:
            time.sleep(0.05)
            self.run_outer("send-keys", "-t", ":0.0", "Enter")
        time.sleep(delay)

    def cmd(self, text, delay=0.8):
        """Type a shell command in the focused pane."""
        self.type(text, delay=delay)

    def raw(self, data, delay=0.3):
        self.run_outer("send-keys", "-t", ":0.0", "-l", data)
        time.sleep(delay)

    def paste(self, text):
        """Type `text` the way a terminal paste arrives (bracketed paste)."""
        self.raw(f"\x1b[200~{text}\x1b[201~")

    def clipboard(self):
        return clip_get() or ""

    def pane_labelled(self, label):
        for p in self.snap()["panes"]:
            if p.get("label") == label:
                return p["pane_id"]
        return None

    def agents(self):
        return {a["agent"]: a for a in self.snap()["agents"]}

    def click(self, x, y, button=0):
        """SGR mouse press + release at 1-based cell x, y."""
        self.raw(f"\x1b[<{button};{x};{y}M\x1b[<{button};{x};{y}m")

    def drag(self, x1, y1, x2, y2):
        self.raw(f"\x1b[<0;{x1};{y1}M", delay=0.05)
        steps = max(abs(x2 - x1), abs(y2 - y1), 1)
        for i in range(1, steps + 1):
            x = x1 + (x2 - x1) * i // steps
            y = y1 + (y2 - y1) * i // steps
            self.raw(f"\x1b[<32;{x};{y}M", delay=0.02)
        self.raw(f"\x1b[<0;{x2};{y2}m")

    # --- output
    def screen(self):
        return self.run_outer("capture-pane", "-p", "-t", ":0.0").stdout

    def hud(self):
        lines = self.screen().rstrip("\n").split("\n")
        return "\n".join(lines[-3:])

    def runtime(self):
        try:
            with open(os.path.join(self.home, "run", "runtime.json")) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def title(self):
        return self.runtime().get("title", "")

    def progress(self):
        try:
            with open(os.path.join(self.home, "progress.json")) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def stars(self, mid):
        return self.progress().get("missions", {}).get(mid, {}).get("stars", 0)

    def engine_log(self):
        try:
            with open(os.path.join(self.home, "engine.log")) as f:
                return f.read()
        except OSError:
            return ""

    def send_event(self, event):
        event["t"] = time.time()
        with open(os.path.join(self.home, "run", "events.jsonl"), "a") as f:
            f.write(json.dumps(event) + "\n")

    def answer(self, text):
        self.send_event({"type": "answer", "text": text})

    # --- waiting
    def wait(self, pred, timeout=15, what="condition"):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if pred():
                    return True
            except Exception:
                pass
            time.sleep(0.15)
        raise AssertionError(f"[{self.name}] timed out waiting for {what}\nTITLE: {self.title()}\n"
                             f"SCREEN:\n{self.screen()}\nLOG:\n{self.engine_log()[-2500:]}")

    def wait_title(self, text, timeout=15):
        return self.wait(lambda: text in self.title(), timeout, f"title to contain {text!r}")

    def wait_screen(self, text, timeout=15):
        return self.wait(lambda: text in self.screen(), timeout, f"screen to contain {text!r}")

    def wait_hud(self, text, timeout=15):
        return self.wait(lambda: text in self.hud(), timeout, f"HUD to contain {text!r}")

    def wait_done(self, mid, timeout=20):
        return self.wait(lambda: self.stars(mid) > 0, timeout, f"mission {mid} to complete")

    def close_card(self, timeout=12):
        self.wait_screen("Enter to continue", timeout)
        time.sleep(0.2)
        self.keys("Enter", delay=0.6)

    def close(self):
        try:
            self.run_outer("kill-server")
        finally:
            # stop every Herdr server in this game's sandbox
            env = dict(os.environ, XDG_CONFIG_HOME=os.path.join(self.home, "x"))
            env.pop("HERDR_SOCKET_PATH", None)
            try:
                out = subprocess.run(["herdr", "session", "list", "--json"], env=env, capture_output=True,
                                     text=True, timeout=5).stdout
                for s in json.loads(out).get("sessions", []):
                    if s.get("running"):
                        subprocess.run(["herdr", "session", "stop", s["name"]], env=env, capture_output=True,
                                       timeout=5)
            except Exception:
                pass
            if self._own_home:
                shutil.rmtree(self.home, ignore_errors=True)
            clip_set(self._clip)
