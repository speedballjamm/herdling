"""Title menu, starting the game's Herdr server, attaching, and your shell while detached."""
import curses
import logging
import os
import shutil
import subprocess
import sys
import time

from . import cli, conf, herdr, outside, paths, progress
from .hud import Hud
from .proxy import Proxy

LOGO = r"""
  _                   _ _ _
 | |__   ___ _ __ __| | (_)_ __   __ _
 | '_ \ / _ \ '__/ _` | | | '_ \ / _` |
 | | | |  __/ | | (_| | | | | | | (_| |
 |_| |_|\___|_|  \__,_|_|_|_| |_|\__, |
                                 |___/
""".strip("\n")

B = "\x1b[1m"
Y = "\x1b[38;5;214m"
C = "\x1b[38;5;117m"
G = "\x1b[38;5;78m"
DIM = "\x1b[38;5;244m"
R = "\x1b[0m"

MIN_VERSION = (0, 9, 0)

# ------------------------------------------------------------------ checks

def preflight():
    v = herdr.version()
    if v is None:
        print("Herdr isn't installed. Install it with:")
        print("   curl -fsSL https://herdr.dev/install.sh | sh      (or: brew install herdr)")
        return False
    if v < MIN_VERSION:
        print(f"herdling needs Herdr {'.'.join(map(str, MIN_VERSION))} or newer (you have "
              f"{'.'.join(map(str, v))}). Try: herdr update")
        return False
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("herdling needs a real terminal.")
        return False
    cols, rows = shutil.get_terminal_size((80, 24))
    if cols < 80 or rows < 24:
        print(f"{Y}Your terminal is {cols}×{rows}. herdling needs at least 80×24; 110×32 or larger is nicer.{R}")
        print("Make the window bigger (or zoom out), then press Enter…")
        input()
    if os.environ.get("HERDR_ENV") == "1":
        print(f"{Y}You're already inside Herdr!{R} Herdr won't start inside one of its own panes.")
        print("Open a plain terminal window (outside Herdr) and run ./herdling there.")
        return False
    if os.environ.get("TMUX"):
        print(f"{Y}You're inside tmux.{R} Herdr works inside tmux, but tmux eats ctrl+b (its own prefix),")
        print("so you'd have to press it twice. A plain terminal window is much better.")
        if input("Continue anyway? [y/N] ").strip().lower() != "y":
            return False
    return True


# ------------------------------------------------------------------ playing

def stop_everything(h):
    """Stop every server in the sandbox: the game's own, and any practice sessions."""
    for s in herdr.sessions():
        if s.get("running") and s.get("name") != "default":
            herdr.Herdr(s["name"]).stop_server()
    h.stop_server()


def attach(engine, hud, session=None):
    """Attach a Herdr client (through the HUD proxy). Returns when it exits."""
    argv = [herdr.herdr_bin()] + (["--session", session] if session and session != "default" else [])
    proxy = Proxy(argv, herdr.game_env(), hud, engine.on_input, cwd=os.path.expanduser("~"))
    engine.attached(proxy, session or "default")
    try:
        proxy.run()
    finally:
        engine.detached()


def play(mode="campaign", start=None):
    from .engine import Engine
    if not preflight():
        return
    paths.ensure()
    logging.basicConfig(filename=paths.LOG, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    conf.ensure()
    h = herdr.Herdr()
    stop_everything(h)
    if not h.start_server(os.path.join(paths.HOME, "server.out")):
        print("Couldn't start Herdr's server. Details in ~/.herdling/x/herdr/herdr-server.log")
        return
    if not (h.snapshot_raw() or {}).get("workspaces"):
        h.try_call("workspace.create", label="home", cwd=os.path.expanduser("~"), focus=True)
    for f in (paths.RUNTIME, paths.EVENTS):
        try:
            os.remove(f)
        except OSError:
            pass
    hud = Hud()
    engine = Engine(h, hud, mode, start, once=os.environ.get("HERDLING_ONCE") == "1")
    engine.start_thread()
    try:
        attach(engine, hud)
        if not engine.finished.is_set() and h.alive():
            outside_shell(engine, hud)
    finally:
        engine.stop.set()
        if engine.thread:
            engine.thread.join(timeout=3)
        stop_everything(h)
    print(f"\n{G}Progress saved.{R} Run ./herdling to play again.\n")


def outside_shell(engine, hud):
    """You've detached: your own shell, until you exit it or the game ends. `herdr` in it
    (bin/outside/herdr) asks us to attach; we borrow the terminal, then hand it back."""
    outside.await_engine()
    outside.banner()
    shell = outside.Shell()
    try:
        while shell.alive():
            if not engine.h.alive() or engine.finished.is_set():
                shell.end()
                print("\nThe game's Herdr server has stopped (that ends every pane in it). Back to the menu!"
                      if not engine.h.alive() else "\nBack to the menu. Progress is saved.")
                time.sleep(1.5)
                return
            req = shell.request()
            if req is None:
                time.sleep(0.1)
                continue
            outside.take_terminal()
            attach(engine, hud, req.get("session"))
            if engine.finished.is_set() or not engine.h.alive():
                continue
            shell.done(req.get("pgrp"))
    finally:
        shell.end()


# ------------------------------------------------------------------ menu

def world_unlocked(data, worlds, n):
    if data["settings"].get("unlock_all"):
        return True
    return progress.worlds_done(data, worlds) >= n


def continue_target(data, order):
    for m in order:
        if not progress.completed(data, m.id) and not m.bonus:
            return m
    return None


def menu():
    os.environ.setdefault("ESCDELAY", "25")
    if not sys.stdout.isatty():
        print(cli.OUT_HELP)
        return
    while True:
        choice = curses.wrapper(_menu_screen)
        if choice is None:
            return
        kind, arg = choice
        if kind == "play":
            play(*arg)
        elif kind == "cheat":
            text = cli.cheat_sheet(show_all=True)
            pager = shutil.which("less")
            if pager:
                subprocess.run([pager, "-R"], input=text.encode())
            else:
                print(text)
                input("\nPress Enter…")


def _menu_screen(scr):
    from .worlds import ORDER, WORLDS
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, 214, -1)
    curses.init_pair(2, 117, -1)
    curses.init_pair(3, 78, -1)
    curses.init_pair(4, 244, -1)
    curses.init_pair(5, 16, 214)
    ORANGE, CYAN, GREEN, GREY, SEL = (curses.color_pair(i) for i in range(1, 6))
    screen = "main"
    sel = 0
    world_sel = 0
    msg = ""
    while True:
        data = progress.load()
        due = len(progress.due_keys(data))
        scr.erase()
        h, w = scr.getmaxyx()

        def put(y, x, text, attr=0):
            if 0 <= y < h - 1 and x < w:
                try:
                    scr.addstr(y, x, text[:max(0, w - x - 1)], attr)
                except curses.error:
                    pass

        y = 1
        for line in LOGO.splitlines():
            put(y, 2, line, ORANGE | curses.A_BOLD)
            y += 1
        put(y, 3, "learn Herdr by playing it", GREY)
        y += 2
        put(y, 3, f"Rank: {progress.rank(data, WORLDS)}", CYAN | curses.A_BOLD)
        put(y, 34, f"XP: {data['xp']}   Streak: {data['streak']}   Dojo best: {data['dojo_best']}", CYAN)
        y += 2
        if screen == "main":
            nxt = continue_target(data, ORDER)
            items = [
                ("play", ("campaign", nxt.id if nxt else None),
                 f"Continue: {nxt.id} {nxt.title}" if nxt else "Campaign complete! Replay from the start"),
                ("worlds", None, "World select"),
                ("play", ("dojo",), "Dojo: 60-second speed drills"),
                ("play", ("review",), f"Review: {due} key{'s' if due != 1 else ''} due"),
                ("play", ("sandbox",), "Sandbox: free play with live explanations"),
                ("cheat", None, "Cheat sheet"),
                ("settings", None, "Settings"),
                ("quit", None, "Quit"),
            ]
            for i, (_, _, label) in enumerate(items):
                put(y + i, 3, (" ▶ " if i == sel else "   ") + label + " ", SEL if i == sel else 0)
            y += len(items) + 1
            for wd in WORLDS:
                done = sum(progress.completed(data, m.id) for m in wd.missions)
                bar = "█" * done + "░" * (len(wd.missions) - done)
                lock = "" if world_unlocked(data, WORLDS, wd.num) else "  (locked)"
                put(y, 3, f"{wd.num:>2} {wd.title:<24}", GREY if lock else 0)
                put(y, 31, bar, GREEN)
                put(y, 32 + len(bar), f"{done}/{len(wd.missions)}{lock}", GREY)
                y += 1
        elif screen == "worlds":
            put(y, 3, "Choose a world (Enter), Esc to go back", GREY)
            y += 1
            for i, wd in enumerate(WORLDS):
                ok = world_unlocked(data, WORLDS, wd.num)
                stars = sum(data["missions"].get(m.id, {}).get("stars", 0) for m in wd.missions)
                label = f"World {wd.num}: {wd.title:<26} ★ {stars}/{3 * len(wd.missions)}"
                put(y + i, 3, (" ▶ " if i == sel else "   ") + label + ("" if ok else "  locked") + " ",
                    SEL if i == sel else (GREY if not ok else 0))
            items = WORLDS
        elif screen == "missions":
            wd = WORLDS[world_sel]
            put(y, 3, f"World {wd.num}: {wd.title}. Enter plays from there, Esc goes back", GREY)
            y += 1
            items = wd.missions
            for i, m in enumerate(items):
                e = data["missions"].get(m.id, {})
                st = progress.stars_str(e.get("stars", 0))
                tag = " bonus" if m.bonus else ""
                best = f"  best {e['best']:.0f}s" if e.get("best") else ""
                label = f"{m.id:<5} {m.title:<30} {st}{tag}{best}"
                put(y + i, 3, (" ▶ " if i == sel else "   ") + label + " ", SEL if i == sel else 0)
        elif screen == "settings":
            items = [("bell", f"Bell on success: {'on' if data['settings'].get('bell', True) else 'off'}"),
                     ("unlock", f"Unlock all worlds: {'yes' if data['settings'].get('unlock_all') else 'no'}"),
                     ("reset", "Reset all progress"),
                     ("back", "Back")]
            for i, (_, label) in enumerate(items):
                put(y + i, 3, (" ▶ " if i == sel else "   ") + label + " ", SEL if i == sel else 0)
        if msg:
            put(h - 2, 3, msg, ORANGE)
        put(h - 1 if h > 1 else 0, 3, "↑↓ move · Enter choose · q quit", GREY)
        scr.refresh()
        k = scr.getch()
        msg = ""
        n = len(items)
        if k in (curses.KEY_UP, ord("k")):
            sel = (sel - 1) % n
        elif k in (curses.KEY_DOWN, ord("j")):
            sel = (sel + 1) % n
        elif k in (27, curses.KEY_BACKSPACE, 127, curses.KEY_LEFT) and screen != "main":
            back_to = {"missions": ("worlds", world_sel), "worlds": ("main", 1), "settings": ("main", 6)}
            screen, sel = back_to.get(screen, ("main", 0))
        elif k == ord("q") and screen == "main":
            return None
        elif k == ord("q"):
            screen, sel = {"worlds": ("main", 1), "settings": ("main", 6)}.get(screen, ("worlds", world_sel))
        elif k in (10, 13, curses.KEY_ENTER, curses.KEY_RIGHT):
            if screen == "main":
                kind, arg, _ = items[sel]
                if kind == "play":
                    return ("play", arg)
                if kind == "cheat":
                    return ("cheat", None)
                if kind == "quit":
                    return None
                screen, sel = kind, 0
            elif screen == "worlds":
                if world_unlocked(data, WORLDS, items[sel].num):
                    world_sel, screen, sel = sel, "missions", 0
                else:
                    msg = "Locked: finish the earlier worlds first (or Settings → Unlock all)."
            elif screen == "missions":
                return ("play", ("campaign", items[sel].id))
            elif screen == "settings":
                what = items[sel][0]
                if what == "bell":
                    data["settings"]["bell"] = not data["settings"].get("bell", True)
                    progress.save(data)
                elif what == "unlock":
                    data["settings"]["unlock_all"] = not data["settings"].get("unlock_all")
                    progress.save(data)
                elif what == "reset":
                    put(h - 2, 3, "Really erase all progress? Press y to confirm.", ORANGE | curses.A_BOLD)
                    scr.refresh()
                    if scr.getch() == ord("y"):
                        progress.save(progress.default())
                        msg = "Progress reset."
                else:
                    screen, sel = "main", 0
