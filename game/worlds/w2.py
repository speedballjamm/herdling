from .common import Mission, P, R, Step, World, active_id, fresh, npanes, panes_right, reset, tab


def ratio(c):
    t = tab(c)
    return t.splits[0].ratio if t and t.splits else 0.5


def in_mode(c, mode):
    return c.tracker_mode() == mode


def a_left_of_b(c):
    t = tab(c)
    a, b = (t.by_label("A"), t.by_label("B")) if t else (None, None)
    return bool(a and b) and a.rect.x < b.rect.x


def sidebar_open(c):
    w = c.s.sidebar_width()
    return w is not None and w >= 12


def sidebar_closed(c):
    w = c.s.sidebar_width()
    return w is not None and w < 12


def blueprint_shape(c):
    """One pane down the whole left side, three stacked on the right."""
    t = tab(c)
    if not t or len(t.panes) != 4:
        return False
    left = t.leftmost()
    rest = [p for p in t.panes if p.id != left.id]
    return (left.rect.h == t.area.h or left.rect.y == 0 and left.rect.bottom >= t.area.h - 1) and \
        len({p.rect.x for p in rest}) == 1 and rest[0].rect.x > left.rect.x and len({p.rect.y for p in rest}) == 3


def left_wide(c):
    t = tab(c)
    return blueprint_shape(c) and t.leftmost().rect.w > t.area.w * 0.55


def zoomed_br(c):
    t = tab(c)
    if not t or not t.zoomed or len(t.panes) != 4:
        return False
    rest = [p for p in t.panes if p.id != t.leftmost().id]
    return active_id(c) == max(rest, key=lambda p: p.rect.y).id


def two_labelled(c):
    reset(c, tabs=[(None, R(P("A"), P("B")))], focus_pane="A")


def side_by_side(c):
    reset(c, tabs=[(None, R(P("left"), P("right")))], focus_pane="left")


WORLD = World(2, "Pane Power", card="pane_power", missions=[
    Mission("2.1", "Zoom", xp=50, par=25, steps=[
        Step("Zoom the focused pane to fill the tab: `prefix+z`",
             setup=panes_right(3, sel=1),
             goal=lambda c: bool(tab(c) and tab(c).zoomed),
             hints=["Prefix, then z.", "`ctrl+b` then `z`"],
             expect=["zoom"], keys=["zoom"], demo=["prefix+z"]),
        Step("The other panes are still there, just hidden. Unzoom: `prefix+z` again.",
             goal=lambda c: bool(tab(c) and not tab(c).zoomed),
             hints=["Same key again: `prefix+z`"],
             done="Zoom is a toggle: work small, zoom to focus, zoom back out."),
    ]),
    Mission("2.2", "Resize mode", xp=60, par=40, card="resize", steps=[
        Step("Make the LEFT pane much wider: `prefix+r`, then `l` a few times.",
             setup=side_by_side,
             goal=lambda c: ratio(c) >= 0.65,
             mistakes=[(lambda c: ratio(c) < 0.4, "The divider went left. `l` pushes it right, `h` pulls it left.")],
             hints=["prefix+r enters resize mode (see RESIZE at the bottom). Then tap l, l, l.",
                    "`prefix+r` then `l` `l` `l` `l`"],
             expect=["resize_mode"], keys=["resize"], demo=["prefix+r", "l", "l", "l", "l"]),
        Step("Wide enough! Leave resize mode: `esc`",
             goal=lambda c: not in_mode(c, "resize"),
             hints=["Press Escape once."],
             done="One prefix, then as many h/j/k/l taps as you like. j/k do heights."),
    ]),
    Mission("2.3", "Drag the border", xp=40, par=30, bonus=True, steps=[
        Step("Use the mouse: **drag** the line between the panes to the left, until the right "
             "pane takes up about three quarters of the space.",
             setup=side_by_side,
             goal=lambda c: ratio(c) <= 0.35,
             hints=["Press the mouse button on the border between the two panes, hold, move left, let go."],
             keys=["drag-border"],
             done="Borders are handles. Every split can be dragged."),
    ]),
    Mission("2.4", "Swap", xp=50, par=30, steps=[
        Step("Pane A is on the left. Swap it with its neighbour: `prefix+shift+l`",
             setup=two_labelled,
             goal=lambda c: bool(tab(c) and tab(c).by_label("A")) and not a_left_of_b(c),
             hints=["shift+l is a capital L. Swap keys are the move keys with Shift held.",
                    "`ctrl+b` then `L` (Shift+l)"],
             expect=["swap_pane_right"], keys=["swap"], demo=["prefix+shift+l"]),
        Step("And swap it back: `prefix+shift+h`",
             goal=a_left_of_b,
             hints=["`ctrl+b` then `H` (Shift+h)"],
             done="The pane moved with its program still running inside. Same for j/k: swap up and down."),
    ]),
    Mission("2.5", "Hide the sidebar", xp=50, par=30, steps=[
        Step("Need more room? Collapse the sidebar: `prefix+b`",
             setup=fresh,
             goal=sidebar_closed,
             hints=["Prefix, then b (for sidebar... or Bar).", "`ctrl+b` then `b`"],
             expect=["toggle_sidebar"], keys=["sidebar"], demo=["prefix+b"]),
        Step("A slim rail stays, still showing agent status dots. Bring it back: `prefix+b`",
             goal=sidebar_open,
             hints=["Same key: `prefix+b`. (Or click the « / » at the bottom of the rail.)"],
             done="The sidebar is Herdr's dashboard: workspaces on top, agents below."),
    ]),
    Mission("2.6", "BOSS: Blueprint", xp=150, par=90, boss=True, card="blueprint", steps=[
        Step("BOSS! Build it: one pane on the LEFT, three stacked on the RIGHT.",
             setup=fresh,
             goal=blueprint_shape,
             mistakes=[(lambda c: npanes(c) > 4, "Too many panes! `prefix+x` closes the focused one.")],
             hints=["Split right once, then split the right pane down twice.",
                    "`prefix+v`, `prefix+minus`, `prefix+minus`"]),
        Step("Make the left pane wider than half the screen.",
             goal=left_wide,
             hints=["Resize mode moves the border: `prefix+r`, then `l` pushes it right. Or drag it.",
                    "`prefix+r` `l` `l` `l` `esc`"]),
        Step("Finally, zoom the BOTTOM-RIGHT pane.",
             goal=zoomed_br,
             hints=["Move to it with `prefix+l` / `prefix+j`, then `prefix+z`."]),
    ]),
])
