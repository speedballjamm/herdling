"""Little programs the game runs inside your panes.

    label NAME [COLOUR]              a big name tag
    log SEED SECRET [BEFORE] [AFTER] a long log with a secret line buried in it
    search SEED WORD N               a log with N lines containing WORD
    incident SEED FIRST DECOYS [DELAY] [LEVEL]  a log stream; find the first ERROR (or WARN…)
    ticker SECS CODE                 counts up, then prints a code word
    banner TEXT                      one line of text
    agent NAME SCRIPT                a pretend coding agent (see `agent` below)
"""
import json
import os
import random
import select
import socket
import sys
import time

SERVICES = ["api", "auth", "db", "cache", "billing", "search", "queue", "cdn"]
MSGS = [
    "GET /v1/users/{n} 200 {ms}ms", "POST /v1/orders 201 {ms}ms", "cache hit ratio {pct}%",
    "worker {n} heartbeat ok", "rotated log segment {n}", "GET /healthz 200 1ms",
    "connection pool size={n}", "flushed {n} metrics", "scheduled job #{n} complete",
    "GET /v1/search?q=herdr 200 {ms}ms", "user {n} logged in", "TLS session resumed",
]
LEVELS = ["INFO"] * 6 + ["DEBUG"] * 3 + ["WARN"]
COLOURS = [117, 150, 217, 222, 183, 116, 210, 186]


def fake_line(rng, i):
    msg = rng.choice(MSGS).format(n=rng.randint(1, 9999), ms=rng.randint(2, 400), pct=rng.randint(60, 99))
    h, m, s = 9 + i // 3600 % 12, (i // 60) % 60, i % 60
    return f"{h:02d}:{m:02d}:{s:02d} {rng.choice(LEVELS):<5} [{rng.choice(SERVICES):<7}] {msg}"


def label(name, colour=None):
    bg = int(colour) if colour else COLOURS[sum(map(ord, name)) % len(COLOURS)]
    pad = " " * (len(name) + 6)
    print("\x1b[2J\x1b[H")
    print()
    print(f"   \x1b[1;30;48;5;{bg}m{pad}\x1b[0m")
    print(f"   \x1b[1;30;48;5;{bg}m   {name}   \x1b[0m")
    print(f"   \x1b[1;30;48;5;{bg}m{pad}\x1b[0m")
    print()


def log(seed, secret, before=220, after=60):
    rng = random.Random(seed)
    before, after = int(before), int(after)
    for i in range(before):
        print(fake_line(rng, i))
    print(f"\x1b[1m{secret}\x1b[0m")
    for i in range(after):
        print(fake_line(rng, before + i + 1))
    sys.stdout.flush()


def search(seed, word, n):
    """`n` lines containing `word`, spread through a long log; the oldest says it's the oldest."""
    rng = random.Random(seed)
    n = int(n)
    marks = sorted(rng.sample(range(20, 260), n))
    k = n
    for i in range(300):
        if i in marks:
            tag = " (the OLDEST one)" if k == n else ""
            print(f"{fake_line(rng, i)}  {word} hint #{n - k + 1}{tag}")
            k -= 1
        else:
            print(fake_line(rng, i))
    sys.stdout.flush()


INCIDENT_LINES = {    # level -> (first line, later ones): the id comes straight after the level,
    "ERROR": ("[billing] charge failed: upstream timeout", "[billing] retry failed"),  # so `W` reaches it
    "WARN": ("[disk] /var is 91% full", "[disk] /var is still filling up"),
}


def incident(seed, first_id, decoys, delay=0.02, level="ERROR"):
    rng = random.Random(seed)
    first_msg, later_msg = INCIDENT_LINES[level]
    decoys = [d for d in decoys.split(",") if d]
    delay = float(delay)
    first_at = rng.randint(50, 80)
    later = sorted(rng.sample(range(first_at + 30, 240), len(decoys)))
    print("=== incident stream: payments-api (prod) ===")
    for i in range(260):
        if i == first_at:
            line = f"{i:05d} {level:<5} {first_id} {first_msg}"
        elif i in later:
            line = f"{i:05d} {level:<5} {decoys[later.index(i)]} {later_msg}"
        else:
            line = f"{i:05d} " + fake_line(rng, i)[9:].replace(f"{level:<5} [", "INFO  [")   # only ours match
        print(line, flush=True)
        if delay:
            time.sleep(delay)
    print(f"=== stream ended: find the FIRST {level} ===", flush=True)


def ticker(secs, code):
    secs = int(secs)
    for i in range(secs + 1):
        print(f"\r  working… {i:3d}s / {secs}s", end="", flush=True)
        time.sleep(1)
    print(f"\n\n  Job finished. The code word is: \x1b[1m{code}\x1b[0m\n", flush=True)


def banner(text):
    print()
    print(f"   {text}")
    print()


# ------------------------------------------------------------------ the pretend agent

def report(state, agent, message=None):
    """Tell Herdr what state this agent is in, like a real agent integration does."""
    sock = os.environ.get("HERDR_SOCKET_PATH")
    pane = os.environ.get("HERDR_PANE_ID")
    if not sock or not pane:
        return
    method = "pane.release_agent" if state == "release" else "pane.report_agent"
    params = {"pane_id": pane, "source": "custom:herdling", "agent": agent}
    if state != "release":
        params["state"] = state
        if message:
            params["message"] = message
    try:
        s = socket.socket(socket.AF_UNIX)
        s.settimeout(2)
        s.connect(sock)
        s.sendall((json.dumps({"id": "agent", "method": method, "params": params}) + "\n").encode())
        s.recv(65536)
        s.close()
    except OSError:
        pass


THOUGHTS = ["Reading src/app.py", "Thinking about the failing test", "Editing handlers/users.py",
            "Running the test suite", "Grepping for TODOs", "Refactoring the config loader",
            "Writing a migration", "Checking the lint output", "Updating the README"]
SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def work(name, secs, rng):
    report("working", name)
    end = time.time() + secs
    thought = rng.choice(THOUGHTS)
    i = 0
    while time.time() < end:
        print(f"\r  \x1b[38;5;214m{SPIN[i % len(SPIN)]}\x1b[0m {thought}…   ", end="", flush=True)
        time.sleep(0.12)
        i += 1
        if i % 20 == 0:
            print(f"\r  \x1b[38;5;78m✔\x1b[0m {thought}      ")
            thought = rng.choice(THOUGHTS)
    print(f"\r  \x1b[38;5;78m✔\x1b[0m {thought}      ", flush=True)


NAG_EVERY = 8   # seconds between taps on the shoulder while a question waits


def wait_for_answer(name, question):
    """Read a line, tapping the shoulder again every few seconds. Herdr's notice only shows for
    a moment and `prefix+o` only works while it's up, so a slow player would otherwise be stuck.
    Blocked -> unknown -> blocked re-fires the notice without ever looking answered."""
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], NAG_EVERY)
        if ready:
            return sys.stdin.readline()
        report("unknown", name)
        time.sleep(0.3)
        report("blocked", name, question)


def agent(name, script=""):
    """A pretend coding agent. SCRIPT is comma-separated steps:
         idle:N    sit at the prompt for N seconds
         work:N    'work' for N seconds (state: working)
         ask:TEXT  ask a yes/no question and wait (state: blocked)
         done      finish (state: idle; Herdr shows it as done until you look)
    Afterwards it waits at a prompt: type anything to give it more 'work'."""
    rng = random.Random(name)
    print(f"\x1b[1;38;5;214m ✻ {name}\x1b[0m  \x1b[38;5;244m(a pretend coding agent: herdling's practice sheep)\x1b[0m")
    print()
    report("idle", name)
    try:
        for step in [s for s in script.split(",") if s]:
            kind, _, arg = step.partition(":")
            if kind == "idle":
                report("idle", name)
                time.sleep(float(arg or 1))
            elif kind == "work":
                work(name, float(arg or 3), rng)
            elif kind == "ask":
                question = arg.replace("_", " ") or "Run the migration?"
                report("blocked", name, question)
                print(f"\n  \x1b[1;38;5;222m? {question}\x1b[0m  [y/n] ", end="", flush=True)
                while True:
                    ans = wait_for_answer(name, question)
                    if not ans:
                        raise EOFError
                    ans = ans.strip().lower()
                    if ans in ("y", "yes", "n", "no"):
                        break
                    print("  Please answer y or n: ", end="", flush=True)
                print("  Thanks!" if ans.startswith("y") else "  OK, I'll skip that.")
                report("working", name)
            elif kind == "done":
                print("\n  \x1b[38;5;78m✔ All done.\x1b[0m", flush=True)
                report("idle", name)
        report("idle", name)
        while True:
            print("\n\x1b[38;5;244m  > \x1b[0m", end="", flush=True)
            line = sys.stdin.readline()
            if not line:
                break
            if line.strip():
                work(name, 2, rng)
                print("  \x1b[38;5;78m✔ Done.\x1b[0m (I'm only pretend, but thanks for the chat.)")
                report("idle", name)
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        report("release", name)


def main(argv):
    if not argv:
        print(__doc__)
        return
    cmd, args = argv[0], argv[1:]
    {"label": label, "log": log, "search": search, "incident": incident, "ticker": ticker,
     "banner": banner, "agent": agent}[cmd](*args)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        pass
