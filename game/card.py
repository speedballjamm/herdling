"""Lesson cards: drawn full-screen by the proxy while Herdr waits underneath."""
from . import markup
from .keyin import Decoder

TITLE = "\x1b[0;1;38;5;255;48;5;24m"
BOX = "\x1b[0;38;5;24m"
BODY = "\x1b[0;38;5;252m"
DIM = "\x1b[0;38;5;244m"
R = "\x1b[0m"

NEXT = {"space", "down", "j", "pagedown"}
PREV = {"up", "k", "pageup"}
DONE = {"enter", "q", "esc", "ctrl+c"}


class CardView:
    def __init__(self, card):
        self.title = card["title"]
        self.lines = card["body"].rstrip("\n").split("\n")
        self.pos = 0
        self.page = 10
        self.decoder = Decoder()   # keys may arrive as kitty-protocol sequences while Herdr runs

    def render(self, cols, rows):
        w = min(cols - 2, max(60, max(markup.visible_len(l) for l in self.lines) + 6))
        self.page = max(3, rows - 7)
        x = max(1, (cols - w) // 2 + 1)
        shown = self.lines[self.pos:self.pos + self.page]
        h = len(shown) + 6
        y = max(1, (rows - h) // 2 + 1)
        more = self.pos + self.page < len(self.lines)
        out = ["\x1b[?2026h\x1b[0m\x1b[2J\x1b[?25l"]

        def row(i, text):
            out.append(f"\x1b[{y + i};{x}H{text}")

        row(0, TITLE + markup.fit(f" {self.title}", w) + R)
        row(1, BOX + "│" + " " * (w - 2) + "│")
        for i, line in enumerate(shown):
            row(2 + i, BOX + "│ " + BODY + markup.fit(markup.to_ansi(line, BODY), w - 4) + BOX + " │")
        row(2 + len(shown), BOX + "│" + " " * (w - 2) + "│")
        foot = " Space/↓ more · Enter continue" if more else " Press Enter to continue"
        row(3 + len(shown), BOX + "│" + DIM + markup.fit(foot, w - 2) + BOX + "│")
        row(4 + len(shown), BOX + "└" + "─" * (w - 2) + "┘" + R)
        out.append("\x1b[?2026l")
        return "".join(out)

    def feed(self, data):
        """Handle raw input bytes. True when the card is finished."""
        for kind, *rest in self.decoder.feed(data) + self.decoder.flush():
            if kind != "key":
                continue   # mouse, paste, terminal replies
            key = rest[0]
            more = self.pos + self.page < len(self.lines)
            if more and (key in NEXT or key == "enter"):
                self.pos += self.page - 1
            elif key in PREV and self.pos:
                self.pos = max(0, self.pos - self.page + 1)
            elif key in DONE:
                return True
        return False
