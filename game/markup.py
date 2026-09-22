"""Tiny markup shared by the HUD and lesson cards.

    `prefix+v`  -> a key chip
    **text**    -> bold

Keys are written the way Herdr's own help (prefix+?) writes them, so what you
learn here matches what you'll see in the app.
"""
import re
import unicodedata

CHIP = re.compile(r"`([^`]+)`")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
ANSI = re.compile(r"\x1b\[[0-9;]*m")

RESET = "\x1b[0m"
CHIP_STYLE = "\x1b[1;38;5;16;48;5;214m"


def to_ansi(text, base=""):
    """Render markup as ANSI. `base` is the SGR the surrounding text uses (re-applied after chips)."""
    text = CHIP.sub(lambda m: f"{CHIP_STYLE} {m.group(1)} {RESET}{base}", text)
    text = BOLD.sub(lambda m: f"\x1b[1m{m.group(1)}\x1b[22m", text)
    return text


def plain(text):
    return BOLD.sub(r"\1", CHIP.sub(r"\1", text))


def char_width(ch):
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def width(s):
    """Display width of a string that may contain SGR escapes."""
    return sum(char_width(c) for c in ANSI.sub("", s))


def visible_len(raw):
    """Width of marked-up text once rendered (chips get a space either side)."""
    return width(plain(CHIP.sub(lambda m: f" {m.group(1)} ", raw)))


TOKEN = re.compile(r"`[^`]+`|\*\*[^*]+\*\*|\S+|\s+")


def wrap(raw, w):
    """Split marked-up text into (first, rest) at a word boundary, never inside markup."""
    if visible_len(raw) <= w:
        return raw, ""
    used, cut = 0, 0
    toks = TOKEN.findall(raw)
    for i, tok in enumerate(toks):
        tw = visible_len(tok)
        if used + tw > w:
            break
        used += tw
        if tok.isspace():
            cut = i
    if cut == 0:
        return raw, ""
    return "".join(toks[:cut]), "".join(toks[cut:]).strip()


def fit(s, w):
    """Truncate an ANSI string to display width w (keeping escapes), then pad with spaces."""
    out, used, i = [], 0, 0
    while i < len(s):
        m = ANSI.match(s, i)
        if m:
            out.append(m.group(0))
            i = m.end()
            continue
        cw = char_width(s[i])
        if used + cw > w:
            break
        out.append(s[i])
        used += cw
        i += 1
    return "".join(out) + " " * (w - used)
