"""`herdling install`: offer to make the practice config your real Herdr config (with a backup)."""
import os
import shutil
import time

from . import paths

B = "\x1b[1m"
DIM = "\x1b[38;5;244m"
GREEN = "\x1b[38;5;78m"
R = "\x1b[0m"

HEADER = ("# My Herdr config: a practice copy, made in herdling.\n"
          "# (Inside the game, Herdr reads this file because HERDR_CONFIG_PATH points here.)\n")
REAL_HEADER = "# My Herdr config (started in herdling).\n"


def rewrite(text):
    return text.replace(HEADER, REAL_HEADER)


def main():
    """Returns True if installed, False if declined, None if there was nothing to install."""
    try:
        with open(paths.CONFIG) as f:
            text = rewrite(f.read())
    except OSError:
        print("No practice config found. Nothing to install.")
        return None
    real = paths.REAL_CONF
    shown = real.replace(os.path.expanduser("~"), "~")
    print(f"{B}Your Herdr config{R}\n")
    for line in text.rstrip().splitlines():
        print(f"  {DIM if line.strip().startswith('#') else ''}{line}{R}")
    print()
    exists = os.path.exists(real)
    if exists:
        print(f"You already have {B}{shown}{R}. It will be backed up first.")
    try:
        ans = input(f"Install this as {B}{shown}{R}? [y/N] ").strip().lower()
    except EOFError:
        ans = ""
    if ans not in ("y", "yes"):
        print(f"\nNo problem. It stays at {paths.CONFIG_TILDE}")
        return False
    os.makedirs(os.path.dirname(real), exist_ok=True)
    if exists:
        backup = real + time.strftime(".bak-%Y%m%d-%H%M%S")
        shutil.copy2(real, backup)
        print(f"Backed up the old one to {backup}")
    with open(real, "w") as f:
        f.write(text)
    print(f"\n{GREEN}Installed!{R} Your own Herdr picks it up next start, or right away with:")
    print("  herdr server reload-config      (or prefix+shift+r inside Herdr)")
    return True
