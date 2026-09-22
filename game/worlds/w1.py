from .common import Mission, Step, World, active_id, corner_is, fresh, npanes, panes_right, quad, tab

SPLIT_DOWN_NOT_RIGHT = (lambda c: c.just("split-down"),
                        "That was `prefix+minus` (stacked). For side by side press `prefix+v`. "
                        "`prefix+x` closes the extra pane.")
SPLIT_RIGHT_NOT_DOWN = (lambda c: c.just("split-right"),
                        "That was `prefix+v` (side by side). For top/bottom press `prefix+minus` (the - key). "
                        "`prefix+x` closes the extra pane.")


def visit_all(c):
    seen = c.mem.setdefault("seen", set())
    seen.add(active_id(c))
    return len({p.id for p in tab(c).panes} - seen) == 0


def is_left(c):
    return bool(tab(c) and active_id(c) == tab(c).leftmost().id)


def is_right(c):
    return bool(tab(c) and active_id(c) == tab(c).rightmost().id)


def focused_is(label):
    return lambda c: bool(c.s.pane and c.s.pane.label == label)


WORLD = World(1, "Panes 101", card="panes", missions=[
    Mission("1.1", "Side by side", xp=50, par=20, steps=[
        Step("Split this pane into left | right: `prefix+v`",
             setup=fresh,
             goal=lambda c: c.did("split-right") and npanes(c) >= 2,
             mistakes=[SPLIT_DOWN_NOT_RIGHT], expect=["split_vertical"],
             hints=["Prefix first (ctrl+b, let go), then the letter v.", "`ctrl+b` then `v`"],
             keys=["split-right"], demo=["prefix+v"],
             done="Two shells, side by side. v for a Vertical divider line."),
    ]),
    Mission("1.2", "Stacked", xp=50, par=20, steps=[
        Step("Split this pane top / bottom: `prefix+minus` (the - key)",
             setup=fresh,
             goal=lambda c: c.did("split-down") and npanes(c) >= 2,
             mistakes=[SPLIT_RIGHT_NOT_DOWN], expect=["split_horizontal"],
             hints=["Prefix, then the minus key (next to 0).", "`ctrl+b` then `-`"],
             keys=["split-down"], demo=["prefix+minus"],
             done="Top and bottom. - looks like the horizontal line it draws."),
    ]),
    Mission("1.3", "Hop around", xp=50, par=25, steps=[
        Step("The focused pane has the bright border. Move LEFT: `prefix+h`",
             setup=panes_right(2, sel="right"),
             goal=is_left,
             hints=["Herdr moves with vim's keys: h left, j down, k up, l right.", "`ctrl+b` then `h`"],
             keys=["focus"], demo=["prefix+h"]),
        Step("And back RIGHT: `prefix+l`",
             goal=is_right,
             hints=["l is right (it's the rightmost of h j k l).", "`ctrl+b` then `l`"],
             done="h ← j ↓ k ↑ l →. Your fingers already rest on them."),
    ]),
    Mission("1.4", "Four corners", xp=60, par=40, steps=[
        Step("Four panes! Go to the TOP-LEFT one: `prefix` + `h` `j` `k` `l`",
             setup=quad(sel="br"),
             goal=corner_is("tl"),
             hints=["One prefix per move: `prefix+k` goes up, `prefix+h` goes left.",
                    "From bottom-right: `prefix+k` then `prefix+h`"],
             keys=["focus"]),
        Step("Now the BOTTOM-RIGHT pane.", goal=corner_is("br"), hints=["`prefix+j` then `prefix+l`"]),
        Step("Now the TOP-RIGHT pane.", goal=corner_is("tr"), hints=["`prefix+k`"]),
        Step("And finally BOTTOM-LEFT.", goal=corner_is("bl"), hints=["`prefix+j` then `prefix+h`"],
             done="Clicking a pane works too, but h/j/k/l is quicker once your hands know it."),
    ]),
    Mission("1.5", "Round robin", xp=50, par=25, steps=[
        Step("Visit every pane with `prefix+tab` (next pane). Press it a few times.",
             setup=panes_right(3, sel="left"),
             goal=visit_all,
             hints=["Prefix, then the Tab key. Repeat it.", "`prefix+tab`, `prefix+tab`, `prefix+tab`"],
             keys=["cycle"], demo=["prefix+tab", "prefix+tab"],
             done="`prefix+tab` cycles in order; `prefix+shift+tab` goes backwards."),
    ]),
    Mission("1.6", "Clean up", xp=50, par=30, card="close", steps=[
        Step("Close the focused pane: `prefix+x`. (No 'are you sure?': it just goes.)",
             setup=panes_right(3),
             goal=lambda c: npanes(c) == 2,
             hints=["Prefix, then x.", "`ctrl+b` then `x`"],
             expect=["close_pane"], keys=["close-pane"], demo=["prefix+x"]),
        Step("Close another the shell way: type **exit** and press Enter.",
             goal=lambda c: npanes(c) == 1,
             hints=["Type exit in the focused pane and press Enter."],
             keys=["exit"], done="When the program in a pane ends, the pane closes."),
    ]),
    Mission("1.7", "Name tags", xp=50, par=40, steps=[
        Step("Name this pane **server**: `prefix+shift+p`, type server, press Enter.",
             setup=panes_right(2, sel="left"),
             goal=focused_is("server"),
             mistakes=[(lambda c: c.s.pane and c.s.pane.label and c.s.pane.label != "server",
                        "Close! The name should be exactly: server. Try `prefix+shift+p` again.")],
             hints=["shift+p means a capital P: prefix, then Shift+p.",
                    "`prefix+shift+p`, then type server, then Enter"],
             expect=["rename_pane"], keys=["rename-pane"],
             done="The name shows on the pane's border. Agents and scripts can find panes by name too."),
    ]),
    Mission("1.8", "Click to focus", xp=40, par=20, bonus=True, steps=[
        Step("Click the pane labelled **C** to focus it.",
             setup=panes_right(3, sel="A", labels=["A", "B", "C"]),
             goal=focused_is("C"),
             hints=["Pane names are on their top borders. Click anywhere inside C."],
             keys=["click-pane"],
             done="Mouse or keys: both move focus. Use whichever your hand is already on."),
    ]),
    Mission("1.9", "BOSS: The Quad", xp=150, par=60, boss=True, steps=[
        Step("BOSS! Build a 2×2 grid of four panes. The clock is ticking!",
             setup=fresh,
             goal=lambda c: bool(tab(c) and tab(c).is_grid(2, 2) and not tab(c).zoomed),
             hints=["Split side by side, then split each half top/bottom.",
                    "`prefix+v`, `prefix+minus`, `prefix+h`, `prefix+minus`"],
             mistakes=[(lambda c: npanes(c) > 4, "Too many panes! Close extras with `prefix+x`.")]),
        Step("Visit ↖ TOP-LEFT", goal=corner_is("tl")),
        Step("Visit ↘ BOTTOM-RIGHT", goal=corner_is("br")),
        Step("Visit ↗ TOP-RIGHT", goal=corner_is("tr")),
        Step("Visit ↙ BOTTOM-LEFT", goal=corner_is("bl")),
    ]),
])
