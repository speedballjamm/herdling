"""End-to-end tests for everything that isn't a mission: sandbox, dojo, review, hints,
show-me, skip, reset, the menu, the shell outside Herdr and the title screen.

    python3 tests/test_modes.py            # all, in parallel
    python3 tests/test_modes.py hints      # just one
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game  # noqa: E402
from test_missions import outside  # noqa: E402


def seed_progress(home, keys, due=True):
    os.makedirs(home, exist_ok=True)
    t = time.time() - 10 if due else time.time() + 86400
    data = {"xp": 500, "missions": {}, "streak": 0, "best_streak": 0, "dojo_best": 0, "settings": {"bell": False},
            "keys": {k: {"box": 2, "due": t} for k in keys}}
    with open(os.path.join(home, "progress.json"), "w") as f:
        json.dump(data, f)


def t_sandbox(g):
    g.wait_title("SANDBOX")
    time.sleep(1)
    g.prefix("v")
    g.wait_hud("split right")
    g.prefix("%")
    g.wait_hud("tmux's split side by side")
    g.prefix("z")
    g.wait_hud("zoom")


def t_hints(g):
    g.close_card()  # panes card (starting at 1.1)
    g.wait_title("1.1 ")
    g.cmd("herdling hint", delay=1.5)
    g.wait_hud("Prefix first")
    g.wait_screen("Prefix first")          # printed in the pane too
    g.cmd("herdling hint", delay=1.5)
    g.wait_hud("ctrl+b")
    g.cmd("herdling task", delay=1)
    g.wait_screen("Split this pane into left | right")
    g.prefix("v")
    g.wait(lambda: g.stars("1.1") == 1, 20, "a hinted clear to give 1 star")


def t_show(g):
    g.close_card()
    g.wait_title("1.1 ")
    g.cmd("herdling show", delay=1)
    g.wait_hud("That's how")
    time.sleep(2.5)       # the demo resets the step afterwards
    g.prefix("v")
    g.wait(lambda: g.stars("1.1") == 1, 20, "a shown clear to give 1 star")
    assert g.progress()["missions"]["1.1"]["xp"] == 0


def t_skip_reset(g):
    g.close_card()
    g.wait_title("1.1 ")
    g.cmd("herdling skip", delay=1.5)
    g.wait_title("1.2 ")
    assert g.progress()["missions"]["1.1"]["skipped"]
    g.prefix("v")   # wrong split, then reset puts it back to one pane
    g.wait(lambda: len(g.pane_ids()) == 2, 5, "the extra pane")
    g.cmd("herdling reset", delay=1.5)
    g.wait(lambda: len(g.pane_ids()) == 1, 10, "reset to one pane")
    g.prefix("-")
    g.wait_done("1.2")


def t_menu(g):
    g.close_card()
    g.wait_title("1.1 ")
    g.cmd("herdling menu", delay=1)
    g.wait_screen("Progress saved", timeout=15)
    g.wait(lambda: not os.path.exists(os.path.join(g.home, "x", "herdr", "herdr.sock")) or not _alive(g), 10,
           "the game's Herdr server to stop")


def _alive(g):
    try:
        g.call("ping")
        return True
    except Exception:
        return False


def t_outside(g):
    g.close_card()
    g.wait_title("1.1 ")
    g.prefix("q")
    g.wait_screen("outside Herdr")
    outside(g, "echo real-$((6*7))")
    g.wait_screen("real-42")
    g.type("herdr update", delay=1.0)     # plain commands don't signal a prompt: type straight on
    g.wait_screen("isn't available while you're playing")
    outside(g, "herdr status", delay=1.5)
    g.wait_screen("running")
    outside(g, "herdr", delay=1.5)
    g.wait_hud("1.1 Side by side")
    g.prefix("v")
    g.wait_done("1.1")


def round_over(g):
    screen = g.screen()
    return "Time!" in screen or "Round over" in screen


def t_dojo(g):
    g.close_card()   # dojo intro
    g.wait_title("DOJO")
    end = time.time() + 20
    solved = 0
    while time.time() < end and "Round over" not in g.screen():
        prompt = g.runtime().get("prompt", "")
        before = prompt
        if "Move one pane" in prompt:
            g.prefix({"LEFT": "h", "RIGHT": "l", "UP": "k", "DOWN": "j"}[prompt.split()[-1].rstrip("!")])
        elif "RIGHT" in prompt:
            g.prefix("v")
        elif "BELOW" in prompt:
            g.prefix("-")
        elif "Unzoom" in prompt or prompt == "Zoom!":
            g.prefix("z")
        elif "New tab" in prompt:
            g.prefix("c")
            g.keys("Enter")
        elif "Next tab" in prompt:
            g.prefix("n")
        elif "Close this pane" in prompt:
            g.prefix("x")
        else:
            time.sleep(0.3)
            continue
        solved += 1
        g.wait(lambda: g.runtime().get("prompt") != before or round_over(g), 8, f"drill {before!r} to pass")
        if round_over(g):
            break
    g.wait(lambda: round_over(g), 20, "the round to end")
    if "Time!" in g.screen():
        g.close_card()
    assert g.progress()["dojo_best"] > 0, "dojo score was saved"
    assert solved >= 3


def t_review(g):
    g.close_card()   # review intro
    g.wait_title("REVIEW")
    for _ in range(2):
        prompt = g.runtime().get("prompt", "")
        g.wait(lambda: g.runtime().get("prompt"), 5, "a review prompt")
        prompt = g.runtime().get("prompt", "")
        if "RIGHT" in prompt:
            g.prefix("v")
        elif "BELOW" in prompt:
            g.prefix("-")
        g.wait(lambda: g.runtime().get("prompt") != prompt or "Review done" in g.screen(), 10, "next prompt")
    g.close_card(timeout=15)  # review done
    keys = g.progress()["keys"]
    assert keys["split-right"]["box"] == 3 and keys["split-down"]["box"] == 3, keys


def t_title_menu(g):
    g.wait_screen("learn Herdr by playing it", timeout=10)
    g.wait_screen("Continue: 0.1 Just a terminal")
    g.keys("Down", "Enter")   # World select
    g.wait_screen("World 10: Final Boss")
    g.keys("Escape")
    g.keys("q")
    time.sleep(1)
    assert "learn Herdr" not in g.screen()


TESTS = {
    "sandbox": (t_sandbox, ("sandbox",), None),
    "hints": (t_hints, ("play", "1.1"), None),
    "show": (t_show, ("play", "1.1"), None),
    "skip": (t_skip_reset, ("play", "1.1"), None),
    "menu": (t_menu, ("play", "1.1"), None),
    "outside": (t_outside, ("play", "1.1"), None),
    "dojo": (t_dojo, ("dojo",), {"HERDLING_DOJO_SECS": "15"}),
    "review": (t_review, ("review",), None),
    "title": (t_title_menu, (), None),
}


def run(name):
    fn, args, env = TESTS[name]
    home = None
    if name == "review":
        import tempfile
        home = tempfile.mkdtemp(prefix="hl-review-", dir="/tmp")
        seed_progress(home, ["split-right", "split-down"])
    g = Game(f"m-{name}", args=args, env=env, home=home)
    ok = False
    try:
        fn(g)
        print(f"{name}: OK")
        ok = True
    except AssertionError as e:
        print(f"{name}: FAILED\n{e}")
    finally:
        if not ok:
            g.save_evidence()
        g.close()
        if home:
            import shutil
            shutil.rmtree(home, ignore_errors=True)
    return ok


def main(argv):
    names = argv or list(TESTS)
    if len(names) == 1:
        sys.exit(0 if run(names[0]) else 1)
    procs = {n: subprocess.Popen([sys.executable, __file__, n], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True) for n in names}
    ok = True
    for n, p in procs.items():
        out = p.communicate()[0]
        print(out, end="")
        ok &= p.returncode == 0
    print("ALL OK" if ok else "SOME FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
