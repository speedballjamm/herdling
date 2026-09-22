"""The campaign: every world, in order."""
import importlib

_NAMES = ["w0", "w1", "w2", "w3", "w4", "w5", "w6", "w7", "w8", "w9", "w10"]

WORLDS = []
for _n in _NAMES:
    try:
        WORLDS.append(importlib.import_module(f".{_n}", __name__).WORLD)
    except ModuleNotFoundError as e:
        if e.name != f"{__name__}.{_n}":
            raise

ORDER = [m for w in WORLDS for m in w.missions]


def mission_index(mid):
    for i, m in enumerate(ORDER):
        if m.id == mid:
            return i
    return 0


def find(mid):
    for m in ORDER:
        if m.id == mid:
            return m
    return None
