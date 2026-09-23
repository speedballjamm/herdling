"""World 6: detach, reattach, and named sessions, practised in your own shell outside Herdr."""
import random

from .. import herdr as herdr_mod
from .common import WORDS, Mission, P, Step, World, answered, reset

OUT_BACK = "Type:  herdr        (with no arguments it re-attaches to your session)"
OUT_LIST = "Type:  herdr session list"


def detached(c):
    return not c.s.attached


def on_session(name):
    return lambda c: c.s.attached and c.s.attached_session == name


def ticking(secs=3600, code="-"):
    def setup(c):
        reset(c, tabs=[("job", P("job", "ticker", secs, code))])
    return setup


def boss_setup(c):
    c.mem["code"] = random.choice(WORDS)
    ticking(20, c.mem["code"])(c)


def session_gone(name):
    def goal(c):
        if not c.ran_outside(("herdr", "session", "stop", name), ("herdr", "session", "delete", name)):
            return False
        return name not in herdr_mod.running_sessions()
    return goal


def stopped_session(name):
    """Make sure a stopped session called `name` exists (so it can be deleted)."""
    def setup(c):
        other = herdr_mod.Herdr(name)
        if name not in [x["name"] for x in herdr_mod.sessions()]:
            other.start_server()
        other.stop_server()
    return setup


def session_deleted(name):
    def goal(c):
        if not c.ran_outside(("herdr", "session", "delete", name)):
            return False
        return name not in [s["name"] for s in herdr_mod.sessions()]
    return goal


WORLD = World(6, "Detach & Sessions", card="sessions", missions=[
    Mission("6.1", "Walk away", xp=60, par=60, card="detach", steps=[
        Step("A job is running in this pane. Detach from Herdr: `prefix+q`",
             setup=ticking(),
             goal=detached,
             hints=["Prefix, then q (for quit the view, not the work).", "`ctrl+b` then `q`"],
             expect=["detach"], keys=["detach"], demo=["prefix+q"],
             done="You're out. Herdr (and the job) are still running in the background."),
        Step("Now go back in: type **herdr** at the prompt.",
             goal=lambda c: c.s.attached and c.ran_outside(("herdr",)),
             outside=OUT_BACK,
             hints=["In your shell, type herdr and press Enter."],
             keys=["herdr"],
             done="Welcome back. The job kept counting while you were gone."),
    ]),
    Mission("6.2", "Still there?", xp=80, par=120, steps=[
        Step("Detach again (`prefix+q`), then list what's running: **herdr session list**",
             setup=ticking(),
             goal=lambda c: c.ran_outside(("herdr", "session", "list"), ("herdr", "session", "ls")),
             detached=True, outside=OUT_LIST,
             hints=["`prefix+q` first, then type the command in your shell."],
             keys=["session-list"],
             done="'default … running': that's the game's Herdr, still going."),
        Step("Back in with **herdr**.",
             goal=lambda c: c.s.attached,
             outside=OUT_BACK,
             hints=["Type herdr."],
             done="Detach and attach as often as you like; SSH users detach before logging off."),
    ]),
    Mission("6.3", "A second session", xp=100, par=180, card="named_sessions", steps=[
        Step("Detach, then start a separate session called **work**: **herdr session attach work**",
             setup=lambda c: reset(c),
             goal=on_session("work"),
             detached=True, outside="Type:  herdr session attach work      (herdr --session work does the same)",
             hints=["`prefix+q`, then in your shell: herdr session attach work"],
             keys=["session-attach"],
             done="A brand-new, empty Herdr: its own server, workspaces and panes."),
        Step("This is the **work** session. Detach from it: `prefix+q`",
             goal=detached,
             hints=["`prefix+q`, same as always."]),
        Step("List sessions: **herdr session list**. You should see two running.",
             goal=lambda c: c.ran_outside(("herdr", "session", "list"), ("herdr", "session", "ls")),
             detached=True, outside=OUT_LIST,
             hints=["herdr session list"]),
        Step("Stop the work session (this ends its panes): **herdr session stop work**",
             goal=session_gone("work"),
             detached=True, outside="Type:  herdr session stop work",
             hints=["herdr session stop work"],
             keys=["session-stop"],
             done="Stopped. (It's remembered, stopped; `herdr session delete work` forgets it.)"),
        Step("Back to your game: **herdr**",
             goal=on_session("default"),
             outside=OUT_BACK,
             hints=["herdr on its own attaches the default session: the game's."]),
    ]),
    Mission("6.4", "Tidy up", xp=40, par=120, bonus=True, steps=[
        Step("Detach and delete the stopped **work** session for good: **herdr session delete work**",
             setup=stopped_session("work"), goal=session_deleted("work"),
             detached=True, outside="Type:  herdr session delete work    (it must be stopped first)",
             hints=["`prefix+q`, then herdr session delete work. If it says it's running: "
                    "herdr session stop work first."],
             keys=["session-delete"]),
        Step("Back in: **herdr**", goal=lambda c: c.s.attached, outside=OUT_BACK, hints=["herdr"]),
    ]),
    Mission("6.5", "BOSS: Survive the disconnect", xp=150, par=150, boss=True, steps=[
        Step("BOSS! A 20-second job just started. Detach **now**, so you're not watching it.",
             setup=boss_setup,
             goal=detached,
             hints=["`prefix+q`"]),
        Step("Prove it's still running: **herdr session list**",
             goal=lambda c: c.ran_outside(("herdr", "session", "list"), ("herdr", "session", "ls")),
             detached=True, outside=OUT_LIST,
             hints=["herdr session list"]),
        Step("Wait a bit, then go back in and read the code word the job printed. "
             "Type **herdling answer WORD** in a pane.",
             goal=lambda c: answered(c, c.mem["code"]),
             outside=OUT_BACK,
             hints=["herdr, then look at the job pane. If it's still counting, wait for it.",
                    "herdling answer <the word>"]),
    ]),
])
