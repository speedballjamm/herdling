from .common import Mission, Step, World, cur_tab_name, fresh, tab_names, tabs_setup


def on_tab(label):
    return lambda c: cur_tab_name(c) == label


def has_tab(label):
    return lambda c: label in tab_names(c)


def boss_tabs(c):
    names = tab_names(c)
    return names[:3] == ["code", "server", "logs"] and len(names) == 3


WORLD = World(3, "Tabs", card="tabs", missions=[
    Mission("3.1", "New tab", xp=50, par=30, steps=[
        Step("Make a new tab called **logs**: `prefix+c`, type logs, press Enter.",
             setup=fresh,
             goal=has_tab("logs"),
             mistakes=[(lambda c: c.did("new-tab") and "logs" not in tab_names(c),
                        "You made a tab, but it isn't called logs. Rename it: `prefix+shift+t`, "
                        "or close it with `prefix+shift+x` and try again.")],
             hints=["prefix+c asks for a name. Type logs over the suggested one, then Enter.",
                    "`prefix+c`, type logs, Enter"],
             expect=["new_tab"], keys=["new-tab"], demo=["prefix+c", "l", "o", "g", "s", "enter"],
             done="Tabs sit along the top. Each has its own layout of panes."),
    ]),
    Mission("3.2", "Next and previous", xp=50, par=30, steps=[
        Step("Three tabs. Go to the NEXT one: `prefix+n`",
             setup=tabs_setup("one", "two", "three"),
             goal=on_tab("two"),
             hints=["Prefix, then n (for next).", "`ctrl+b` then `n`"],
             expect=["next_tab"], keys=["next-tab"], demo=["prefix+n"]),
        Step("And the next one again: `prefix+n`", goal=on_tab("three"), hints=["`prefix+n`"]),
        Step("Now back one: `prefix+p` (previous).",
             goal=on_tab("two"),
             hints=["Prefix, then p.", "`ctrl+b` then `p`"],
             keys=["prev-tab"],
             done="n and p wrap around at the ends, too."),
    ]),
    Mission("3.3", "Jump by number", xp=50, par=30, steps=[
        Step("Tabs count from 1, left to right. Jump to tab 3 (**logs**): `prefix+3`",
             setup=tabs_setup("code", "server", "logs", "notes"),
             goal=on_tab("logs"),
             hints=["Prefix, then the number key 3.", "`ctrl+b` then `3`"],
             expect=["switch_tab_3"], keys=["switch-tab"], demo=["prefix+3"]),
        Step("Straight to tab 1 (**code**): `prefix+1`",
             goal=on_tab("code"),
             hints=["`ctrl+b` then `1`"],
             done="`prefix+1` … `prefix+9`: fastest way around once you know the order."),
    ]),
    Mission("3.4", "Rename", xp=50, par=30, steps=[
        Step("This tab is called **old**. Rename it to **api**: `prefix+shift+t`",
             setup=tabs_setup("old", tags=False),
             goal=on_tab("api"),
             mistakes=[(lambda c: c.did("rename-tab") and cur_tab_name(c) != "api",
                        "Renamed, but not to api. Try `prefix+shift+t` again (ctrl+u clears the box).")],
             hints=["shift+t is a capital T. Type the new name, Enter.",
                    "`prefix+shift+t`, ctrl+u, type api, Enter"],
             expect=["rename_tab"], keys=["rename-tab"],
             done="Good names make `prefix+g` (goto) and the agent list much easier to read."),
    ]),
    Mission("3.5", "Close a tab", xp=50, par=25, steps=[
        Step("Close the tab you're on (**junk**): `prefix+shift+x`",
             setup=tabs_setup("keep", "junk", active=1),
             goal=lambda c: tab_names(c) == ["keep"],
             hints=["shift+x is a capital X. Like closing a pane, there's no confirmation.",
                    "`ctrl+b` then `X`"],
             expect=["close_tab"], keys=["close-tab"], demo=["prefix+shift+x"],
             done="Gone, with every pane in it. The last tab closing closes its workspace."),
    ]),
    Mission("3.6", "Click a tab", xp=40, par=20, bonus=True, steps=[
        Step("Use the mouse: **click** the **server** tab in the top bar.",
             setup=tabs_setup("code", "server", "logs"),
             goal=on_tab("server"),
             hints=["The tab bar is the top row of Herdr. Click the word server."],
             keys=["click-tab"],
             done="Right-click a tab for more: rename, close, move."),
    ]),
    Mission("3.7", "BOSS: Mission Control", xp=150, par=120, boss=True, steps=[
        Step("BOSS! Make exactly three tabs named **code**, **server**, **logs**, in that order. "
             "(Rename this one to code first.)",
             setup=fresh,
             goal=boss_tabs,
             mistakes=[(lambda c: len(tab_names(c)) > 3, "Too many tabs: `prefix+shift+x` closes one.")],
             hints=["`prefix+shift+t` renames this tab to code. Then `prefix+c` twice.",
                    "`prefix+shift+t` code, `prefix+c` server, `prefix+c` logs"]),
        Step("Quick! Go to **server**.", goal=on_tab("server"), hints=["`prefix+2`"]),
        Step("Next tab!", goal=on_tab("logs"), hints=["`prefix+n`"]),
        Step("Rename **logs** to **tail**.", goal=on_tab("tail"), hints=["`prefix+shift+t`"]),
        Step("Back to **code**.", goal=on_tab("code"), hints=["`prefix+1`"]),
    ]),
])
