"""Missions, steps, and the context their goal functions see."""
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple


@dataclass
class Step:
    prompt: str
    goal: Callable
    hints: Sequence[str] = ()          # hints[0] is a free nudge; the rest cost XP
    setup: Optional[Callable] = None
    mistakes: Sequence[Tuple[Callable, str]] = ()
    expect: Sequence[str] = ()          # action kinds that count as "on track"
    card: Optional[str] = None
    keys: Sequence[str] = ()            # key ids practised (for review)
    done: str = ""
    demo: Sequence = ()                 # what `herdling show` does: key strings or callables
    outside: str = ""                   # extra help shown at the outside-Herdr prompt
    detached: bool = False              # the step is done at the outside prompt (nag if still inside)
    timeout_hints: bool = True


@dataclass
class Mission:
    id: str
    title: str
    steps: List[Step]
    xp: int = 50
    par: int = 30
    bonus: bool = False
    boss: bool = False
    card: Optional[str] = None
    blurb: str = ""
    world: int = 0

    @property
    def keys(self):
        out = []
        for s in self.steps:
            for k in s.keys:
                if k not in out:
                    out.append(k)
        return out


@dataclass
class World:
    num: int
    title: str
    missions: List[Mission]
    card: Optional[str] = None
    blurb: str = ""

    def __post_init__(self):
        for m in self.missions:
            m.world = self.num

    @property
    def core(self):
        return [m for m in self.missions if not m.bonus]


class Ctx:
    """What a goal function can look at."""

    def __init__(self, herdr, mem, engine=None):
        self.herdr = herdr
        self.engine = engine
        self.mem = mem            # shared across all steps of a mission
        self.s = None             # current snapshot
        self.prev = None
        self.base = None          # snapshot right after the step's setup
        self.actions = []         # actions since the step started
        self.new = []             # actions from the latest tick
        self.events = []          # outside-prompt / herdling-command events since step start
        self._reads = {}
        self.feedback = None      # (text, kind) a goal wants shown
        self._said = None

    def say(self, text, kind="bad"):
        """Goals call this to give feedback (shown once per distinct message)."""
        if text != self._said:
            self._said = text
            self.feedback = (text, kind)

    # --- what happened
    def did(self, *kinds):
        return any(a.kind in kinds for a in self.actions)

    def just(self, *kinds):
        return any(a.kind in kinds for a in self.new)

    def last(self, kind):
        for a in reversed(self.actions):
            if a.kind == kind:
                return a
        return None

    def pressed(self, *herdr_actions):
        """Did the player press a key bound to one of these Herdr actions (e.g. "zoom")?"""
        return any(a.kind == "key" and a.info.get("action") in herdr_actions for a in self.actions)

    def just_pressed(self, *herdr_actions):
        return any(a.kind == "key" and a.info.get("action") in herdr_actions for a in self.new)

    def tracker_mode(self):
        """Herdr's mode as the key watcher sees it: terminal, prefix, copy, resize, navigate, help…"""
        return self.engine.tracker.mode if self.engine else "terminal"

    def mode_keys(self, mode):
        """Keys pressed inside a Herdr mode (copy, resize, navigate…) this step."""
        return [a.info["key"] for a in self.actions if a.kind == "mkey" and a.info.get("mode") == mode]

    def clicked(self):
        return any(a.kind == "mouse" and a.info.get("event") == "press" and a.info.get("button") == "left"
                   for a in self.actions)

    def dragged(self):
        return any(a.kind == "mouse" and a.info.get("event") == "drag" for a in self.actions)

    def copied(self):
        """Text the player copied (Herdr sends copies to the terminal clipboard), newest last."""
        return [a.info["text"] for a in self.actions if a.kind == "copy"]

    def pasted(self):
        return [a.info["text"] for a in self.actions if a.kind == "paste"]

    # --- reading panes
    def read(self, pane_id, lines=200, source="recent_unwrapped"):
        key = (pane_id, lines, source)
        if key not in self._reads:
            r = self.herdr.try_call("pane.read", pane_id=pane_id, source=source, lines=lines)
            self._reads[key] = (r or {}).get("read", {}).get("text", "")
        return self._reads[key]

    # --- outside Herdr and the herdling command
    def ran_outside(self, *argv_prefixes):
        """True if the player ran a command at the outside prompt starting with any of these,
        e.g. ran_outside(("herdr", "session", "list"))."""
        for e in self.events:
            if e.get("type") == "outside":
                argv = e.get("argv", [])
                for pre in argv_prefixes:
                    if tuple(argv[:len(pre)]) == tuple(pre):
                        return True
        return False

    def answer(self):
        for e in reversed(self.events):
            if e.get("type") == "answer":
                return e.get("text", "")
        return None

    def new_tick(self, snap, actions, events):
        self.prev, self.s = self.s, snap
        self.new = actions
        self.actions.extend(actions)
        self.events.extend(events)
        self._reads = {}
