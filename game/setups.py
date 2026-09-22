"""Arrange the sandbox for a step: workspaces, tabs, pane layouts, programs in panes.

Layouts are built declaratively with Herdr's `layout.apply`:

    reset(c, tabs=[("main", R(P("A"), D(P("B"), P("C"))))])

gives one workspace with a tab "main": pane A on the left, B over C on the right.
"""
import os
import shlex
import time

from . import paths

HOME = os.path.expanduser("~")


# ------------------------------------------------------------------ layout nodes

def P(label=None, prog=None, *args, cwd=None):
    """A pane. `prog` runs one of the game's pane programs (panes.py) before the shell."""
    node = {"type": "pane", "cwd": cwd or HOME}
    if label:
        node["label"] = label
    if prog:
        node["command"] = [os.path.join(paths.BIN, "hl-pane"), prog] + [str(a) for a in args]
    return node


def R(first, second, ratio=0.5):
    """Split side by side: `first` on the left, `second` on the right."""
    return {"type": "split", "direction": "right", "ratio": ratio, "first": first, "second": second}


def D(first, second, ratio=0.5):
    """Split stacked: `first` on top, `second` below."""
    return {"type": "split", "direction": "down", "ratio": ratio, "first": first, "second": second}


def row(*panes):
    """Several panes side by side, evenly."""
    if len(panes) == 1:
        return panes[0]
    return R(panes[0], row(*panes[1:]), ratio=1 / len(panes))


def col(*panes):
    if len(panes) == 1:
        return panes[0]
    return D(panes[0], col(*panes[1:]), ratio=1 / len(panes))


def grid(labels=(None, None, None, None)):
    a, b, cc, d = labels
    return R(D(P(a), P(cc)), D(P(b), P(d)))


# ------------------------------------------------------------------ helpers

def snap(c):
    c.s = c.engine.refresh() if c.engine else c.s
    return c.s


def settle(c, secs=0.15):
    time.sleep(secs)
    return snap(c)


def build(c, ws_label, tabs, focus=True):
    """Create a workspace with these tabs [(label, node)]. Returns (ws_id, [tab ids])."""
    h = c.herdr
    r = h.call("workspace.create", label=ws_label, cwd=HOME, focus=focus)
    ws = r["workspace"]["workspace_id"]
    first = r["tab"]["tab_id"]
    tab_ids = []
    for i, (label, node) in enumerate(tabs or [(None, None)]):
        if i == 0:
            if node is None or node.get("type") == "pane" and not node.get("label") and not node.get("command"):
                if label:
                    h.call("tab.rename", tab_id=first, label=label)
                tab_ids.append(first)
                continue
            lr = h.call("layout.apply", tab_id=first, tab_label=label, focus=focus, root=node)
        else:
            lr = h.call("layout.apply", workspace_id=ws, tab_label=label, focus=False,
                        root=node or P())
        tab_ids.append(lr["layout"]["tab_id"])
    if focus and tab_ids:
        h.try_call("tab.focus", tab_id=tab_ids[0])
    return ws, tab_ids


def reset(c, label="home", tabs=None, extra=(), focus_pane=None, keep=()):
    """A fresh sandbox: one workspace `label` (plus `extra` workspaces [(label, tabs)]),
    every other workspace closed. Returns {"ws": id, "tabs": [ids], "extra": [(ws, tabs)]}."""
    h = c.herdr
    before = h.snapshot_raw() or {"workspaces": []}
    ws, tab_ids = build(c, label, tabs)
    extras = [build(c, el, et, focus=False) for el, et in extra]
    for w in before.get("workspaces", []):
        if w["label"] in keep:
            continue
        if h.try_call("workspace.close", workspace_id=w["workspace_id"]) is None:
            h.try_call("workspace.close", workspace_id=w["workspace_id"], close_group=True)
    h.try_call("workspace.focus", workspace_id=ws)
    settle(c, 0.2)
    if focus_pane:
        select(c, focus_pane)
    ensure_sidebar(c)
    info = {"ws": ws, "tabs": tab_ids, "extra": extras}
    c.mem["setup"] = info
    return info


def ensure_sidebar(c):
    """Setups assume the sidebar is open; a player who collapsed it gets it back."""
    s = snap(c)
    w = s.sidebar_width() if s else None
    if w is not None and w < 12 and c.engine:
        c.engine.press("prefix", "b")
        settle(c, 0.3)


def pane_id(c, which):
    """A pane in the focused tab: by label, by corner (tl/tr/bl/br), "left"/"right", or index."""
    s = snap(c)
    t = s.tab
    if not t or not t.panes:
        return None
    if isinstance(which, int):
        order = t.order()
        return order[which % len(order)]
    if which in ("tl", "tr", "bl", "br"):
        return t.corner(which).id
    if which == "left":
        return t.leftmost().id
    if which == "right":
        return t.rightmost().id
    p = t.by_label(which) or s.pane_labelled(which)
    return p.id if p else which


def select(c, which):
    pid = pane_id(c, which)
    if pid:
        c.herdr.try_call("pane.focus", pane_id=pid)
    return settle(c, 0.1)


def type_in(c, which, text, enter=True):
    pid = pane_id(c, which)
    c.herdr.try_call("pane.send_input", pane_id=pid, text=text, keys=["enter"] if enter else [])


def run_prog(c, which, prog, *args):
    """Run a pane program in an existing shell pane (the command line is cleared first)."""
    cmd = " ".join(shlex.quote(str(a)) for a in [os.path.join(paths.BIN, "hl-run"), prog, *args])
    type_in(c, which, " clear; " + cmd)


def agent(c, pane, name, state, message=None):
    """Report a pretend agent's state for a pane (what agent integrations do for real)."""
    c.herdr.try_call("pane.report_agent", pane_id=pane, source="custom:herdling", agent=name, state=state,
                     message=message)
