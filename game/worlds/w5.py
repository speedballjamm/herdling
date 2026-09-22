"""World 5: agents. The panes run a pretend coding agent (panes.py `agent`) that reports
working / blocked / idle to Herdr exactly the way a real agent integration does."""
from .common import Mission, P, R, Step, World, reset, settle, snap


def agent_pane(c, name):
    for a in c.s.agents:
        if a.agent == name:
            return a.pane
    return c.mem.get(f"pane:{name}")


def status(c, name):
    for a in c.s.agents:
        if a.agent == name:
            return a.status
    return None


def track(c):
    """Remember every agent that has been blocked this mission."""
    seen = c.mem.setdefault("was_blocked", set())
    for a in c.s.agents:
        c.mem[f"pane:{a.agent}"] = a.pane
        if a.status == "blocked":
            seen.add(a.agent)
    return seen


def answered(name):
    def goal(c):
        seen = track(c)
        st = status(c, name)
        return name in seen and st in ("working", "idle", "done")
    return goal


def focused_on(name):
    def goal(c):
        track(c)
        return c.s.fpane is not None and c.s.fpane == agent_pane(c, name)
    return goal


def sheep(name, script):
    return P(None, "agent", name, script)


def order(c, *labels):
    s = snap(c)
    c.herdr.try_call("workspace.move_block", workspace_ids=[s.workspace_named(l).id for l in labels
                                                            if s.workspace_named(l)])
    settle(c)


def same_tab(c):
    reset(c, label="home", tabs=[("work", R(P("editor"), sheep("claude", "work:4,ask:Can_I_edit_src/app.py?,work:3,done"),
                                              ratio=0.45))], focus_pane="editor")


def far_away(c):
    reset(c, label="home", tabs=[(None, P("editor"))],
          extra=[("api", [("agents", sheep("codex", "work:5,ask:Run_the_database_migration?,work:3,done"))]),
                 ("docs", [("agents", sheep("gemini", "work:600"))])])
    order(c, "home", "api", "docs")


def three_working(c):
    reset(c, label="web", tabs=[("agents", sheep("claude", "work:900"))],
          extra=[("api", [("agents", sheep("codex", "work:900"))]),
                 ("docs", [("agents", sheep("gemini", "work:900"))])])
    order(c, "web", "api", "docs")


def finishes_elsewhere(c):
    reset(c, label="home", tabs=[(None, P("editor"))],
          extra=[("ml", [("train", sheep("pi", "work:4,done"))])])


def boss_setup(c):
    reset(c, label="web", tabs=[("agents", R(sheep("claude", "work:3,ask:Install_3_new_packages?,work:4,done"),
                                             sheep("codex", "work:14,ask:Overwrite_package-lock.json?,work:3,done")))],
          extra=[("api", [("agents", sheep("gemini", "work:8,ask:Drop_the_users_table?_(it's_a_test_db),work:3,done"))]),
                 ("docs", [("agents", sheep("pi", "work:20,ask:Publish_the_docs_site?,work:2,done"))])])
    order(c, "web", "api", "docs")
    c.mem["herd"] = ["claude", "codex", "gemini", "pi"]


def herd_done(c):
    seen = track(c)
    herd = c.mem.get("herd", [])
    sts = [status(c, n) for n in herd]
    if any(s == "blocked" for s in sts):
        return False
    return set(herd) <= seen and all(s in ("idle", "done") for s in sts)


def not_blocked_msg(c):
    track(c)
    return False


WORLD = World(5, "The Herd", card="agents", missions=[
    Mission("5.1", "It needs you", xp=60, par=60, steps=[
        Step("An agent is working in the right pane. Watch its row in the sidebar's **agents** list. "
             "When it asks a question, click its pane (or `prefix+l`) and answer **y** + Enter.",
             setup=same_tab,
             goal=answered("claude"),
             hints=["When it's blocked, its dot changes colour and the pane shows a [y/n] question.",
                    "Focus the right pane with `prefix+l`, then type y and press Enter."],
             keys=["agents-panel"],
             done="Blocked means 'waiting for you'. Herdr spots it so you don't have to keep checking."),
        Step("Now let it finish. Wait until it's **done**.",
             goal=lambda c: status(c, "claude") in ("idle", "done"),
             hints=["Just wait a few seconds: it's working."],
             done="working → blocked → working → done. That's the whole life of an agent task."),
    ]),
    Mission("5.2", "A tap on the shoulder", xp=70, par=60, steps=[
        Step("An agent in another workspace will need you soon. When the notice pops up "
             "(bottom right), press `prefix+o` to jump straight to it.",
             setup=far_away,
             goal=focused_on("codex"),
             mistakes=[(lambda c: c.just_pressed("open_notification_target") and status(c, "codex") != "blocked"
                        and "codex" not in track(c),
                        "Nothing needs you yet. Wait for the pop-up, then `prefix+o`.")],
             hints=["Keep an eye on the bottom-right corner and the sidebar's dots.",
                    "When 'codex needs attention' appears: `ctrl+b` then `o`"],
             expect=["open_notification_target"], keys=["open-notif"]),
        Step("You're there. Answer it: **y** + Enter.",
             goal=answered("codex"),
             hints=["Type y, then Enter, in the codex pane."],
             done="`prefix+o`: 'take me to whatever just needed me', from anywhere."),
    ]),
    Mission("5.3", "Click the herd", xp=50, par=30, steps=[
        Step("Three agents, three projects. **Click** the agent named **gemini** in the sidebar's "
             "agents list (bottom left).",
             setup=three_working,
             goal=focused_on("gemini"),
             hints=["The lower half of the sidebar lists agents: each row shows its workspace, then its name."],
             keys=["click-agent"],
             done="Every agent, every project, one click away."),
    ]),
    Mission("5.4", "Done means unseen", xp=50, par=60, steps=[
        Step("An agent called **pi** is training a model in the **ml** workspace. Wait for it to finish.",
             setup=finishes_elsewhere,
             goal=lambda c: status(c, "pi") in ("done", "idle"),
             hints=["It takes a few seconds. Watch its row in the agents list."],
             done="It says done: finished, and you haven't looked yet."),
        Step("Go and look at **pi**'s pane (click its row, or navigate there). Seen = idle.",
             goal=lambda c: focused_on("pi")(c),
             hints=["Click pi in the agents list, or `prefix+w` to the ml workspace."],
             done="done = finished but unseen; idle = finished and seen. Both mean 'ready for more'."),
    ]),
    Mission("5.5", "BOSS: Herding cats", xp=200, par=150, boss=True, steps=[
        Step("BOSS! Four agents, three projects. Each will get **blocked** on a question. "
             "Answer every one (y + Enter) until the whole herd is done.",
             setup=boss_setup,
             goal=herd_done,
             hints=["Wait for the notices, then `prefix+o` jumps to whoever needs you. Answer y + Enter.",
                    "`prefix+o`, y, Enter, repeat. Four times."]),
    ]),
])
