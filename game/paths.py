"""Where things live. Overridable with env vars so tests can run in isolation.

The game runs Herdr in a sandbox: XDG_CONFIG_HOME points at ~/.herdling/x, so the
game's Herdr server, sockets, sessions and logs never mix with your own.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser(os.environ.get("HERDLING_HOME", "~/.herdling"))

# Herdr's config home inside the sandbox. Kept short: socket paths have a ~104 byte limit.
XDG = os.path.join(HOME, "x")
HERDR_DIR = os.path.join(XDG, "herdr")
SOCKET = os.path.join(HERDR_DIR, "herdr.sock")

BIN = os.path.join(ROOT, "game", "bin")
BASE_CONF = os.path.join(ROOT, "game", "game.toml")
CONFIG = os.path.join(HOME, "config.toml")      # the practice config.toml the game's Herdr reads
CONFIG_TILDE = "~/.herdling/config.toml" if "HERDLING_HOME" not in os.environ else CONFIG
PROGRESS = os.path.join(HOME, "progress.json")
RUN_DIR = os.path.join(HOME, "run")
EVENTS = os.path.join(RUN_DIR, "events.jsonl")
RUNTIME = os.path.join(RUN_DIR, "runtime.json")
LOG = os.path.join(HOME, "engine.log")
REAL_CONF = os.path.expanduser(os.environ.get("HERDLING_REAL_CONF", "~/.config/herdr/config.toml"))


def session_socket(name):
    if not name or name == "default":
        return SOCKET
    return os.path.join(HERDR_DIR, "sessions", name, "herdr.sock")


def ensure():
    os.makedirs(RUN_DIR, exist_ok=True)
    os.makedirs(XDG, exist_ok=True)
