"""Dojo (60-second speed drills) and Review (spaced repetition).

Each drill is a quick prompt ("Zoom!") with a setup that nudges the sandbox into
a state where the prompt makes sense, and a goal that spots success.
"""
import os
import random
import time

from . import progress
from .keys import BY_ID as KEYS
from .model import Ctx
from .setups import reset, settle, snap

WORDS = ["api", "db", "notes", "build", "logs", "docs", "tests", "web", "infra", "ml"]
BASICS = ["split-right", "split-down", "focus", "zoom", "new-tab", "next-tab", "close-pane"]
ROUND_SECS = int(os.environ.get("HERDLING_DOJO_SECS", "60"))   # tests use a short round


class Drill:
    def __init__(self, kid, prompt, goal, setup=None):
        self.kid, self.prompt, self.goal, self.setup = kid, prompt, goal, setup


# --- sandbox helpers ----------------------------------------------------------------

def norm(c):
    """Leave Herdr modes, unzoom, and keep things from growing without bound."""
    e = c.engine
    for _ in range(2):
        if e.tracker.mode != "terminal":
            e.press("esc", delay=0.15)
    s = snap(c)
    if s is None or not s.ws or not s.tab:
        reset(c)
        return snap(c)
    if s.tab.zoomed:
        c.herdr.try_call("pane.zoom", pane_id=s.fpane, mode="off")
    if len(s.workspaces) > 4 or len(s.ws.tabs) > 5 or len(s.tab.panes) > 5 or \
            min(p.rect.w for p in s.tab.panes) < 12:
        reset(c)
    w = s.sidebar_width()
    if w is not None and w < 12:
        e.press("prefix", "b")
    return settle(c, 0.1)


def need_panes(c, n):
    s = norm(c)
    for _ in range(n - len(s.tab.panes)):
        biggest = max(s.tab.panes, key=lambda p: p.rect.w * p.rect.h)
        c.herdr.try_call("pane.split", target_pane_id=biggest.id,
                         direction="right" if biggest.rect.w > biggest.rect.h * 2 else "down", focus=False)
        s = settle(c, 0.1)
    return s


def need_tabs(c, n):
    s = norm(c)
    for i in range(n - len(s.ws.tabs)):
        c.herdr.try_call("tab.create", workspace_id=s.ws.id, label=random.choice(WORDS), focus=False)
    return settle(c, 0.1)


def need_spaces(c, n):
    s = norm(c)
    for i in range(n - len(s.workspaces)):
        c.herdr.try_call("workspace.create", label=random.choice(WORDS), focus=False)
    return settle(c, 0.1)


def neighbour_dirs(t, a):
    dirs = {}
    for p in t.panes:
        if p.id == a.id:
            continue
        vo = p.rect.y < a.rect.bottom and a.rect.y < p.rect.bottom
        ho = p.rect.x < a.rect.right and a.rect.x < p.rect.right
        if vo and p.rect.right <= a.rect.x + 1:
            dirs["LEFT"] = "h"
        if vo and p.rect.x >= a.rect.right - 1:
            dirs["RIGHT"] = "l"
        if ho and p.rect.bottom <= a.rect.y + 1:
            dirs["UP"] = "k"
        if ho and p.rect.y >= a.rect.bottom - 1:
            dirs["DOWN"] = "j"
    return dirs


def tab_pos(s):
    for i, t in enumerate(s.ws.tabs):
        if t.id == s.ftab:
            return i
    return 0


# --- the drills ---------------------------------------------------------------------

def d_simple(kid, prompt, goal, panes=1, tabs=1):
    def setup(c):
        need_panes(c, panes)
        if tabs > 1:
            need_tabs(c, tabs)
    return Drill(kid, prompt, goal, setup)


def d_nav(rng):
    def setup(c):
        s = need_panes(c, 2)
        dirs = neighbour_dirs(s.tab, s.pane)
        d = rng.choice(sorted(dirs))
        c.mem["dir"] = d.lower()
        c.mem["prompt"] = f"Move one pane {d}!"

    def goal(c):
        return any(a.kind == "focus" and a.info.get("dir") == c.mem["dir"] for a in c.actions)
    return Drill("focus", "", goal, setup)


def d_unzoom():
    def setup(c):
        s = need_panes(c, 2)
        c.herdr.try_call("pane.zoom", pane_id=s.fpane, mode="on")
    return Drill("zoom", "Unzoom!", lambda c: c.s.tab and not c.s.tab.zoomed, setup)


def d_tab_step(kid, step, word):
    def setup(c):
        s = need_tabs(c, 3)
        i = tab_pos(s)
        c.mem["target"] = s.ws.tabs[(i + step) % len(s.ws.tabs)].id
    return Drill(kid, f"{word} tab!", lambda c: c.s.ftab == c.mem["target"], setup)


def d_tab_n(rng):
    def setup(c):
        s = need_tabs(c, 3)
        choices = [i for i in range(len(s.ws.tabs)) if s.ws.tabs[i].id != s.ftab][:9]
        i = rng.choice(choices)
        c.mem["target"] = s.ws.tabs[i].id
        c.mem["prompt"] = f"Go to tab {i + 1}!"
    return Drill("switch-tab", "", lambda c: c.s.ftab == c.mem["target"], setup)


def d_rename_tab(rng):
    word = rng.choice(WORDS) + str(rng.randint(2, 99))
    return Drill("rename-tab", f"Rename this tab to '{word}'!", lambda c: c.s.tab and c.s.tab.label == word,
                 lambda c: norm(c))


def d_rename_ws(rng):
    word = rng.choice(WORDS) + str(rng.randint(2, 99))
    return Drill("rename-ws", f"Rename this workspace to '{word}'!", lambda c: c.s.ws and c.s.ws.label == word,
                 lambda c: norm(c))


def d_rename_pane(rng):
    word = rng.choice(WORDS) + str(rng.randint(2, 99))
    return Drill("rename-pane", f"Name this pane '{word}'!", lambda c: c.s.pane and c.s.pane.label == word,
                 lambda c: norm(c))


def d_space_n(rng):
    def setup(c):
        s = need_spaces(c, 3)
        choices = [i for i, w in enumerate(s.workspaces) if w.id != s.fws][:9]
        i = rng.choice(choices)
        c.mem["target"] = s.workspaces[i].id
        c.mem["prompt"] = f"Go to workspace {i + 1} ({s.workspaces[i].label})!"
    return Drill("navigate", "", lambda c: c.s.fws == c.mem["target"], setup)


def make(kid, rng):
    table = {
        "split-right": lambda: d_simple("split-right", "Split: new pane on the RIGHT!", lambda c: c.did("split-right")),
        "split-down": lambda: d_simple("split-down", "Split: new pane BELOW!", lambda c: c.did("split-down")),
        "focus": lambda: d_nav(rng),
        "cycle": lambda: d_simple("cycle", "Cycle to the next pane!",
                                  lambda c: c.pressed("cycle_pane_next", "cycle_pane_previous"), 3),
        "close-pane": lambda: d_simple("close-pane", "Close this pane!", lambda c: c.did("close-pane"), 2),
        "zoom": lambda: rng.choice([lambda: d_simple("zoom", "Zoom!", lambda c: c.s.tab and c.s.tab.zoomed, 2),
                                    d_unzoom])(),
        "swap": lambda: d_simple("swap", "Swap this pane with a neighbour!", lambda c: c.did("swap"), 2),
        "resize": lambda: d_simple("resize", "Resize a split (then esc)!", lambda c: c.did("resize"), 2),
        "sidebar": lambda: d_simple("sidebar", "Collapse the sidebar!", lambda c: c.did("sidebar")),
        "rename-pane": lambda: d_rename_pane(rng),
        "new-tab": lambda: d_simple("new-tab", "New tab (any name)!", lambda c: c.did("new-tab")),
        "next-tab": lambda: d_tab_step("next-tab", 1, "Next"),
        "prev-tab": lambda: d_tab_step("prev-tab", -1, "Previous"),
        "switch-tab": lambda: d_tab_n(rng),
        "rename-tab": lambda: d_rename_tab(rng),
        "close-tab": lambda: d_simple("close-tab", "Close this tab!", lambda c: c.did("close-tab"), 1, 2),
        "new-ws": lambda: d_simple("new-ws", "New workspace!", lambda c: c.did("new-ws")),
        "rename-ws": lambda: d_rename_ws(rng),
        "navigate": lambda: d_space_n(rng),
        "help": lambda: d_simple("help", "Open the list of every key!", lambda c: c.pressed("help")),
        "copy-mode": lambda: d_simple("copy-mode", "Enter copy mode!", lambda c: c.pressed("copy_mode")),
        "goto": lambda: d_simple("goto", "Open goto (search every pane)!", lambda c: c.pressed("goto")),
    }
    f = table.get(kid)
    return f() if f else None


DRILLABLE = ["split-right", "split-down", "focus", "cycle", "close-pane", "zoom", "swap", "resize", "sidebar",
             "rename-pane", "new-tab", "next-tab", "prev-tab", "switch-tab", "rename-tab", "close-tab", "new-ws",
             "rename-ws", "navigate", "help", "copy-mode", "goto"]


# --- the loop -----------------------------------------------------------------------

def attempt(engine, drill, reveal_after, give_up_after, deadline=None):
    """Run one drill. Returns (seconds taken or None, whether the key was revealed)."""
    ctx = Ctx(engine.h, {}, engine)
    if drill.setup:
        drill.setup(ctx)
        time.sleep(0.1)
    s = engine.refresh()
    engine.key_actions()
    ctx.s = ctx.base = s
    prompt = drill.prompt or ctx.mem.get("prompt", "")
    engine.hud.set(prompt=prompt)
    engine.write_runtime(title=engine.hud.title, prompt=prompt, hints=[])
    engine.msg("")
    start = time.time()
    revealed = False
    while True:
        s, acts, evs = engine.tick()
        ctx.new_tick(s, acts, evs)
        for e in evs:
            if e.get("type") == "cmd" and e.get("cmd") in ("skip", "hint", "show"):
                give_up_after = 0
        el = time.time() - start
        try:
            ok = drill.goal(ctx)
        except Exception:
            ok = False
        if ok:
            return (el, revealed)
        if not revealed and el > reveal_after:
            revealed = True
            engine.msg(f"The key: `{KEYS[drill.kid].keys}`", "hint")
        if el > give_up_after or (deadline and time.time() > deadline):
            return (None, True)


def run(engine, review=False, worlds=None):
    data = engine.data
    rng = random.Random()
    if review:
        return run_review(engine, data, rng)
    while True:
        pool = [k for k in data["keys"] if k in DRILLABLE] or []
        note = ""
        if len(pool) < 4:
            pool = BASICS
            note = " (warm-up set: finish more missions to unlock more)"
        run_dojo(engine, data, rng, pool, note)
        engine.hud.set(title="DOJO", prompt="Round over! Type  **herdling again**  in a pane for another round.")
        engine.msg("Or `herdling menu` to go back to the title screen.", "info")
        while True:
            _, _, evs = engine.tick()
            if any(e.get("type") == "cmd" and e.get("cmd") in ("again", "skip") for e in evs):
                break


def run_dojo(engine, data, rng, pool, note):
    engine.mode = "dojo"
    engine.show_card(text={"title": "Dojo: 60-second drills", "body": f"""\
Prompts flash up in the bar at the bottom: **Zoom!**, **New tab!**,
**Split: new pane BELOW!** Do each one as fast as you can.

  • quick answers (under 4s) build a **combo** multiplier
  • stuck? after 5 seconds the key is shown (fewer points)
  • `herdling skip` in a pane skips a prompt

Keys in play: {len(pool)}{note}
Best score so far: **{data.get('dojo_best', 0)}**
"""})
    reset(Ctx(engine.h, {}, engine))
    score, combo, last = 0, 1, None
    end = time.time() + ROUND_SECS
    engine.timer = None
    engine.hud.set(title="DOJO")
    solved = 0
    while time.time() < end:
        kid = rng.choice([k for k in pool if k != last] or pool)
        last = kid
        drill = make(kid, rng)
        if not drill:
            continue

        def left():
            return max(0, int(end - time.time()))
        engine.hud.set(right=f"time {left()}s · score {score} · combo x{combo}")
        el, revealed = attempt(engine, drill, 5, 15, deadline=end)
        if el is None:
            combo = 1
            continue
        solved += 1
        pts = 25 if revealed else 100 * combo
        score += pts
        combo = min(8, combo + 1) if (el < 4 and not revealed) else 1
        engine.msg(f"+{pts}" + ("  COMBO!" if combo > 2 else ""), "ok", 1)
        engine.hud.set(right=f"time {left()}s · score {score} · combo x{combo}")
    best = data.get("dojo_best", 0)
    new_best = score > best
    data["dojo_best"] = max(best, score)
    data["xp"] += score // 50
    engine.save()
    engine.bell()
    engine.show_card(text={"title": "Time!", "body": f"""\
  Score:    **{score}**{'   NEW PERSONAL BEST!' if new_best else ''}
  Solved:   {solved} prompts
  Best:     {data['dojo_best']}
  XP:       +{score // 50}
"""})


def run_review(engine, data, rng):
    engine.mode = "review"
    due = [k for k in progress.due_keys(data) if k in DRILLABLE][:12]
    if not due:
        engine.show_card(text={"title": "Review", "body": """\
Nothing is due for review right now. Nice!

Keys come back for review after 1, 3, 7 and 21 days, sooner
if you fumbled them. Finish more missions to add keys.

Dropping you into the sandbox instead.
"""})
        return engine.sandbox()
    engine.show_card(text={"title": "Review", "body": f"""\
**{len(due)}** keys are due. For each prompt, do it from memory.

  • get it before the key is revealed (10s) and it moves up a box
    and comes back later
  • miss it and it drops to box 1 and comes back sooner
"""})
    reset(Ctx(engine.h, {}, engine))
    engine.hud.set(title="REVIEW")
    right = 0
    for i, kid in enumerate(due):
        engine.hud.set(right=f"{i + 1} / {len(due)} · {right} right")
        drill = make(kid, rng)
        el, revealed = attempt(engine, drill, 10, 40)
        ok = el is not None and not revealed
        right += ok
        progress.learn_key(data, kid, ok=ok)
        engine.msg("Got it!" if ok else f"That one was `{KEYS[kid].keys}`: it'll come back soon.",
                   "ok" if ok else "hint", 2)
        time.sleep(0.8)
    engine.save()
    engine.show_card(text={"title": "Review done", "body": f"""\
  You knew **{right}** of {len(due)}.

  Missed keys come back tomorrow; known ones get spaced further out.
  Come back daily for a couple of minutes: that's how it sticks.
"""})
    engine.sandbox()
