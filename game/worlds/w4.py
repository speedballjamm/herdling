from .common import (Mission, P, R, Step, World, cur_tab_name, cur_ws_name, fresh, reset, settle, snap,
                     spaces_setup, ws_names)


def on_ws(label):
    return lambda c: cur_ws_name(c) == label


def ws_count(c):
    return len(c.s.workspaces)


def fresh_counted(c):
    fresh(c)
    c.mem["n"] = len(snap(c).workspaces)


def haystack(c):
    """Three projects full of panes; one pane, somewhere, is called secret-sauce."""
    def tabs(*names):
        return [(n, R(P(), P())) for n in names]
    reset(c, label="frontend", tabs=tabs("code", "tests"),
          extra=[("backend", [("code", R(P(), P())), ("jobs", R(P(), R(P(), P("secret-sauce"))))]),
                 ("infra", tabs("terraform", "k8s"))])
    s = snap(c)
    order = [s.workspace_named(n).id for n in ("frontend", "backend", "infra")]
    c.herdr.try_call("workspace.move_block", workspace_ids=order)
    settle(c)


def boss_setup(c):
    reset(c, label="web", tabs=[("code", P(None, "label", "web: code")), ("logs", P(None, "label", "web: logs"))],
          extra=[("api", [("code", P(None, "label", "api: code")), ("logs", P(None, "label", "api: logs"))]),
                 ("db", [("shell", P(None, "label", "db: shell"))])])
    s = snap(c)
    c.herdr.try_call("workspace.move_block", workspace_ids=[s.workspace_named(n).id for n in ("web", "api", "db")])
    settle(c)


WORLD = World(4, "Workspaces", card="workspaces", missions=[
    Mission("4.1", "A new project", xp=50, par=40, steps=[
        Step("Make a new workspace: `prefix+shift+n`. Watch the sidebar.",
             setup=fresh_counted,
             goal=lambda c: ws_count(c) > c.mem.get("n", 1),
             hints=["shift+n is a capital N.", "`ctrl+b` then `N`"],
             expect=["new_workspace"], keys=["new-ws"], demo=["prefix+shift+n"],
             done="A new workspace, named after its folder (~ is your home folder)."),
        Step("Name it **api**: `prefix+shift+w`, type api, Enter.",
             goal=on_ws("api"),
             mistakes=[(lambda c: c.did("rename-ws") and cur_ws_name(c) != "api",
                        "Renamed, but not to api. `prefix+shift+w` again (ctrl+u clears the box).")],
             hints=["shift+w is a capital W.", "`prefix+shift+w`, ctrl+u, type api, Enter"],
             keys=["rename-ws"],
             done="One workspace per project, each with its own tabs and panes."),
    ]),
    Mission("4.2", "Navigate mode", xp=60, par=40, card="navigate", steps=[
        Step("You're in **frontend**. Go to **infra** with navigate mode: `prefix+w`, then ↓ ↓, then Enter.",
             setup=spaces_setup("frontend", "backend", "infra"),
             goal=on_ws("infra"),
             hints=["prefix+w shows NAVIGATE at the bottom. Arrow keys move the highlight in the sidebar.",
                    "`prefix+w` `↓` `↓` `enter`"],
             expect=["workspace_picker"], keys=["navigate"], demo=["prefix+w", "down", "down", "enter"]),
        Step("Faster: `prefix+w` then a number jumps straight there. Go to workspace **1** (frontend).",
             goal=on_ws("frontend"),
             hints=["`prefix+w` then `1`"],
             done="Navigate mode also moves between panes with h/j/k/l, and `esc` leaves."),
    ]),
    Mission("4.3", "Goto anything", xp=60, par=60, steps=[
        Step("Somewhere in these projects is a pane named **secret-sauce**. Find it: `prefix+g`, "
             "`/`, type secret, then ↓ to the pane itself and Enter.",
             setup=haystack,
             goal=lambda c: bool(c.s.pane and c.s.pane.label == "secret-sauce"),
             mistakes=[(lambda c: c.did("switch-ws") and not (c.s.pane and c.s.pane.label == "secret-sauce"),
                        "Right project, wrong pane: Enter opens whatever row is highlighted. "
                        "Try again and press ↓ until the pane row itself is highlighted.")],
             hints=["prefix+g opens a tree of every workspace, tab and pane. / searches it; ↓ moves "
                    "the highlight onto a row.", "`prefix+g` `/` secret, `↓` `↓`, `enter`"],
             expect=["goto"], keys=["goto"],
             done="Goto searches pane names, tabs and folders across every workspace."),
    ]),
    Mission("4.4", "Close a workspace", xp=50, par=30, steps=[
        Step("Close the **scratch** workspace (you're in it): `prefix+shift+d`, then Enter to confirm.",
             setup=spaces_setup("main", "scratch", active=1),
             goal=lambda c: ws_names(c) == ["main"],
             hints=["shift+d is a capital D. Herdr asks first, because it closes every tab and pane in it.",
                    "`prefix+shift+d` then `enter`"],
             expect=["close_workspace"], keys=["close-ws"], demo=["prefix+shift+d", "enter"],
             done="Unlike panes and tabs, closing a whole workspace asks first."),
    ]),
    Mission("4.5", "Click a space", xp=40, par=20, bonus=True, steps=[
        Step("With the mouse: **click** **backend** in the sidebar.",
             setup=spaces_setup("frontend", "backend", "infra"),
             goal=on_ws("backend"),
             hints=["The sidebar's top section lists your spaces (workspaces). Click the name."],
             keys=["click-ws"],
             done="Right-click a workspace for rename, close, and more."),
    ]),
    Mission("4.6", "BOSS: The Juggler", xp=150, par=120, boss=True, steps=[
        Step("BOSS! Three projects: web, api, db. Go to **api**'s **logs** tab.",
             setup=boss_setup,
             goal=lambda c: cur_ws_name(c) == "api" and cur_tab_name(c) == "logs",
             hints=["`prefix+w` `↓` `enter`, then `prefix+2`"]),
        Step("New project! Make a workspace named **docs**.",
             goal=on_ws("docs"),
             hints=["`prefix+shift+n`, then `prefix+shift+w` docs"]),
        Step("**db** is finished. Close it.",
             goal=lambda c: "db" not in ws_names(c),
             hints=["Go to db (`prefix+w`), then `prefix+shift+d` `enter`"]),
        Step("Back to **web**, tab **code**.",
             goal=lambda c: cur_ws_name(c) == "web" and cur_tab_name(c) == "code",
             hints=["`prefix+w` `1`, then `prefix+1`"]),
    ]),
])
