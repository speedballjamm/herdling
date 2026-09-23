"""Your own shell, while you're detached from the game's Herdr.

When you detach, the launcher starts your real shell (your rc files, prompt, aliases and all)
with a `herdr` wrapper first on PATH (bin/outside/herdr, which runs `main` below). The
wrapper sends herdr commands to the game's sandboxed Herdr instead of yours. To attach
(`herdr`, `herdr session attach NAME`, `herdr --session NAME`) it asks the launcher to do it,
then waits in the foreground like a real Herdr client does. The launcher takes the
terminal, runs the Herdr client under the HUD, and gives the terminal back when you
detach, so the `herdr` command returns and your shell carries on where it left off.
"""
import json
import os
import signal
import subprocess
import sys
import time

from . import cli, herdr, paths

REQUEST = os.path.join(paths.RUN_DIR, "attach-request.json")
DONE = os.path.join(paths.RUN_DIR, "attach-done")
READY = os.path.join(paths.RUN_DIR, "outside-ready")   # the shell is at a prompt (tests wait on it)
SHELL_DIR = os.path.join(paths.ROOT, "game", "shell")
OUTSIDE_BIN = os.path.join(paths.BIN, "outside")

B = "\x1b[1m"
Y = "\x1b[38;5;214m"
C = "\x1b[38;5;117m"
G = "\x1b[38;5;78m"
DIM = "\x1b[38;5;244m"
R = "\x1b[0m"

# `herdr` subcommands that run for real (inside the sandbox) while you're playing
REAL = {"session", "status", "workspace", "tab", "pane", "agent", "api", "notification", "--version", "-V",
        "--help", "-h", "help", "--default-config"}


def session_arg(argv):
    """The session a `herdr …` command would attach to, or None if it isn't an attach."""
    if argv == ["herdr"]:
        return "default"
    if len(argv) == 3 and argv[1] == "--session":
        return argv[2]
    if len(argv) == 4 and argv[1:3] == ["session", "attach"]:
        return argv[3]
    return None


def touch(path, text=""):
    try:
        with open(path, "w") as f:
            f.write(text)
    except OSError:
        pass


def remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


# ------------------------------------------------------------------ what you see

def await_engine(timeout=1.5):
    """Give the engine a moment to react to what just happened (it writes runtime.json)."""
    try:
        seen = os.stat(paths.RUNTIME).st_mtime
    except OSError:
        return
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(0.1)
        try:
            if os.stat(paths.RUNTIME).st_mtime != seen:
                time.sleep(0.1)
                return
        except OSError:
            return


def print_task(rt, tick=False):
    print(f"{G + '✔ ' + R if tick else ''}{Y}▶ {rt.get('title', '')}{R}  {rt.get('prompt', '')}")
    if rt.get("outside"):
        print(f"  {B}{rt['outside']}{R}")


def banner():
    rt = cli.runtime()
    running = herdr.running_sessions()
    print("\x1b[H\x1b[2J\x1b[3J", end="")
    print(f"{C}──────────────────────── outside Herdr ────────────────────────{R}")
    print(f"You've {B}detached{R}. Herdr's server is still running in the background, with every")
    print(f"pane and program still going. Running sessions: {B}{', '.join(running) or 'none'}{R}")
    print(f"{DIM}This is your own shell. While the game runs, herdr here means the game's Herdr.{R}")
    print()
    if rt.get("prompt"):
        print_task(rt)
    else:
        print(f"  To go back in:  {B}herdr{R}")
    print(f"{DIM}  (exit this shell to quit to the title menu){R}")
    print()


# ------------------------------------------------------------------ the shell (launcher side)

def shell_env():
    env = dict(os.environ)
    for k in ("HERDR_ENV", "HERDR_SOCKET_PATH", "HERDR_SESSION", "HERDR_PANE_ID", "HERDR_TAB_ID",
              "HERDR_WORKSPACE_ID"):
        env.pop(k, None)
    env.update(HERDLING_GAME="1", HERDLING_HOME=paths.HOME, HERDLING_PYTHON=sys.executable,
               HERDLING_PATH_PREFIX=os.pathsep.join([OUTSIDE_BIN, paths.BIN]), HERDLING_READY=READY,
               HERDLING_SHELL_DIR=SHELL_DIR,
               SHELL_SESSIONS_DISABLE="1")   # macOS Terminal's session restore: not for a shell inside the game
    # the rc wrappers put this back on PATH last; set it now too in case they don't run
    env["PATH"] = env["HERDLING_PATH_PREFIX"] + os.pathsep + env.get("PATH", "")
    return env


def shell_argv(env):
    """Start your shell so that its own startup files run first, then ours (finish.sh)."""
    shell = herdr.user_shell()
    name = os.path.basename(shell)
    login = sys.platform == "darwin"     # like Herdr's shell_mode "auto": login shells on macOS
    if name == "zsh":
        env["HERDLING_ZDOTDIR"] = env.get("ZDOTDIR") or os.path.expanduser("~")
        env["ZDOTDIR"] = os.path.join(SHELL_DIR, "zsh")
        return [shell] + (["-l"] if login else []) + ["-i"]
    if name == "bash":
        return [shell, "--rcfile", os.path.join(SHELL_DIR, "bashrc"), "-i"]
    if name == "fish":
        return [shell] + (["-l"] if login else []) + [
            "-i", "-C", "set -gx PATH (string split : $HERDLING_PATH_PREFIX) $PATH; touch $HERDLING_READY"]
    # sh, dash, ksh… read $ENV when interactive
    env["HERDLING_ORIG_ENV"] = env.get("ENV", "")
    env["ENV"] = os.path.join(SHELL_DIR, "finish.sh")
    return [shell, "-i"]


class Shell:
    """Your shell, running on the real terminal. The launcher only borrows the terminal to attach."""

    def __init__(self, cwd=None):
        remove(REQUEST)
        remove(DONE)
        env = shell_env()
        self.proc = subprocess.Popen(shell_argv(env), env=env, cwd=cwd)

    def alive(self):
        return self.proc.poll() is None

    def request(self):
        """An attach the `herdr` wrapper asked for: {"session", "pgrp", "argv"} or None."""
        try:
            with open(REQUEST) as f:
                req = json.load(f)
        except (OSError, ValueError):
            return None
        remove(REQUEST)
        return req

    def done(self, pgrp):
        """Hand the terminal back to the waiting `herdr` command and let it return."""
        if not give_terminal(pgrp):
            give_terminal(self.pgrp())
        touch(DONE)

    def pgrp(self):
        try:
            return os.getpgid(self.proc.pid)
        except OSError:
            return None

    def end(self):
        """Close the shell (quitting to the menu) and take the terminal back."""
        if self.alive():
            for sig in (signal.SIGHUP, signal.SIGKILL):
                try:
                    os.kill(self.proc.pid, sig)
                    self.proc.wait(timeout=2)
                    break
                except (OSError, subprocess.TimeoutExpired):
                    pass
        take_terminal()
        remove(REQUEST)
        remove(DONE)


def give_terminal(pgrp):
    """Make `pgrp` the terminal's foreground process group. From the background, this needs
    SIGTTOU ignored for the moment (the way shells do it)."""
    if not pgrp:
        return False
    old = signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    try:
        os.tcsetpgrp(sys.stdin.fileno(), pgrp)
        return True
    except OSError:
        return False
    finally:
        signal.signal(signal.SIGTTOU, old)


def take_terminal():
    return give_terminal(os.getpgrp())


# ------------------------------------------------------------------ the `herdr` wrapper

def attach_from_shell(argv, session):
    """Ask the launcher to attach, and wait (in the foreground) until you detach again."""
    remove(DONE)
    touch(REQUEST, json.dumps({"session": session, "pgrp": os.getpgrp(), "argv": argv}))
    while not os.path.exists(DONE):
        time.sleep(0.1)
    remove(DONE)


def run(argv):
    """`herdr ARGS…` typed in the shell while detached. Returns the exit status."""
    if os.environ.get("HERDLING_GAME") != "1":
        # not from the game's shell after all: be the real herdr
        os.execvp(herdr.herdr_bin(), [herdr.herdr_bin()] + argv[1:])
    before = cli.runtime().get("prompt")
    status = 0
    target = session_arg(argv)
    sub = argv[1] if len(argv) > 1 else ""
    if target is not None:
        cli.send({"type": "outside", "argv": argv})
        attach_from_shell(argv, target)
    elif sub == "server" or (argv[1:3] == ["session", "stop"] and (argv[3:4] or ["default"])[0] == "default"):
        if argv[1:3] not in (["server", "stop"], ["session", "stop"]):
            print(f"{DIM}(herdling) Only `herdr server stop` is allowed while you're playing.{R}")
            return 1
        ans = input(f"{Y}That stops the game's own Herdr server, closing every pane (and quitting the "
                    f"game). Sure? [y/N]{R} ").strip().lower()
        if ans != "y":
            return 1
        cli.send({"type": "outside", "argv": argv})
        return subprocess.call([herdr.herdr_bin()] + argv[1:], env=herdr.game_env())
    elif sub not in REAL:
        print(f"{DIM}(herdling) `herdr {sub}` isn't available while you're playing. Try herdr session list, "
              f"herdr session attach NAME, herdr status.{R}")
        return 1
    else:
        cli.send({"type": "outside", "argv": argv})
        status = subprocess.call([herdr.herdr_bin()] + argv[1:], env=herdr.game_env())
    await_engine()
    rt = cli.runtime()
    if rt.get("prompt") and rt.get("prompt") != before:
        print()
        print_task(rt, tick=True)
    return status


def main(args):
    try:
        status = run(["herdr"] + args)
    except KeyboardInterrupt:
        print()
        status = 130
    touch(READY)
    sys.exit(status)


if __name__ == "__main__":
    main(sys.argv[1:])
