"""Save file: XP, stars, streaks and spaced-repetition boxes."""
import json
import os
import time

from . import paths

RANKS = ["Lost Lamb", "Herdling", "Pane Wrangler", "Layout Rancher", "Tab Tamer", "Space Shepherd",
         "Agent Whisperer", "Session Keeper", "Scrollback Sleuth", "Script Drover", "Config Smith",
         "Herd Master"]

# Leitner box -> days until the key is due again
INTERVALS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 21}
DAY = 86400


def default():
    return {"xp": 0, "missions": {}, "streak": 0, "best_streak": 0, "keys": {},
            "dojo_best": 0, "settings": {"bell": True}}


def load():
    try:
        with open(paths.PROGRESS) as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    base = default()
    base.update(data)
    return base


def save(data):
    paths.ensure()
    tmp = paths.PROGRESS + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    os.replace(tmp, paths.PROGRESS)


def completed(data, mid):
    return data["missions"].get(mid, {}).get("stars", 0) > 0


def record_mission(data, mission, stars, xp, secs, hinted):
    """Store a result. Replays only earn XP for improving. Returns XP gained."""
    prev = data["missions"].get(mission.id, {})
    gained = max(0, xp - prev.get("xp", 0))
    entry = {
        "stars": max(stars, prev.get("stars", 0)),
        "xp": max(xp, prev.get("xp", 0)),
        "best": min(secs, prev.get("best", secs)) if stars else prev.get("best"),
        "skipped": stars == 0 and not prev.get("stars"),
    }
    data["missions"][mission.id] = entry
    data["xp"] += gained
    if stars >= 2:
        data["streak"] += 1
        data["best_streak"] = max(data["best_streak"], data["streak"])
    else:
        data["streak"] = 0
    if stars:
        for k in mission.keys:
            learn_key(data, k, ok=not hinted, fresh=True)
    return gained


def learn_key(data, kid, ok, fresh=False):
    """fresh=True: learned in a mission. fresh=False: answered in review."""
    entry = data["keys"].get(kid)
    if not ok:
        box = 1
    elif entry is None:
        box = 2
    elif fresh:
        box = max(entry["box"], 2)
    else:
        box = min(5, entry["box"] + 1)
    data["keys"][kid] = {"box": box, "due": time.time() + INTERVALS[box] * DAY}


def due_keys(data, now=None):
    now = now or time.time()
    return sorted([k for k, v in data["keys"].items() if v["due"] <= now],
                  key=lambda k: (data["keys"][k]["box"], data["keys"][k]["due"]))


def worlds_done(data, worlds):
    n = 0
    for w in worlds:
        if all(completed(data, m.id) for m in w.core):
            n += 1
        else:
            break
    return n


def rank(data, worlds):
    return RANKS[min(worlds_done(data, worlds), len(RANKS) - 1)]


def stars_str(n, total=3):
    return "★" * n + "☆" * (total - n)
