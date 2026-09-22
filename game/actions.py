"""Compare two snapshots and name what the player did ("split-right", "zoom", …).

Key presses come separately, straight from the key watcher; this module only
looks at Herdr's state, so it also catches things done with the mouse or the CLI.
"""
from dataclasses import dataclass, field


@dataclass
class Action:
    kind: str
    info: dict = field(default_factory=dict)

    def __repr__(self):
        return f"<{self.kind} {self.info}>"


# action kind -> (key id in keys.py, plain-English description)
NARRATION = {
    "split-right": ("split-right", "split: new pane on the right"),
    "split-down": ("split-down", "split: new pane below"),
    "close-pane": ("close-pane", "closed a pane"),
    "focus": ("focus", "moved to another pane"),
    "zoom": ("zoom", "zoomed the pane to fill the tab"),
    "unzoom": ("zoom", "unzoomed"),
    "swap": ("swap", "swapped panes"),
    "resize": ("resize", "resized a split"),
    "rename-pane": ("rename-pane", "renamed a pane"),
    "new-tab": ("new-tab", "new tab"),
    "close-tab": ("close-tab", "closed a tab"),
    "rename-tab": ("rename-tab", "renamed a tab"),
    "switch-tab": ("next-tab", "switched tab"),
    "new-ws": ("new-ws", "new workspace"),
    "close-ws": ("close-ws", "closed a workspace"),
    "rename-ws": ("rename-ws", "renamed a workspace"),
    "switch-ws": ("navigate", "switched workspace"),
    "sidebar": ("sidebar", "toggled the sidebar"),
    "agent": (None, "an agent changed state"),
}


def direction(a, b):
    """Which way is pane rect b from pane rect a?"""
    dx, dy = b.cx - a.cx, b.cy - a.cy
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


def classify(old, new, geometry=True):
    """Actions that turn snapshot `old` into `new`. geometry=False skips size-based ones
    (used while the screen is being repainted and pane sizes wobble)."""
    out = []
    if old is None or new is None:
        return out
    ows = {w.id: w for w in old.workspaces}
    nws = {w.id: w for w in new.workspaces}
    for wid, w in nws.items():
        if wid not in ows:
            out.append(Action("new-ws", {"ws": wid, "label": w.label}))
        elif ows[wid].label != w.label:
            out.append(Action("rename-ws", {"ws": wid, "old": ows[wid].label, "new": w.label}))
    for wid, w in ows.items():
        if wid not in nws:
            out.append(Action("close-ws", {"ws": wid, "label": w.label}))
    if old.fws != new.fws and new.fws in ows:
        out.append(Action("switch-ws", {"old": old.fws, "new": new.fws}))

    for tid, t in new.tabs.items():
        ot = old.tabs.get(tid)
        if ot is None:
            if t.ws in ows:
                out.append(Action("new-tab", {"tab": tid, "ws": t.ws, "label": t.label}))
            continue
        if ot.label != t.label:
            out.append(Action("rename-tab", {"tab": tid, "old": ot.label, "new": t.label}))
        if ot.zoomed != t.zoomed:
            out.append(Action("zoom" if t.zoomed else "unzoom", {"tab": tid}))
        old_ids = {p.id for p in ot.panes}
        new_ids = {p.id for p in t.panes}
        added, gone = new_ids - old_ids, old_ids - new_ids
        if added:
            for d in ("right", "down"):
                if t.count(d) > ot.count(d):
                    out.append(Action(f"split-{d}", {"tab": tid, "pane": sorted(added)[0]}))
                    break
            else:
                out.append(Action("pane-added", {"tab": tid}))
        for pid in gone:
            out.append(Action("close-pane", {"tab": tid, "pane": pid}))
        if geometry and not added and not gone and len(t.panes) > 1:
            orect = {p.id: (p.rect.x, p.rect.y) for p in ot.panes}
            nrect = {p.id: (p.rect.x, p.rect.y) for p in t.panes}
            if sorted(orect.values()) == sorted(nrect.values()) and orect != nrect:
                out.append(Action("swap", {"tab": tid}))
            elif [round(s.ratio, 3) for s in ot.splits] != [round(s.ratio, 3) for s in t.splits] and \
                    [s.direction for s in ot.splits] == [s.direction for s in t.splits]:
                out.append(Action("resize", {"tab": tid}))
        if ot.focused_pane != t.focused_pane and t.focused_pane in old_ids and ot.focused_pane in new_ids:
            a, b = t.pane(ot.focused_pane), t.pane(t.focused_pane)
            out.append(Action("focus", {"tab": tid, "old": ot.focused_pane, "new": t.focused_pane,
                                        "dir": direction(a.rect, b.rect) if a and b else None}))
    for tid, t in old.tabs.items():
        if tid not in new.tabs and t.ws in nws:
            out.append(Action("close-tab", {"tab": tid, "ws": t.ws, "label": t.label}))
    if old.ftab != new.ftab and old.fws == new.fws and new.ftab in old.tabs:
        out.append(Action("switch-tab", {"old": old.ftab, "new": new.ftab}))

    for pid, p in new.panes.items():
        op = old.panes.get(pid)
        if op is None:
            continue
        if op.label != p.label:
            out.append(Action("rename-pane", {"pane": pid, "old": op.label, "new": p.label}))
        if op.status != p.status and (p.agent or op.agent):
            out.append(Action("agent", {"pane": pid, "old": op.status, "new": p.status, "agent": p.agent}))
        if op.scroll != p.scroll:
            out.append(Action("scroll", {"pane": pid, "old": op.scroll, "new": p.scroll}))

    if geometry and old.cols and old.cols == new.cols:
        ow, nw = old.sidebar_width(), new.sidebar_width()
        if ow is not None and nw is not None and old.ftab == new.ftab and abs(ow - nw) > 2:
            out.append(Action("sidebar", {"open": nw > ow, "width": nw}))
    return out
