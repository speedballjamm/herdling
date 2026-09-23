"""Final boss: a whole working day, using everything."""
import random

from .common import Mission, Step, World, cur_ws_name, fresh, run_prog, snap


def shop(c):
    return c.s.workspace_named("shop")


def has_tabs(c):
    w = shop(c)
    return bool(w) and [t.label for t in w.tabs][:2] == ["code", "server"]


def code_split(c):
    w = shop(c)
    t = w.tab_named("code") if w else None
    return bool(t) and len(t.panes) >= 2 and t.count("right") >= 1


def start_the_day(c):
    """Once the layout exists: an agent starts in `code`, and a log starts streaming in `server`."""
    s = snap(c)
    w = s.workspace_named("shop")
    code_tab, server_tab = w.tab_named("code"), w.tab_named("server")
    first = f"req-{random.randint(10000, 99999)}"
    c.mem["code"] = first
    decoys = ",".join(f"req-{random.randint(10000, 99999)}" for _ in range(2))
    agent_pane = code_tab.leftmost().id
    run_prog(c, agent_pane, "agent", "claude", "work:5,ask:Deploy_the_hotfix_to_staging?,work:4,done")
    run_prog(c, server_tab.panes[0].id, "incident", random.randint(1, 10 ** 6), first, decoys, 0.01)
    c.mem["agent_pane"] = agent_pane


def agent_answered(c):
    for a in c.s.agents:
        if a.agent == "claude":
            if a.status == "blocked":
                c.mem["was_blocked"] = True
            return c.mem.get("was_blocked") and a.status in ("working", "idle", "done")
    return False


def answered_code(c):
    a = c.answer()
    if a is None:
        return False
    if a.strip() == c.mem["code"]:
        return True
    c.say(f"'{a}' isn't the first error's request id. In copy mode, `g` jumps to the top, then `/` ERROR.")
    return False


def zoomed_agent(c):
    t = c.s.tab
    return bool(t and t.zoomed and c.s.fpane == c.mem.get("agent_pane"))


WORLD = World(10, "Final Boss", card="final", missions=[
    Mission("10.1", "FINAL BOSS: A day in the life", xp=400, par=420, boss=True, steps=[
        Step("Morning! New project: make a workspace called **shop**.",
             setup=fresh,
             goal=lambda c: cur_ws_name(c) == "shop",
             hints=["`prefix+shift+n`, then `prefix+shift+w` shop"]),
        Step("Give it two tabs: rename this one **code**, and add one called **server**.",
             goal=has_tabs,
             hints=["`prefix+shift+t` code, then `prefix+c` server"]),
        Step("Back in **code**, split it side by side: an agent will work on the left, you on the right.",
             goal=code_split,
             hints=["`prefix+1` (or click code), then `prefix+v`"]),
        Step("The day begins: an agent just started in the left pane, and logs are streaming in **server**. "
             "When the agent asks something, go to its pane and answer **y**.",
             setup=start_the_day,
             goal=agent_answered,
             hints=["Watch its dot in the agents list. When it's blocked: `prefix+h`, y, Enter."]),
        Step("Errors in the logs! Find the request id of the **FIRST** ERROR in the **server** tab, "
             "then type **herdling answer req-…** in your shell pane (not the agent's).",
             goal=answered_code,
             hints=["`prefix+2`, `prefix+[`, `g` to the top, then `/` ERROR. Answer back in code's "
                    "right pane."]),
        Step("Home time. Detach, and leave it all running.",
             goal=lambda c: not c.s.attached,
             hints=["`prefix+q`"]),
        Step("Next morning: back in with **herdr**.",
             goal=lambda c: c.s.attached,
             outside="Type:  herdr",
             hints=["herdr"]),
        Step("Last one: go to the agent's pane in **code** and zoom it to review its work.",
             goal=zoomed_agent,
             hints=["`prefix+w` to shop if needed, `prefix+1`, `prefix+h` to the agent, `prefix+z`"]),
    ]),
])
