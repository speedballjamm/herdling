"""World 8: drive Herdr from the command line, the way scripts and agents do.

Every pane has HERDR_ENV=1 and HERDR_PANE_ID set, and the `herdr` command in it
talks to the Herdr that owns the pane."""
import random

from .common import WORDS, Mission, P, R, Step, World, answered, npanes, pane_contains, reset, tab, tab_names


def one_pane(c):
    reset(c, tabs=[("cli", P("console"))])


def with_target(c):
    reset(c, tabs=[("cli", R(P("console"), P("target")))], focus_pane="console")
    c.mem["target"] = c.s.pane_labelled("target").id if c.s.pane_labelled("target") else None


def with_secret(c):
    code = f"{random.choice(WORDS)}-{random.randint(100, 999)}"
    c.mem["code"] = code
    reset(c, tabs=[("cli", R(P("console"), P("vault", "banner", f"vault unlocked. code: {code}")))],
          focus_pane="console")


def console_says(text):
    def goal(c):
        p = c.s.pane_labelled("console")
        return bool(p) and text in c.read(p.id)
    return goal


def target_says(text):
    def goal(c):
        p = c.s.pane_labelled("target")
        return bool(p) and pane_contains(c, p.id, text)
    return goal


def split_kept_focus(c):
    t = tab(c)
    return bool(t) and c.did("split-right") and npanes(c) == 2 and c.s.pane and c.s.pane.label == "console"


def fleet_ready(c):
    for t in c.s.tabs.values():
        if t.label == "fleet" and len(t.panes) >= 3:
            ready = sum(1 for p in t.panes if "ready" in "\n".join(
                l for l in c.read(p.id).splitlines() if "echo ready" not in l))
            return ready >= 2
    return False


WORLD = World(8, "The Command Line", card="cli", missions=[
    Mission("8.1", "Where am I?", xp=50, par=60, steps=[
        Step("Ask Herdr about this pane: type **herdr pane current** and press Enter.",
             setup=one_pane,
             goal=console_says('"pane_id"'),
             hints=["It prints JSON: the pane's id, its tab, its workspace, its folder…"],
             keys=["cli-list"],
             done="That id (like w1:p1) is how scripts point at a pane."),
        Step("Now the whole picture: **herdr workspace list**",
             goal=console_says('"workspaces"'),
             hints=["herdr workspace list. Also try herdr tab list and herdr pane list."],
             done="Everything you see in the sidebar, as data a script can read."),
    ]),
    Mission("8.2", "Split from a script", xp=60, par=60, steps=[
        Step("Split without touching a key: **herdr pane split --current --direction right --no-focus**",
             setup=one_pane,
             goal=split_kept_focus,
             hints=["--current means 'the pane I'm typing in'; --no-focus keeps you where you are.",
                    "herdr pane split --current --direction right --no-focus"],
             keys=["cli-split"],
             done="The new pane's id is in the JSON it printed (\"pane_id\")."),
    ]),
    Mission("8.3", "Run it over there", xp=60, par=90, steps=[
        Step("Find the **target** pane's id with **herdr pane list**, then run a command in it: "
             "**herdr pane run ID \"echo hi from afar\"**",
             setup=with_target,
             goal=target_says("hi from afar"),
             hints=["pane list shows each pane's \"pane_id\" and its \"label\". The target's id is like w5:p3.",
                    "herdr pane run <target id> \"echo hi from afar\""],
             keys=["cli-run"],
             done="Your typing never left this pane. That's how agents drive test runners and servers."),
    ]),
    Mission("8.4", "Read it back", xp=60, par=90, steps=[
        Step("The **vault** pane printed a code. Find its id with **herdr pane list**, read it with "
             "**herdr pane read ID**, then send it: **herdling answer CODE**. Hit Enter after each.",
             setup=with_secret,
             goal=lambda c: answered(c, c.mem["code"]),
             hints=["herdr pane list to get the vault's id, then herdr pane read <id>.",
                    "herdr pane read <vault id> --source recent"],
             keys=["cli-read"],
             done="pane read + pane wait-output: watch any pane from a script."),
    ]),
    Mission("8.5", "Tabs on demand", xp=50, par=60, steps=[
        Step("Make a tab called **build** from the command line: **herdr tab create --label build**",
             setup=one_pane,
             goal=lambda c: "build" in tab_names(c),
             hints=["herdr tab create --label build (add --focus to switch to it)."],
             keys=["cli-tab"],
             done="workspace create, tab create, pane split: a project's whole layout can be a script."),
    ]),
    Mission("8.6", "Ping!", xp=40, par=60, bonus=True, steps=[
        Step("Pop up a notification: **herdr notification show \"coffee break\"**",
             setup=one_pane,
             goal=console_says('"shown"'),
             hints=["herdr notification show \"coffee break\" --body \"back in 5\""],
             keys=["cli-notify"],
             done="Handy at the end of a long script: it pops up even if you're in another workspace."),
    ]),
    Mission("8.7", "BOSS: Fleet", xp=200, par=300, boss=True, steps=[
        Step("BOSS! Using only herdr commands: make a tab labelled **fleet** with **3 panes**, and "
             "run **echo ready** in at least two of them with `herdr pane run`.",
             setup=one_pane,
             goal=fleet_ready,
             hints=["herdr tab create --label fleet --focus prints the new root pane's id. Split it twice "
                    "with herdr pane split <id> --direction right.",
                    "Each split prints the new pane_id; then: herdr pane run <id> \"echo ready\""]),
    ]),
])
