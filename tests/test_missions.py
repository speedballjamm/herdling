"""End-to-end: play every mission with real keystrokes and check each one clears.

    python3 tests/test_missions.py            # all worlds, in parallel
    python3 tests/test_missions.py 1 5        # just worlds 1 and 5
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game  # noqa: E402


def step(g, n, total):
    g.wait_title(f"({n}/{total})")


def mission(g, mid):
    g.wait_title(f"{mid} ")


def geom(g):
    """{pane_id: rect} for the focused tab."""
    return {p["pane_id"]: p["rect"] for p in g.layout()["panes"]}


def pane_at(g, which):
    """Pane id in a corner of the focused tab: tl tr bl br."""
    r = geom(g)
    minx = min(v["x"] for v in r.values())
    maxr = max(v["x"] + v["width"] for v in r.values())
    miny = min(v["y"] for v in r.values())
    maxb = max(v["y"] + v["height"] for v in r.values())
    for pid, v in r.items():
        h = v["x"] == minx if which[1] == "l" else v["x"] + v["width"] == maxr
        vv = v["y"] == miny if which[0] == "t" else v["y"] + v["height"] == maxb
        if h and vv:
            return pid
    return None


def screen_xy(g, pane_id):
    """Screen cell (1-based) roughly in the middle of a pane, for clicking."""
    lay = g.layout()
    rect = next(p["rect"] for p in lay["panes"] if p["pane_id"] == pane_id)
    cols = int(g.run_outer("display", "-p", "#{pane_width}").stdout.strip())
    side = cols - lay["area"]["width"]
    top = 1  # tab bar row
    return side + rect["x"] + rect["width"] // 2 + 1, top + rect["y"] + rect["height"] // 2 + 1


def label_xy(g, text, row_limit=None):
    """Screen cell of `text` (first match), 1-based."""
    for y, line in enumerate(g.screen().split("\n")):
        if row_limit is not None and y >= row_limit:
            break
        x = line.find(text)
        if x >= 0:
            return x + 1, y + 1
    return None


def goto_corner(g, which):
    """Move focus to a corner with prefix+h/j/k/l."""
    for _ in range(4):
        cur = g.snap()["focused_pane_id"]
        if cur == pane_at(g, which):
            return
        r = geom(g)[cur]
        tgt = geom(g)[pane_at(g, which)]
        if tgt["x"] < r["x"]:
            g.prefix("h")
        elif tgt["x"] > r["x"]:
            g.prefix("l")
        elif tgt["y"] < r["y"]:
            g.prefix("k")
        elif tgt["y"] > r["y"]:
            g.prefix("j")


# ------------------------------------------------------------------------------ worlds

def world0(g):
    g.close_card()  # welcome
    mission(g, "0.1")
    g.type("echo hello")
    g.wait_done("0.1")
    g.close_card()  # prefix
    mission(g, "0.2")
    g.keys("C-b")
    step(g, 2, 2)
    g.keys("Escape")
    g.wait_done("0.2")
    mission(g, "0.3")
    g.prefix("?")
    step(g, 2, 3)
    g.keys("/", "z", "o", "o", "m", delay=0.1)
    step(g, 3, 3)
    g.keys("Escape", "Escape")
    g.wait_done("0.3")
    g.close_card()  # mouse
    mission(g, "0.4")
    time.sleep(0.5)
    x, y = label_xy(g, "+", row_limit=1)
    g.click(x, y)
    g.keys("Enter", delay=0.5)
    step(g, 2, 2)
    x, y = label_xy(g, " 1 ", row_limit=1)
    g.click(x + 1, y)
    g.wait_done("0.4")


def world1(g):
    g.close_card()  # panes
    mission(g, "1.1")
    g.prefix("-")   # wrong split first: coaching
    g.wait_hud("prefix+minus")
    g.prefix("v")
    g.wait_done("1.1")
    mission(g, "1.2")
    g.prefix("-")
    g.wait_done("1.2")
    mission(g, "1.3")
    g.prefix("Left")  # tmux habit
    g.wait_hud("tmux")
    g.prefix("h")
    step(g, 2, 2)
    g.prefix("l")
    g.wait_done("1.3")
    mission(g, "1.4")
    for i, corner in enumerate(["tl", "br", "tr", "bl"]):
        step(g, i + 1, 4)
        time.sleep(0.3)
        goto_corner(g, corner)
    g.wait_done("1.4")
    mission(g, "1.5")
    for _ in range(3):
        g.prefix("Tab")
    g.wait_done("1.5")
    g.close_card()  # close
    mission(g, "1.6")
    g.prefix("x")
    step(g, 2, 2)
    g.cmd("exit")
    g.wait_done("1.6")
    mission(g, "1.7")
    g.prefix("P")
    g.type("server", delay=0.6)
    g.wait_done("1.7")
    mission(g, "1.8")
    time.sleep(0.6)
    pid = next(p["pane_id"] for p in g.snap()["panes"] if p.get("label") == "C")
    g.click(*screen_xy(g, pid))
    g.wait_done("1.8")
    mission(g, "1.9")
    g.prefix("v")
    g.prefix("-")
    g.prefix("h")
    g.prefix("-")
    for i, corner in enumerate(["tl", "br", "tr", "bl"]):
        step(g, i + 2, 5)
        time.sleep(0.3)
        goto_corner(g, corner)
    g.wait_done("1.9")


def divider_x(g):
    """Screen column (1-based) of the vertical border between two side-by-side panes."""
    for line in g.screen().split("\n")[1:4]:
        x = line.find("┐┌")
        if x >= 0:
            return x + 1
    return None


def world2(g):
    g.close_card()  # pane power
    mission(g, "2.1")
    g.prefix("z")
    step(g, 2, 2)
    g.prefix("z")
    g.wait_done("2.1")
    g.close_card()  # resize
    mission(g, "2.2")
    g.prefix("r")
    g.keys("l", "l", "l", "l", delay=0.2)
    step(g, 2, 2)
    g.keys("Escape")
    g.wait_done("2.2")
    mission(g, "2.3")
    time.sleep(0.6)
    x = divider_x(g)
    g.drag(x, 15, x - 30, 15)
    g.wait_done("2.3")
    mission(g, "2.4")
    g.prefix("L")
    step(g, 2, 2)
    g.prefix("H")
    g.wait_done("2.4")
    mission(g, "2.5")
    g.prefix("b")
    step(g, 2, 2)
    g.prefix("b")
    g.wait_done("2.5")
    g.close_card()  # blueprint
    mission(g, "2.6")
    g.prefix("v")
    g.prefix("-")
    g.prefix("-")
    step(g, 2, 3)
    g.prefix("r")
    g.keys("l", "l", "l", "Escape", delay=0.2)
    step(g, 3, 3)
    goto_corner(g, "br")
    g.prefix("z")
    g.wait_done("2.6")


def world3(g):
    g.close_card()  # tabs
    mission(g, "3.1")
    g.prefix("c")
    g.type("logs", delay=0.5)
    g.wait_done("3.1")
    mission(g, "3.2")
    g.prefix("n")
    step(g, 2, 3)
    g.prefix("n")
    step(g, 3, 3)
    g.prefix("p")
    g.wait_done("3.2")
    mission(g, "3.3")
    g.prefix("3")
    step(g, 2, 2)
    g.prefix("1")
    g.wait_done("3.3")
    mission(g, "3.4")
    g.prefix("T")
    g.keys("C-u")
    g.type("api", delay=0.5)
    g.wait_done("3.4")
    mission(g, "3.5")
    g.prefix("X")
    g.wait_done("3.5")
    mission(g, "3.6")
    time.sleep(0.6)
    x, y = label_xy(g, "server", row_limit=1)
    g.click(x + 1, y)
    g.wait_done("3.6")
    mission(g, "3.7")
    g.prefix("T")
    g.keys("C-u")
    g.type("code", delay=0.4)
    g.prefix("c")
    g.type("server", delay=0.4)
    g.prefix("c")
    g.type("logs", delay=0.4)
    step(g, 2, 5)
    g.prefix("2")
    step(g, 3, 5)
    g.prefix("n")
    step(g, 4, 5)
    g.prefix("T")
    g.keys("C-u")
    g.type("tail", delay=0.4)
    step(g, 5, 5)
    g.prefix("1")
    g.wait_done("3.7")


def world4(g):
    g.close_card()  # workspaces
    mission(g, "4.1")
    g.prefix("N")
    step(g, 2, 2)
    g.prefix("W")
    g.keys("C-u")
    g.type("api", delay=0.5)
    g.wait_done("4.1")
    g.close_card()  # navigate
    mission(g, "4.2")
    g.prefix("w")
    g.keys("Down", "Down", "Enter")
    step(g, 2, 2)
    g.prefix("w")
    g.keys("1")
    g.wait_done("4.2")
    mission(g, "4.3")
    g.prefix("g")
    g.keys("/")
    g.type("secret", enter=False)
    g.keys("Down", "Down", "Enter")
    g.wait_done("4.3")
    mission(g, "4.4")
    g.prefix("D")
    g.keys("Enter")
    g.wait_done("4.4")
    mission(g, "4.5")
    time.sleep(0.6)
    x, y = label_xy(g, "backend")
    g.click(x + 1, y)
    g.wait_done("4.5")
    mission(g, "4.6")
    time.sleep(0.5)
    g.prefix("w")
    g.keys("2")
    g.prefix("2")
    step(g, 2, 4)
    g.prefix("N")
    g.prefix("W")
    g.keys("C-u")
    g.type("docs", delay=0.5)
    step(g, 3, 4)
    names = [w["label"] for w in sorted(g.snap()["workspaces"], key=lambda w: w["number"])]
    g.prefix("w")
    g.keys(str(names.index("db") + 1))
    g.prefix("D")
    g.keys("Enter")
    step(g, 4, 4)
    g.prefix("w")
    g.keys("1")
    g.prefix("1")
    g.wait_done("4.6")


def wait_agent(g, name, *states, timeout=30):
    g.wait(lambda: g.agents().get(name, {}).get("agent_status") in states, timeout, f"{name} to be {states}")


def world5(g):
    g.close_card()  # agents
    mission(g, "5.1")
    wait_agent(g, "claude", "blocked")
    g.prefix("l")
    g.type("y", delay=0.6)
    step(g, 2, 2)
    g.wait_done("5.1", timeout=30)
    mission(g, "5.2")
    wait_agent(g, "codex", "blocked")
    g.wait_screen("needs attention", timeout=10)
    g.prefix("o")
    step(g, 2, 2)
    g.type("y", delay=0.6)
    g.wait_done("5.2")
    mission(g, "5.3")
    wait_agent(g, "gemini", "working")
    time.sleep(0.5)
    x, y = label_xy(g, "gemini")
    g.click(x + 1, y)
    g.wait_done("5.3")
    mission(g, "5.4")
    g.wait_title("(2/2)", timeout=30)
    time.sleep(0.5)
    x, y = label_xy(g, "  pi ")
    g.click(x + 3, y)
    g.wait_done("5.4")
    mission(g, "5.5")
    answered = set()
    end = time.time() + 120
    while len(answered) < 4 and time.time() < end:
        blocked = [n for n, a in g.agents().items() if a["agent_status"] == "blocked" and n not in answered]
        if blocked:
            g.prefix("o", delay=0.6)
            focused = g.snap()["focused_pane_id"]
            who = [n for n, a in g.agents().items() if a["pane_id"] == focused]
            if who and who[0] in blocked:
                g.type("y", delay=0.8)
                answered.add(who[0])
            else:   # the notice went to someone else: go there directly
                g.call("pane.focus", pane_id=g.agents()[blocked[0]]["pane_id"])
                time.sleep(0.3)
                g.type("y", delay=0.8)
                answered.add(blocked[0])
        time.sleep(0.4)
    g.wait_done("5.5", timeout=40)


def outside(g, text, delay=1.0):
    """Type a command into your shell while detached, once it's at a prompt."""
    ready = os.path.join(g.home, "run", "outside-ready")
    g.wait(lambda: os.path.exists(ready), 20, "the shell outside Herdr")
    os.remove(ready)
    time.sleep(0.3)
    g.type(text, delay=delay)


def world6(g):
    g.close_card()  # sessions
    g.close_card()  # detach
    mission(g, "6.1")
    g.prefix("q")
    step(g, 2, 2)
    outside(g, "herdr")
    g.wait_done("6.1")
    mission(g, "6.2")
    time.sleep(0.5)
    g.prefix("q")
    outside(g, "herdr session list")
    step(g, 2, 2)
    outside(g, "herdr")
    g.wait_done("6.2")
    g.close_card()  # named sessions
    mission(g, "6.3")
    time.sleep(0.5)
    g.prefix("q")
    outside(g, "herdr session attach work", delay=2)
    step(g, 2, 5)
    time.sleep(1)
    g.prefix("q")
    step(g, 3, 5)
    outside(g, "herdr session list")
    step(g, 4, 5)
    outside(g, "herdr session stop work", delay=1.5)
    step(g, 5, 5)
    outside(g, "herdr")
    g.wait_done("6.3")
    mission(g, "6.4")
    time.sleep(1)
    g.prefix("q")
    outside(g, "herdr session delete work", delay=1.5)
    step(g, 2, 2)
    outside(g, "herdr")
    g.wait_done("6.4")
    mission(g, "6.5")
    time.sleep(0.5)
    g.prefix("q")
    step(g, 2, 3)
    outside(g, "herdr session list")
    step(g, 3, 3)
    outside(g, "herdr", delay=1.5)
    g.wait(lambda: "code word is:" in g.read(g.pane_labelled("job")), 60, "the job to finish")
    text = g.read(g.pane_labelled("job"))
    code = text.split("code word is:")[1].split()[0]
    g.cmd(f"herdling answer {code}")
    g.wait_done("6.5")


def secret_in(g, label, marker):
    text = g.read(g.pane_labelled(label), lines=2000)
    return text.split(marker)[1].split()[0]


def world7(g):
    g.close_card()  # copy
    mission(g, "7.1")
    g.prefix("[")
    step(g, 2, 2)
    g.keys("C-u", "C-u", "C-u", "q", delay=0.2)
    g.cmd(f"herdling answer {secret_in(g, 'server-log', 'SECRET: ')}")
    g.wait_done("7.1")
    mission(g, "7.2")
    time.sleep(0.8)
    g.prefix("[")
    g.keys("?")
    g.type("PASSWORD", delay=0.4)
    g.keys("q")
    g.cmd(f"herdling answer {secret_in(g, 'server-log', 'PASSWORD: ')}")
    g.wait_done("7.2")
    mission(g, "7.3")
    time.sleep(0.8)
    g.prefix("[")
    g.keys("g")
    g.keys("/")
    g.type("WARN", delay=0.4)
    g.keys("q")
    text = g.read(g.pane_labelled("disk-log"), lines=400)
    g.cmd(f"herdling answer {next(l for l in text.splitlines() if ' WARN ' in l).split()[2]}")
    g.wait_done("7.3")
    mission(g, "7.4")
    time.sleep(0.8)
    code = secret_in(g, "from", "copy-me: ")
    g.prefix("[")
    g.keys("?")
    g.type("copy-me", delay=0.4)
    g.keys("W", "v", "E", "y", delay=0.3)
    g.wait(lambda: code in g.clipboard(), 10, "the copy to reach the clipboard")
    step(g, 2, 2)
    g.prefix("l")
    g.paste(g.clipboard())
    g.keys("Enter")
    assert_filed(g, "to", code)
    g.wait_done("7.4")
    mission(g, "7.5")
    time.sleep(0.8)
    code = secret_in(g, "notes", "deploy code is ")
    x, y = label_xy(g, code)
    g.drag(x, y, x + len(code) - 1, y)
    g.wait_done("7.5")
    mission(g, "7.6")
    g.wait(lambda: "stream ended" in g.read(g.pane_labelled("incident"), lines=400), 60, "incident log")
    text = g.read(g.pane_labelled("incident"), lines=400)
    first = next(l for l in text.splitlines() if " ERROR " in l).split()[2]
    g.prefix("[")
    g.keys("g")
    g.keys("/")
    g.type("ERROR", delay=0.4)
    g.keys("W", "v", "E", "y", delay=0.3)
    g.wait(lambda: first in g.clipboard(), 10, "the copy to reach the clipboard")
    g.prefix("l")
    g.paste(g.clipboard())
    g.keys("Enter")
    assert_filed(g, "ticket", first)
    g.wait_done("7.6")


def assert_filed(g, label, code):
    """The paste landed in an inbox, not a shell (which says "command not found")."""
    pane = g.pane_labelled(label)
    g.wait(lambda: f"filed: {code}" in g.read(pane, lines=50), 5, f"the {label} pane to file {code}")
    assert "not found" not in g.read(pane, lines=50), f"[{g.name}] {label} pane ran the paste as a command"


def world8(g):
    g.close_card()  # cli
    mission(g, "8.1")
    g.cmd("herdr pane current")
    step(g, 2, 2)
    g.cmd("herdr workspace list")
    g.wait_done("8.1")
    mission(g, "8.2")
    g.cmd("herdr pane split --current --direction right --no-focus")
    g.wait_done("8.2")
    mission(g, "8.3")
    time.sleep(0.5)
    g.cmd("herdr pane list")
    g.cmd(f'herdr pane run {g.pane_labelled("target")} "echo hi from afar"')
    g.wait_done("8.3")
    mission(g, "8.4")
    time.sleep(0.8)
    vault = g.pane_labelled("vault")
    g.cmd(f"herdr pane read {vault}")
    code = g.read(vault).split("code: ")[1].split()[0]
    g.cmd(f"herdling answer {code}")
    g.wait_done("8.4")
    mission(g, "8.5")
    g.cmd("herdr tab create --label build")
    g.wait_done("8.5")
    mission(g, "8.6")
    g.cmd('herdr notification show "coffee break"')
    g.wait_done("8.6")
    mission(g, "8.7")
    time.sleep(0.5)
    g.cmd("herdr tab create --label fleet")
    tab = next(t for t in g.snap()["tabs"] if t["label"] == "fleet")
    root = next(p["pane_id"] for p in g.snap()["panes"] if p["tab_id"] == tab["tab_id"])
    g.cmd(f"herdr pane split {root} --direction right")
    g.cmd(f"herdr pane split {root} --direction right")
    ids = [p["pane_id"] for p in g.snap()["panes"] if p["tab_id"] == tab["tab_id"]]
    for pid in ids[:2]:
        g.cmd(f'herdr pane run {pid} "echo ready"')
    g.wait_done("8.7")


def conf_edit(g, fn):
    path = os.path.join(g.home, "config.toml")
    with open(path) as f:
        text = f.read()
    with open(path, "w") as f:
        f.write(fn(text))


def world9(g):
    g.close_card()  # config
    mission(g, "9.1")
    conf_edit(g, lambda t: t.replace('# name = "catppuccin"', 'name = "tokyo-night"'))
    g.prefix("R")
    g.wait_done("9.1")
    mission(g, "9.2")
    conf_edit(g, lambda t: t.replace('[keys]\n', '[keys]\nlast_pane = "prefix+semicolon"\n'))
    time.sleep(1.2)
    g.prefix("R")
    step(g, 2, 2)
    time.sleep(1.2)
    g.prefix("l")
    g.prefix(";")
    g.wait_done("9.2")
    mission(g, "9.3")
    conf_edit(g, lambda t: t.replace('# tab_bar_right = []', 'tab_bar_right = [{ type = "datetime", format = "%H:%M" }]'))
    g.prefix("R")
    g.wait_done("9.3")
    mission(g, "9.4")
    conf_edit(g, lambda t: t.replace('[keys]\n', '[keys]\nzoom = ["prefix+z", "ctrl+alt+z"]\n'))
    g.prefix("R")
    time.sleep(1.2)
    g.keys("C-M-z")
    g.wait_done("9.4")
    mission(g, "9.5")
    g.cmd("herdling install", delay=1)
    g.type("n", delay=1)
    g.wait_done("9.5")


def world10(g):
    g.close_card()  # final
    mission(g, "10.1")
    g.prefix("N")
    g.prefix("W")
    g.keys("C-u")
    g.type("shop", delay=0.5)
    step(g, 2, 8)
    g.prefix("T")
    g.keys("C-u")
    g.type("code", delay=0.4)
    g.prefix("c")
    g.type("server", delay=0.5)
    step(g, 3, 8)
    g.prefix("1")
    g.prefix("v")
    step(g, 4, 8)
    wait_agent(g, "claude", "blocked", timeout=30)
    g.prefix("h")
    g.type("y", delay=0.6)
    step(g, 5, 8)
    srv = next(t for t in g.snap()["tabs"] if t["label"] == "server")
    logs = g.layout_of(srv["tab_id"])["panes"][0]["pane_id"]
    g.wait(lambda: "stream ended" in g.read(logs, lines=400), 60, "incident log")
    first = next(l for l in g.read(logs, lines=400).splitlines() if " ERROR " in l).split()[2]
    g.prefix("l")
    g.cmd(f"herdling answer {first}")
    step(g, 6, 8)
    g.prefix("q")
    step(g, 7, 8)
    outside(g, "herdr", delay=1.5)
    step(g, 8, 8)
    g.prefix("1")
    g.prefix("h")
    g.prefix("z")
    g.wait_done("10.1")


WORLDS = {0: world0, 1: world1, 2: world2, 3: world3, 4: world4, 5: world5, 6: world6, 7: world7, 8: world8,
          9: world9, 10: world10}
START = {n: f"{n}.1" for n in WORLDS}


def run_world(n):
    args = ("play",) if n == 0 else ("play", START[n])
    g = Game(f"w{n}", args=args, clipboard=(n == 7))
    ok = False
    try:
        WORLDS[n](g)
        print(f"world {n}: OK")
        ok = True
    except AssertionError as e:
        print(f"world {n}: FAILED\n{e}")
    finally:
        if not ok:
            g.save_evidence()
        g.close()
    return ok


def main(argv):
    worlds = [int(a) for a in argv] or sorted(WORLDS)
    if len(worlds) == 1:
        sys.exit(0 if run_world(worlds[0]) else 1)
    procs = {n: subprocess.Popen([sys.executable, __file__, str(n)], stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True) for n in worlds}
    ok = True
    for n, p in procs.items():
        out = p.communicate()[0]
        print(out, end="")
        ok &= p.returncode == 0
    print("ALL OK" if ok else "SOME FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
