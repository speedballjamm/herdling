"""Watch what the player types, on its way from their terminal to Herdr.

The launcher sits between the terminal and the Herdr client (see proxy.py). It
forwards every byte untouched and also feeds a copy here, so the game can name
the exact keys you press, the way a coach watching over your shoulder would.

Two layers:
  Decoder     bytes -> key / mouse / paste events. Understands legacy terminal
              bytes *and* the kitty keyboard protocol Herdr turns on (CSI u),
              plus SGR mouse reports.
  KeyTracker  key events -> Herdr actions ("prefix+v" -> split_vertical), with a
              best-effort guess at Herdr's current mode (prefix, copy, resize…).
"""
import re

# ---------------------------------------------------------------------------- decoding

CSI_RE = re.compile(rb"\x1b\[([0-?]*)([ -/]*)([@-~])")
SS3_RE = re.compile(rb"\x1bO([@-~])")
MOUSE_RE = re.compile(rb"\x1b\[<(\d+);(\d+);(\d+)([Mm])")
PASTE_END = b"\x1b[201~"

KITTY_CODES = {13: "enter", 9: "tab", 27: "esc", 127: "backspace", 8: "backspace", 32: "space",
               57358: "capslock", 57359: "scrolllock", 57360: "numlock", 57361: "printscreen", 57362: "pause",
               57363: "menu", 57414: "enter", 57399: "0", 57400: "1", 57401: "2", 57402: "3", 57403: "4",
               57404: "5", 57405: "6", 57406: "7", 57407: "8", 57408: "9"}
KITTY_MODIFIER_KEYS = set(range(57441, 57455))   # bare shift/ctrl/alt/super presses
TILDE_KEYS = {1: "home", 2: "insert", 3: "delete", 4: "end", 5: "pageup", 6: "pagedown", 7: "home", 8: "end",
              11: "f1", 12: "f2", 13: "f3", 14: "f4", 15: "f5", 17: "f6", 18: "f7", 19: "f8", 20: "f9",
              21: "f10", 23: "f11", 24: "f12"}
LETTER_KEYS = {"A": "up", "B": "down", "C": "right", "D": "left", "H": "home", "F": "end",
               "P": "f1", "Q": "f2", "R": "f3", "S": "f4", "E": "begin"}
NAMED_CHARS = {"-": "minus", " ": "space", "\t": "tab", "\r": "enter", "\n": "enter"}


def _mods(n):
    """Kitty/xterm modifier parameter -> list of names (caps/num lock ignored)."""
    try:
        n = int(n) - 1
    except ValueError:
        return []
    out = []
    if n & 4:
        out.append("ctrl")
    if n & 2:
        out.append("alt")
    if n & 8:
        out.append("super")
    if n & 1:
        out.append("shift")
    return out


def key_name(char, mods=()):
    """Canonical Herdr-style name: "ctrl+b", "shift+n", "minus", "?", "enter"."""
    mods = list(mods)
    if len(char) == 1:
        if char in NAMED_CHARS:
            char = NAMED_CHARS[char]
        elif char.isalpha() and char.isupper():
            char = char.lower()
            if "shift" not in mods:
                mods.append("shift")
        elif not char.isalnum() and "shift" in mods:
            mods.remove("shift")   # "?" not "shift+?"
    order = [m for m in ("ctrl", "alt", "super", "shift") if m in mods]
    return "+".join(order + [char])


class Decoder:
    def __init__(self):
        self.buf = b""
        self.paste = None

    def feed(self, data):
        """Decode as much as possible; keeps an incomplete tail for next time."""
        self.buf += data
        events = []
        b = self.buf
        i = 0
        n = len(b)
        while i < n:
            if self.paste is not None:
                j = b.find(PASTE_END, i)
                if j < 0:
                    self.paste += b[i:]
                    i = n
                    break
                self.paste += b[i:j]
                events.append(("paste", self.paste.decode("utf-8", "replace")))
                self.paste = None
                i = j + len(PASTE_END)
                continue
            c = b[i]
            if c == 0x1b:
                ev, used = self._escape(b, i)
                if used == 0:          # incomplete: wait for more bytes
                    break
                if ev:
                    events.append(ev)
                i += used
                continue
            if c < 0x20 or c == 0x7f:
                events.append(("key", self._control(c)))
                i += 1
                continue
            # UTF-8 text
            size = 1 if c < 0x80 else 2 if c < 0xe0 else 3 if c < 0xf0 else 4
            if i + size > n:
                break
            ch = b[i:i + size].decode("utf-8", "replace")
            events.append(("key", key_name(ch)))
            i += size
        self.buf = b[i:]
        return events

    def flush(self):
        """Called when input goes quiet: a lone ESC is the Escape key."""
        if self.buf == b"\x1b":
            self.buf = b""
            return [("key", "esc")]
        if self.buf.startswith(b"\x1b") and len(self.buf) > 64:
            self.buf = b""   # garbage; don't let it grow
        return []

    @staticmethod
    def _control(c):
        if c == 0x0d or c == 0x0a:
            return "enter"
        if c == 0x09:
            return "tab"
        if c in (0x7f, 0x08):
            return "backspace"
        if c == 0:
            return "ctrl+space"
        if 1 <= c <= 26:
            return "ctrl+" + chr(c + 96)
        return "ctrl+" + {0x1c: "\\", 0x1d: "]", 0x1e: "^", 0x1f: "_"}.get(c, "?")

    def _escape(self, b, i):
        """Returns (event or None, bytes consumed). consumed == 0 means incomplete."""
        n = len(b)
        if i + 1 >= n:
            return None, 0
        nxt = b[i + 1]
        if nxt == ord("["):
            if b.startswith(b"\x1b[200~", i):
                self.paste = b""
                return None, 6
            m = MOUSE_RE.match(b, i)
            if m:
                return self._mouse(m), m.end() - i
            m = CSI_RE.match(b, i)
            if not m:
                if n - i > 32:
                    return None, 2  # malformed; skip the introducer
                return None, 0
            return self._csi(m.group(1).decode(), m.group(3).decode()), m.end() - i
        if nxt == ord("O"):
            m = SS3_RE.match(b, i)
            if not m:
                return None, 0
            return ("key", LETTER_KEYS.get(m.group(1).decode(), "f?")), 3
        if nxt in (ord("]"), ord("P"), ord("_"), ord("^"), ord("X")):
            # a string reply from the terminal (OSC colour answer, DCS…): skip to ST/BEL
            for term in (b"\x07", b"\x1b\\"):
                j = b.find(term, i + 2)
                if j >= 0:
                    return None, j + len(term) - i
            return None, 0 if n - i < 4096 else n - i
        if nxt == 0x1b:
            return ("key", "esc"), 1
        # ESC + char = Alt/Meta + char
        if nxt < 0x20 or nxt == 0x7f:
            name = self._control(nxt)
            if name.startswith("ctrl+"):
                return ("key", key_name(name[5:], ["ctrl", "alt"])), 2
            return ("key", key_name(name, ["alt"])), 2
        size = 1 if nxt < 0x80 else 2 if nxt < 0xe0 else 3 if nxt < 0xf0 else 4
        if i + 1 + size > n:
            return None, 0
        ch = b[i + 1:i + 1 + size].decode("utf-8", "replace")
        return ("key", key_name(ch, ["alt"])), 1 + size

    @staticmethod
    def _mouse(m):
        code, x, y, final = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
        button = code & 3
        motion = bool(code & 32)
        wheel = bool(code & 64)
        mods = []
        if code & 16:
            mods.append("ctrl")
        if code & 8:
            mods.append("alt")
        if code & 4:
            mods.append("shift")
        if wheel:
            kind = "wheel-up" if button == 0 else "wheel-down"
        elif motion:
            kind = "move" if button == 3 else "drag"
        elif final == b"m":
            kind = "release"
        else:
            kind = "press"
        names = {0: "left", 1: "middle", 2: "right", 3: "none"}
        return ("mouse", {"kind": kind, "button": names[button], "x": x, "y": y, "mods": mods})

    @staticmethod
    def _csi(params, final):
        if params.startswith(("?", ">", "=")):
            return None   # a reply to one of Herdr's queries, not a key
        parts = params.split(";") if params else []
        if final == "u":
            codes = parts[0].split(":") if parts else ["0"]
            modev = parts[1].split(":") if len(parts) > 1 else ["1"]
            if len(modev) > 1 and modev[1] == "3":
                return None   # key release
            try:
                code = int(codes[0] or 0)
            except ValueError:
                return None
            if code in KITTY_MODIFIER_KEYS:
                return None
            mods = _mods(modev[0] or "1")
            shifted = codes[1] if len(codes) > 1 and codes[1] else ""
            if code in KITTY_CODES:
                return ("key", key_name(KITTY_CODES[code], mods))
            try:
                ch = chr(code)
            except ValueError:
                return None
            if "shift" in mods and shifted and not ch.isalpha():
                try:
                    ch = chr(int(shifted))
                except ValueError:
                    pass
            return ("key", key_name(ch, mods))
        if final == "~":
            try:
                num = int(parts[0]) if parts else 0
            except ValueError:
                return None
            mods = _mods(parts[1]) if len(parts) > 1 else []
            if num == 27 and len(parts) > 2:     # xterm modifyOtherKeys: 27;mods;code~
                try:
                    return ("key", key_name(chr(int(parts[2])), mods))
                except ValueError:
                    return None
            name = TILDE_KEYS.get(num)
            return ("key", key_name(name, mods)) if name else None
        if final in ("I", "O") and not parts:
            return ("focus", final == "I")
        if final == "Z":
            return ("key", "shift+tab")
        if final in LETTER_KEYS:
            mods = _mods(parts[1]) if len(parts) > 1 else []
            return ("key", key_name(LETTER_KEYS[final], mods))
        return None


# ---------------------------------------------------------------------------- Herdr's keymap

# Herdr 0.9 default prefix-mode bindings: key after the prefix -> action.
DEFAULT_PREFIX_KEYS = {
    "?": "help", "s": "settings", "q": "detach", "shift+r": "reload_config", "o": "open_notification_target",
    "w": "workspace_picker", "g": "goto", "shift+n": "new_workspace", "shift+g": "new_worktree",
    "shift+w": "rename_workspace", "shift+d": "close_workspace",
    "c": "new_tab", "shift+t": "rename_tab", "p": "previous_tab", "n": "next_tab", "shift+x": "close_tab",
    "shift+p": "rename_pane", "e": "edit_scrollback", "[": "copy_mode", "z": "zoom", "r": "resize_mode",
    "b": "toggle_sidebar", "h": "focus_pane_left", "j": "focus_pane_down", "k": "focus_pane_up",
    "l": "focus_pane_right", "tab": "cycle_pane_next", "shift+tab": "cycle_pane_previous",
    "v": "split_vertical", "minus": "split_horizontal", "x": "close_pane",
    "shift+h": "swap_pane_left", "shift+j": "swap_pane_down", "shift+k": "swap_pane_up", "shift+l": "swap_pane_right",
}
for _i in range(1, 10):
    DEFAULT_PREFIX_KEYS[str(_i)] = f"switch_tab_{_i}"

# Habits from tmux that do something else (or nothing) in Herdr, and what to press instead.
TMUX_HABITS = {
    "%": ("split side by side", "prefix+v"),
    '"': ("split top/bottom", "prefix+minus"),
    "d": ("detach", "prefix+q"),
    ";": ("jump to the last pane", "prefix+tab"),
    "&": ("close the window", "prefix+shift+x"),
    ",": ("rename the window", "prefix+shift+t"),
    "$": ("rename the session", "prefix+shift+w"),
    "!": ("break the pane out", "prefix+c"),
    "space": ("cycle layouts", "prefix+r"),
    "]": ("paste", "your terminal's paste (Cmd+V / Ctrl+Shift+V)"),
    "t": ("show the clock", ""),
    "{": ("swap panes", "prefix+shift+h / l"),
    "left": ("move between panes", "prefix+h / j / k / l (vim-style)"),
    "right": ("move between panes", "prefix+h / j / k / l (vim-style)"),
    "up": ("move between panes", "prefix+h / j / k / l (vim-style)"),
    "down": ("move between panes", "prefix+h / j / k / l (vim-style)"),
    "}": ("swap panes", "prefix+shift+h / l"),
}

# What each action opens, so later keys are read in the right context.
ACTION_MODE = {
    "copy_mode": "copy", "resize_mode": "resize", "workspace_picker": "navigate", "help": "help",
    "goto": "goto", "settings": "settings", "new_tab": "dialog", "rename_tab": "dialog",
    "rename_workspace": "dialog", "rename_pane": "dialog", "close_workspace": "confirm",
    "new_worktree": "dialog",
}


def parse_binding(value):
    """'prefix+shift+n' -> ('prefix', 'shift+n'); 'ctrl+alt+d' -> ('direct', 'ctrl+alt+d')."""
    v = value.strip().lower()
    if v.startswith("prefix+"):
        return "prefix", normalise(v[len("prefix+"):])
    return "direct", normalise(v)


ALIASES = {"escape": "esc", "return": "enter", "-": "minus", "comma": ",", "ampersand": "&", "plus": "+",
           "backtick": "`", "period": ".", "dot": ".", "semicolon": ";", "colon": ":", "slash": "/",
           "backslash": "\\", "question": "?", "equal": "=", "equals": "=", "control": "ctrl", "option": "alt",
           "cmd": "super", "command": "super", "pgup": "pageup", "pgdn": "pagedown", "leftbracket": "[",
           "rightbracket": "]", "apostrophe": "'", "quote": "'", "grave": "`", "tilde": "~"}


def normalise(key):
    """Make config spellings comparable with decoded keys ("ctrl+B" == "ctrl+b", "minus" == "-")."""
    key = key.lower()
    parts = key.split("+") if key != "+" else ["+"]
    if key.endswith("++"):
        parts = key[:-2].split("+") + ["+"]
    parts = [ALIASES.get(p, p) for p in parts if p != ""]
    if not parts:
        return key
    last = parts[-1]
    mods = [ALIASES.get(p, p) for p in parts[:-1]]
    if last == "-":
        last = "minus"
    return key_name(last, mods) if len(last) == 1 else "+".join(
        [m for m in ("ctrl", "alt", "super", "shift") if m in mods] + [last])


class KeyTracker:
    """Turns decoded key events into Herdr actions, tracking Herdr's mode as best it can.

    feed() returns dicts:
      {"kind": "prefix"}                                   the prefix was pressed
      {"kind": "hkey", "key": "prefix+v", "action": "split_vertical", "mode": "terminal"}
      {"kind": "hkey", "key": "prefix+%", "action": None, "habit": (...)}   unbound after prefix
      {"kind": "mkey", "key": "j", "mode": "copy"}          a key pressed inside a Herdr mode
      {"kind": "mode", "mode": "copy", "old": "terminal"}   mode changed
    """

    def __init__(self, prefix="ctrl+b", prefix_keys=None, direct_keys=None):
        self.prefix = normalise(prefix)
        self.prefix_keys = dict(prefix_keys if prefix_keys is not None else DEFAULT_PREFIX_KEYS)
        self.direct_keys = dict(direct_keys or {})
        self.mode = "terminal"
        self.sub = None          # copy mode: "search" / "select"; help: "filter"

    def configure(self, prefix, prefix_keys, direct_keys):
        self.prefix = normalise(prefix)
        self.prefix_keys = prefix_keys
        self.direct_keys = direct_keys

    def _set(self, mode, out):
        if mode != self.mode:
            out.append({"kind": "mode", "mode": mode, "old": self.mode})
            self.mode = mode
            self.sub = None

    def reset(self):
        self.mode = "terminal"
        self.sub = None

    def feed(self, ev):
        out = []
        kind = ev[0]
        if kind == "mouse":
            m = dict(ev[1])
            m["event"] = m.pop("kind")     # press / release / drag / move / wheel-up / wheel-down
            out.append({"kind": "mouse", **m})
            if m["event"] == "press" and self.mode in ("prefix",):
                self._set("terminal", out)
            return out
        if kind == "paste":
            out.append({"kind": "paste", "text": ev[1]})
            return out
        if kind != "key":
            return out
        key = ev[1]
        mode = self.mode
        if mode == "terminal":
            if key == self.prefix:
                self._set("prefix", out)
                out.append({"kind": "prefix"})
            elif key in self.direct_keys:
                act = self.direct_keys[key]
                out.append({"kind": "hkey", "key": key, "action": act, "mode": "terminal"})
                self._set(self._mode_after(act), out)
            else:
                out.append({"kind": "tkey", "key": key})
            return out
        if mode == "prefix":
            if key == "esc":
                out.append({"kind": "hkey", "key": "prefix+esc", "action": "cancel", "mode": "prefix"})
                self._set("terminal", out)
                return out
            if key == self.prefix:
                out.append({"kind": "hkey", "key": "prefix+" + key, "action": "send_prefix", "mode": "prefix"})
                self._set("terminal", out)
                return out
            act = self.prefix_keys.get(key)
            if act is None and key.startswith("ctrl+") and len(key) == 6:
                # Holding Ctrl for the second key too: a classic slip
                out.append({"kind": "hkey", "key": "prefix+" + key, "action": None, "held_ctrl": True,
                            "mode": "prefix"})
                self._set("terminal", out)
                return out
            item = {"kind": "hkey", "key": "prefix+" + key, "action": act, "mode": "prefix"}
            if act is None:
                bare = {"minus": "-", "space": "space"}.get(key, key)
                if bare in TMUX_HABITS:
                    item["habit"] = TMUX_HABITS[bare]
            out.append(item)
            self._set(self._mode_after(act), out)
            return out
        # --- inside a Herdr mode
        if key == self.prefix and mode in ("copy", "resize", "navigate"):
            # the prefix keeps its meaning in copy mode; in the others it's also a way out
            self._set("prefix", out)
            out.append({"kind": "prefix"})
            return out
        out.append({"kind": "mkey", "key": key, "mode": mode, "sub": self.sub})
        if mode == "copy":
            if self.sub == "search":
                if key in ("enter", "esc"):
                    self.sub = None
            elif key in ("/", "?"):
                self.sub = "search"
            elif key in ("v", "space", "shift+v"):
                self.sub = "select"
            elif key in ("y", "enter"):
                if self.sub == "select":
                    self._set("terminal", out)
            elif key == "esc":
                if self.sub:
                    self.sub = None
                else:
                    self._set("terminal", out)
            elif key == "q":
                self._set("terminal", out)
        elif mode == "resize":
            if key in ("esc", "enter", "q"):
                self._set("terminal", out)
        elif mode == "navigate":
            if key in ("esc", "enter") or (len(key) == 1 and key.isdigit()):
                self._set("terminal", out)
        elif mode in ("help", "goto"):
            if self.sub == "filter":
                if key == "enter":
                    self._set("terminal", out)   # goto jumps to the match; help closes
                elif key == "esc":
                    self.sub = None
            elif key == "/":
                self.sub = "filter"
            elif key in ("esc", "enter", "q") and not (mode == "goto" and key == "q"):
                self._set("terminal", out)
        elif mode in ("dialog", "confirm"):
            if key in ("enter", "esc"):
                self._set("terminal", out)
        elif mode == "settings":
            if key in ("esc", "q"):
                self._set("terminal", out)
        return out

    @staticmethod
    def _mode_after(action):
        return ACTION_MODE.get(action, "terminal")

