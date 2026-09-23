"""The `herdling` command.

Outside the game:   herdling [play [MISSION] | dojo | review | sandbox | cheat | status | help]
Inside the game:    herdling task | hint | skip | show | reset | card | edit | install | answer WORD | again | menu
"""
import json
import os
import sys
import time

from . import paths, progress
from .keys import KEYS

IN_GAME_HELP = """\
herdling, in-game commands (type them in any shell pane):

  herdling task           reprint the current task (and hints so far) in this pane
  herdling hint           a hint (the first is free, later ones halve the XP)
  herdling show           watch the game do it, then try yourself
  herdling skip           skip this mission (come back later from the menu)
  herdling reset          set the current step up again
  herdling card           re-open the lesson card
  herdling edit           open your practice config.toml in your editor
  herdling install        make your practice config your real Herdr config (asks first)
  herdling answer WORD    answer a question the game asked
  herdling again          another Dojo round
  herdling cheat          print your cheat sheet
  herdling menu           quit to the title menu (progress is saved)
"""

OUT_HELP = """\
usage: ./herdling [command]

  (nothing)        title menu
  play [ID]        jump straight into the campaign (optionally at a mission, e.g. 2.3)
  dojo             60-second speed drills
  review           spaced-repetition review of keys you've learned
  sandbox          free play with live explanations
  cheat [--all]    print your cheat sheet (--all includes keys you haven't learned yet)
  status           your progress
  install          copy your practice config to ~/.config/herdr/config.toml (asks first, backs up)
  about            version, credits, where to report problems
"""

GAME_CMDS = {"hint", "skip", "show", "reset", "card", "again", "menu"}


def in_game():
    return os.environ.get("HERDLING_GAME") == "1"


def runtime():
    try:
        with open(paths.RUNTIME) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def show_task(before=None, wait=0.0):
    """Print the current task (and any hints so far) here in the pane, where it stays
    on screen while you type. The HUD only ever shows the newest line."""
    r = runtime()
    if wait:
        deadline = time.time() + wait
        while time.time() < deadline and r.get("hints", []) == (before or []):
            time.sleep(0.1)
            r = runtime()
    b = (lambda s: f"\x1b[1m{s}\x1b[0m") if sys.stdout.isatty() else (lambda s: s)
    title, prompt = r.get("title", ""), r.get("prompt", "")
    if not prompt:
        return False
    print(f"\n{b('▶ ' + title if title else '▶ task')}\n  {prompt}")
    for h in r.get("hints", []):
        print(f"  {b('»')} {h}")
    print()
    return True


def send(event):
    paths.ensure()
    event["t"] = time.time()
    with open(paths.EVENTS, "a") as f:
        f.write(json.dumps(event) + "\n")


def cheat_sheet(show_all=False, color=True):
    data = progress.load()
    learned = set(data["keys"])
    b = (lambda s: f"\x1b[1;38;5;214m{s}\x1b[0m") if color else (lambda s: s)
    dim = (lambda s: f"\x1b[38;5;244m{s}\x1b[0m") if color else (lambda s: s)
    out = ["Herdr cheat sheet" + ("" if show_all else "  (keys you've learned; --all for everything)"),
           "prefix = ctrl+b: hold Ctrl, tap b, let go. Then press the action key on its own.", ""]
    group = None
    for k in KEYS:
        mark = k.id in learned
        if not show_all and not mark:
            continue
        if k.group != group:
            group = k.group
            out.append(b(f"── {group} " + "─" * (50 - len(group))))
        line = f"  {k.keys:<26} {k.desc}"
        out.append(line if mark or not show_all else dim(line))
    if len(out) == 3:
        out.append("Nothing learned yet! Play a few missions, or use --all.")
    out += ["", "Everything else: prefix+? inside Herdr, `herdr --help` in a shell, https://herdr.dev/docs/"]
    return "\n".join(out)


def status():
    from .worlds import WORLDS
    d = progress.load()
    print(f"Rank: {progress.rank(d, WORLDS)}   XP: {d['xp']}   Best streak: {d['best_streak']}   "
          f"Dojo best: {d['dojo_best']}")
    for w in WORLDS:
        done = sum(progress.completed(d, m.id) for m in w.missions)
        print(f"  World {w.num}  {w.title:<24} {done}/{len(w.missions)}")
    print(f"Keys due for review: {len(progress.due_keys(d))}")


def about(short=False):
    import game
    if short:
        print(f"herdling {game.__version__}")
        return
    print(f"herdling {game.__version__}: learn Herdr by playing it.\n"
          f"Made by James Moult. MIT licensed. Not affiliated with Herdr, Inc.\n\n"
          f"  Home & problems   {game.URL}/issues\n"
          f"  Say thanks        {game.SPONSOR}")


def edit_config():
    from . import conf
    conf.ensure()
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "nano"
    os.execvp("sh", ["sh", "-c", f'{editor} "$1"', "sh", paths.CONFIG])


def main(argv):
    cmd = argv[0] if argv else ""
    if cmd in ("-h", "--help", "help"):
        print(IN_GAME_HELP if in_game() else OUT_HELP)
        return
    if cmd == "cheat":
        print(cheat_sheet("--all" in argv, color=sys.stdout.isatty()))
        return
    if cmd == "status":
        status()
        return
    if cmd in ("about", "--version", "-V", "version"):
        about(short=cmd != "about")
        return
    if cmd == "install":
        from . import graduate
        result = graduate.main()
        if in_game():
            send({"type": "install", "done": result})
        return
    if in_game():
        if cmd == "edit":
            edit_config()
        if cmd == "task":
            if not show_task():
                print("No task right now.")
            return
        if cmd in GAME_CMDS:
            before = runtime().get("hints", [])
            send({"type": "cmd", "cmd": cmd})
            if cmd == "hint":
                if not show_task(before, wait=2.5):
                    print("Hint on its way: look at the bar at the bottom.")
                return
            print({"skip": "Skipping…", "show": "Watch the screen!", "reset": "Resetting…",
                   "card": "Opening the card…", "again": "Here we go!",
                   "menu": "Back to the menu. Progress is saved."}[cmd])
        elif cmd == "answer":
            send({"type": "answer", "text": " ".join(argv[1:])})
            print("Answer sent: look at the bar at the bottom.")
        else:
            print(IN_GAME_HELP)
        return
    from . import launcher
    if cmd in ("", "menu"):
        launcher.menu()
    elif cmd in ("play", "campaign"):
        start = argv[1].strip().rstrip(".") if len(argv) > 1 else None
        if start:
            from .worlds import find
            if not find(start):
                print(f"There's no mission {argv[1]!r}. Missions look like 2.3 (world 2, mission 3); "
                      f"`herdling status` lists the worlds.")
                sys.exit(1)
        launcher.play("campaign", start)
    elif cmd in ("dojo", "review", "sandbox"):
        launcher.play(cmd)
    else:
        print(OUT_HELP)


if __name__ == "__main__":
    main(sys.argv[1:])
