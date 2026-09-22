"""Shared building blocks for mission files."""
import random
import re
import shutil
import subprocess
import time

from ..model import Mission, Step, World  # noqa: F401  (re-exported for world files)
from ..setups import (D, P, R, agent, col, ensure_sidebar, grid, pane_id, reset, row, run_prog,  # noqa: F401
                      select, settle, snap, type_in)

WORDS = ["ORCA", "LYNX", "OTTER", "FALCON", "BADGER", "HERON", "IBEX", "MARTEN", "OCELOT", "PUFFIN",
         "TAPIR", "WOMBAT", "GECKO", "KESTREL", "NARWHAL", "QUOKKA", "ALPACA", "BISON", "LLAMA", "YAK"]


# --- quick state readers -------------------------------------------------------

def tab(c):
    return c.s.tab


def npanes(c):
    t = c.s.tab
    return len(t.panes) if t else 0


def active(c):
    return c.s.pane


def active_id(c):
    return c.s.fpane


def label_of(c):
    p = c.s.pane
    return p.label if p else None


def ws(c):
    return c.s.ws


def ws_names(c):
    return [w.label for w in c.s.workspaces]


def tab_names(c, w=None):
    w = w or c.s.ws
    return [t.label for t in w.tabs] if w else []


def cur_tab_name(c):
    t = c.s.tab
    return t.label if t else None


def cur_ws_name(c):
    w = c.s.ws
    return w.label if w else None


def focused_label(c, label):
    p = c.s.pane
    return bool(p and p.label == label)


def corner_is(which):
    return lambda c: bool(tab(c) and not tab(c).zoomed and len(tab(c).panes) > 1
                          and active_id(c) == tab(c).corner(which).id)


def lines_of(text):
    return [l.rstrip() for l in text.splitlines()]


def pane_has_line(c, pid, text):
    return any(l.strip() == text for l in lines_of(c.read(pid)))


def pane_contains(c, pid, text):
    return text in c.read(pid)


def answered(c, expected, strip=("SECRET:", "CODE:")):
    a = c.answer()
    if a is None:
        return False
    got = a.strip().upper()
    for s in strip:
        got = got.replace(s, "").strip()
    if got == expected.upper():
        return True
    c.say(f"'{a}' isn't it. Look again!")
    return False


def rand_code(prefix=""):
    return f"{prefix}{random.choice(WORDS)}-{random.randint(100, 999)}"


_clip = {"t": 0, "text": ""}


def clipboard():
    """The system clipboard's text (Herdr copies there on macOS; elsewhere it may use OSC 52)."""
    now = time.time()
    if now - _clip["t"] < 0.4:
        return _clip["text"]
    for argv in (["pbpaste"], ["wl-paste", "--no-newline"], ["xclip", "-selection", "clipboard", "-o"],
                 ["xsel", "--clipboard", "--output"]):
        if shutil.which(argv[0]):
            try:
                _clip["text"] = subprocess.run(argv, capture_output=True, text=True, timeout=2).stdout
            except (OSError, subprocess.TimeoutExpired):
                continue
            break
    _clip["t"] = now
    return _clip["text"]


def copied_has(c, text):
    """Did the player copy `text`? (seen in a terminal clipboard write, or on the clipboard)"""
    return any(text in t for t in c.copied()) or text in clipboard()


# --- common setups ------------------------------------------------------------------

def fresh(c):
    reset(c)


def panes_right(n, sel=None, labels=None):
    """n panes side by side (optionally labelled)."""
    def setup(c):
        ls = labels or [None] * n
        reset(c, tabs=[(None, row(*[P(l) for l in ls]))], focus_pane=sel)
    return setup


def panes_down(n, sel=None, labels=None):
    def setup(c):
        ls = labels or [None] * n
        reset(c, tabs=[(None, col(*[P(l) for l in ls]))], focus_pane=sel)
    return setup


def quad(sel=None, labels=(None, None, None, None)):
    def setup(c):
        reset(c, tabs=[(None, grid(labels))], focus_pane=sel)
    return setup


def tabs_setup(*labels, active=0, tags=True, ws_label="home"):
    """One workspace with these tabs; `tags` puts a big name tag in each so switching is visible."""
    def setup(c):
        tabs = [(l, P(None, "label", f"TAB {i + 1}: {l}") if tags else P()) for i, l in enumerate(labels)]
        info = reset(c, label=ws_label, tabs=tabs)
        c.herdr.try_call("tab.focus", tab_id=info["tabs"][active])
        c.mem["tabs"] = info["tabs"]
        settle(c)
    return setup


def spaces_setup(*labels, active=0, tags=True):
    """Several workspaces; each gets a name tag."""
    def setup(c):
        def tabs(l):
            return [(None, P(None, "label", f"SPACE: {l}") if tags else P())]
        reset(c, label=labels[active], tabs=tabs(labels[active]),
                     extra=[(l, tabs(l)) for i, l in enumerate(labels) if i != active])
        # put the workspaces in the listed order
        s = snap(c)
        order = [s.workspace_named(l).id for l in labels if s.workspace_named(l)]
        c.herdr.try_call("workspace.move_block", workspace_ids=order)
        c.herdr.try_call("workspace.focus", workspace_id=s.workspace_named(labels[active]).id)
        settle(c)
    return setup


def chain(*fns):
    def setup(c):
        for f in fns:
            f(c)
    return setup


def did_key(*herdr_actions):
    """Goal helper: the player pressed a key for one of these Herdr actions."""
    return lambda c: c.pressed(*herdr_actions)


def norm_name(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())
