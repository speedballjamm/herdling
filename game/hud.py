"""The heads-up display: three lines the launcher reserves under Herdr.

    ▶ 1.2 Stacked │ Split this pane top / bottom:  prefix+minus        ← mission
      (continuation when the prompt doesn't fit)                     ← mission, line 2
                                                     (or a long message's first half)
    MODE ✔ feedback / hints                      Lost Lamb · 340 XP   ← messages

Herdr is told the terminal is three rows shorter, so it never draws here.
"""
import threading

from . import markup

ROWS = 3

A = "\x1b[0;38;5;255;48;5;24m"        # mission lines
B = "\x1b[0;38;5;252;48;5;236m"       # message line
MSG = {
    "": B,
    "ok": "\x1b[0;38;5;16;48;5;78m",
    "bad": "\x1b[0;38;5;255;48;5;131m",
    "hint": "\x1b[0;38;5;16;48;5;222m",
    "info": "\x1b[0;38;5;16;48;5;117m",
}
ICONS = {"ok": "✔ ", "bad": "✘ ", "hint": "» ", "info": "• "}
BADGE = "\x1b[0;1;38;5;16;48;5;214m"
# Only modes with a clear way out get a badge, so a guess never lingers on screen.
MODE_NAMES = {"prefix": "PREFIX", "copy": "COPY", "resize": "RESIZE", "navigate": "NAVIGATE"}


class Hud:
    def __init__(self):
        self.lock = threading.Lock()
        self.title = ""
        self.prompt = ""
        self.msg = ""
        self.kind = ""
        self.right = ""
        self.mode = "terminal"
        self.version = 0
        self.listeners = []

    def set(self, title=None, prompt=None, right=None, msg=None, kind="", mode=None):
        with self.lock:
            if title is not None:
                self.title = title
            if prompt is not None:
                self.prompt = prompt
            if right is not None:
                self.right = right
            if msg is not None:
                self.msg, self.kind = msg, kind
            if mode is not None:
                self.mode = mode
            self.version += 1
        for fn in list(self.listeners):
            fn()

    def lines(self, cols):
        """The three rendered rows, each exactly `cols` wide."""
        with self.lock:
            title, prompt, msg, kind, right, mode = (self.title, self.prompt, self.msg, self.kind,
                                                     self.right, self.mode)
        if title:
            head = f"{A}\x1b[1m ▶ {title} \x1b[22m│ "
            head_w = markup.width(f" ▶ {title} │ ")
        else:
            head, head_w = f"{A} ", 1
        first, rest = markup.wrap(prompt, max(20, cols - head_w - 1))
        l1 = head + markup.to_ansi(first, A)
        l2 = A + " " * min(head_w, 14) + markup.to_ansi(rest, A) if rest else A
        badge = ""
        if mode in MODE_NAMES:
            badge = f"{BADGE} {MODE_NAMES[mode]} {B}"
        style = MSG.get(kind, B)
        icon = ICONS.get(kind, "")
        body = f"{style} {icon}{markup.to_ansi(msg, style)} {B}" if msg else ""
        right_s = markup.to_ansi(right, B) + " " if right else ""
        left = B + badge + body
        room = cols - markup.width(right_s)
        if msg and not rest and markup.width(left) > room - 1:
            # A long message borrows the mission's empty second row rather than being cut off.
            lead = markup.width(badge) + 1 + markup.width(icon)
            top, more = markup.wrap(msg, max(20, cols - lead - 1))
            if more:
                l2 = f"{B}{badge}{style} {icon}{markup.to_ansi(top, style)} {B}"
                left = f"{B}{style}{' ' * lead}{markup.to_ansi(more, style)} {B}"
        if markup.width(left) > room - 1:
            left = markup.fit(left, max(0, room - 2)) + "…" + B
        l3 = left + B + " " * max(0, room - markup.width(left)) + right_s
        return [markup.fit(l1, cols) + markup.RESET, markup.fit(l2, cols) + markup.RESET,
                markup.fit(l3, cols) + markup.RESET]

    def text(self):
        """Plain text of the HUD, for tests and logs."""
        with self.lock:
            return f"{self.title} | {markup.plain(self.prompt)} | {markup.plain(self.msg)} | {self.right}"
