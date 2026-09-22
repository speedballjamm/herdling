"""The game engine: watches Herdr and runs the lessons.

It runs as a background thread in the launcher process, next to the proxy that
draws the HUD. Each tick it takes a snapshot of the whole Herdr session over the
socket API, diffs it against the last one, adds the keys the player pressed
(from the proxy), and checks the current step's goal.
"""
import json
import logging
import os
import queue
import threading
import time

from . import actions, conf, markup, paths, progress, state
from .card import CardView
from .keyin import KeyTracker
from .keys import BY_ID as KEYS, describe
from .model import Ctx

TICK = 0.1
NUDGE_AFTER = 20
HINT_AFTER = 45
IGNORE_KEYS = {"cancel", "help", "send_prefix"}
IDLE_TIP = "stuck? type  herdling hint  in a pane   (also: herdling task · show · skip · reset)"

log = logging.getLogger("herdling")

# how the engine types keys into Herdr for `herdling show` (legacy terminal bytes)
KEY_BYTES = {"enter": b"\r", "esc": b"\x1b", "tab": b"\t", "shift+tab": b"\x1b[Z", "minus": b"-",
             "space": b" ", "up": b"\x1b[A", "down": b"\x1b[B", "right": b"\x1b[C", "left": b"\x1b[D",
             "backspace": b"\x7f", "pageup": b"\x1b[5~", "pagedown": b"\x1b[6~"}


def key_bytes(key, prefix="ctrl+b"):
    if key == "prefix":
        key = prefix
    if key.startswith("ctrl+") and len(key) == 6:
        return bytes([ord(key[-1]) & 0x1f])
    if key.startswith("shift+") and len(key) == 7:
        return key[-1].upper().encode()
    if key.startswith("alt+"):
        return b"\x1b" + key_bytes(key[4:], prefix)
    if key in KEY_BYTES:
        return KEY_BYTES[key]
    return key.encode()


class Quit(Exception):
    """The Herdr server went away, or the player asked for the menu."""


class Skip(Exception):
    pass


class Reset(Exception):
    pass


class StepResult:
    def __init__(self, hinted=False, shown=False):
        self.hinted = hinted
        self.shown = shown


class Engine:
    def __init__(self, herdr, hud, mode="campaign", start=None, once=False):
        self.h = herdr
        self.hud = hud
        self.mode = mode
        self.start = start
        self.once = once
        self.data = progress.load()
        self.snap = None
        self.proxy = None            # set by the launcher while a Herdr client is attached
        self.session = None          # which session that client is attached to
        self.raw_events = queue.Queue()
        self.tracker = KeyTracker()
        self.conf_mtime = None
        self.flash_until = 0
        self.base_msg = ("", "")
        self.timer = None
        self.runtime = {}
        self.hints_shown = []
        self.stop = threading.Event()
        self.finished = threading.Event()
        self.thread = None
        paths.ensure()
        self.load_keymap()
        try:
            self.ev_pos = os.path.getsize(paths.EVENTS)
        except OSError:
            self.ev_pos = 0

    # ------------------------------------------------------------ attach / detach (launcher calls)

    def attached(self, proxy, session=None):
        self.tracker.reset()
        self.session = session
        self.proxy = proxy

    def detached(self):
        self.proxy = None
        self.tracker.reset()
        self.hud.set(mode="terminal")

    def on_input(self, ev):
        """Called on the proxy's thread for every decoded input/output event."""
        self.raw_events.put(ev)

    @property
    def is_attached(self):
        return bool(self.proxy and self.proxy.running)

    def client(self):
        p = self.proxy
        if p and p.running:
            cols, rows = p.child_size
            return {"attached": True, "cols": cols, "rows": rows, "session": self.session or "default"}
        return {"attached": False, "cols": 0, "rows": 0, "session": None}

    # ------------------------------------------------------------ plumbing

    def load_keymap(self):
        try:
            mtime = os.path.getmtime(paths.CONFIG)
        except OSError:
            mtime = None
        if mtime == self.conf_mtime:
            return
        self.conf_mtime = mtime
        try:
            self.tracker.configure(*conf.keymap())
        except Exception:
            log.exception("couldn't read the practice config's keys")

    def refresh(self):
        s = state.take(self.h, self.client())
        if s is None:
            raise Quit()
        self.snap = s
        return s

    def key_actions(self):
        out = []
        while True:
            try:
                ev = self.raw_events.get_nowait()
            except queue.Empty:
                break
            if ev[0] == "copy":
                out.append(actions.Action("copy", {"text": ev[1]}))
                continue
            if ev[0] == "focus":
                continue
            for item in self.tracker.feed(ev):
                kind = item.pop("kind")
                if kind == "hkey":
                    out.append(actions.Action("key", item))
                    if item.get("action") == "reload_config":
                        self.conf_mtime = -1
                elif kind == "mode":
                    self.hud.set(mode=item["mode"])
                    out.append(actions.Action("mode", item))
                else:
                    out.append(actions.Action(kind, item))
        return out

    def tick(self, sleep=True):
        if sleep:
            time.sleep(TICK)
        if self.stop.is_set():
            raise Quit()
        s = state.take(self.h, self.client())
        if s is None:
            raise Quit()
        settling = bool(self.proxy and time.time() < self.proxy.settle_until)
        acts = actions.classify(self.snap, s, geometry=not settling) if self.snap else []
        acts += self.key_actions()
        self.snap = s
        evs = self.read_events()
        if any(e.get("type") == "cmd" and e.get("cmd") == "menu" for e in evs):
            raise Quit()
        now = time.time()
        if self.flash_until and now > self.flash_until:
            self.flash_until = 0
            self.hud.set(msg=self.base_msg[0], kind=self.base_msg[1])
        if self.timer:
            self.hud.set(right=self.right_text())
        if int(now * 10) % 10 == 0:
            self.load_keymap()
        return s, acts, evs

    def read_events(self):
        out = []
        try:
            size = os.path.getsize(paths.EVENTS)
            if size < self.ev_pos:
                self.ev_pos = 0
            if size == self.ev_pos:
                return out
            with open(paths.EVENTS) as f:
                f.seek(self.ev_pos)
                chunk = f.read()
                self.ev_pos = f.tell()
        except OSError:
            return out
        for line in chunk.splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
        return out

    def msg(self, text, kind="", secs=None):
        if secs:
            self.flash_until = time.time() + secs
        else:
            self.base_msg = (text, kind)
            if self.flash_until:
                return
        self.hud.set(msg=text, kind=kind)

    def set_prompt(self, title, prompt, outside=""):
        self.hints_shown = []
        self.hud.set(title=title, prompt=prompt, right=self.right_text())
        self.write_runtime(title=title, prompt=markup.plain(prompt), outside=outside, hints=[])

    def write_runtime(self, **kw):
        self.runtime.update(kw)
        self.runtime.update(mode=self.mode, pid=os.getpid())
        tmp = paths.RUNTIME + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.runtime, f)
        os.replace(tmp, paths.RUNTIME)

    def show_hint(self, text):
        if text not in self.hints_shown:
            self.hints_shown.append(text)
        self.msg(text, "hint")
        self.write_runtime(hints=[markup.plain(h) for h in self.hints_shown])

    def right_text(self):
        from .worlds import WORLDS
        d = self.data
        bits = [progress.rank(d, WORLDS), f"{d['xp']} XP"]
        if d["streak"] > 1:
            bits.append(f"streak x{d['streak']}")
        if self.timer:
            start, par = self.timer
            el = int(time.time() - start)
            clock = f"time {el // 60}:{el % 60:02d}"
            if par:
                clock += f" / par {par // 60}:{par % 60:02d}"
            bits.append(clock)
        return " · ".join(bits)

    def bell(self):
        if self.data["settings"].get("bell", True) and self.is_attached:
            try:
                os.write(1, b"\a")
            except OSError:
                pass

    def press(self, *keys, delay=0.25):
        """Type keys into Herdr, e.g. press("prefix", "v")."""
        p = self.proxy
        if not p or not p.running:
            return False
        for k in keys:
            if k.startswith("text:"):
                p.inject(k[5:].encode())
            else:
                p.inject(key_bytes(k, self.tracker.prefix))
            time.sleep(delay)
        return True

    def wait_attached(self):
        while not self.is_attached:
            self.tick()
        return self.snap

    def show_card(self, card_id=None, text=None):
        from . import cards
        card = text if text is not None else cards.CARDS[card_id]
        while True:
            self.wait_attached()
            old = self.base_msg
            self.msg("Reading a lesson card: press Enter to continue", "info")
            done = self.proxy.show_card(CardView(card))
            self.msg(*old)
            if done and self.is_attached:
                break
            if done and not self.is_attached:
                break   # they detached with the card open; don't nag with it again
        self.key_actions()   # forget keys pressed on the card
        self.refresh()

    def save(self):
        progress.save(self.data)

    # ------------------------------------------------------------ steps & missions

    def run_step(self, mission, idx, step, ctx, title):
        if step.card:
            self.show_card(step.card)
        if step.setup:
            step.setup(ctx)
            time.sleep(0.15)
        s = self.refresh()
        self.key_actions()  # forget keys pressed during setup
        ctx.s, ctx.prev, ctx.base = s, None, s
        ctx.actions, ctx.events = [], []
        ctx._said = None
        self.set_prompt(title, step.prompt, step.outside)
        self.flash_until = 0
        self.msg(IDLE_TIP)
        start = time.time()
        tier, hinted, shown = 0, False, False
        nagged_inside = False
        while True:
            s, acts, evs = self.tick()
            ctx.new_tick(s, acts, evs)
            for e in evs:
                if e.get("type") != "cmd":
                    continue
                cmd = e.get("cmd")
                if cmd == "hint":
                    if tier < len(step.hints):
                        hinted |= tier >= 1 or len(step.hints) == 1
                        self.show_hint(step.hints[tier])
                        tier += 1
                    elif self.hints_shown:
                        self.show_hint(self.hints_shown[-1])
                    else:
                        self.msg("No hint for this one. `herdling show` will do it for you to watch.", "hint", 6)
                elif cmd == "skip":
                    raise Skip()
                elif cmd == "reset":
                    raise Reset()
                elif cmd == "show":
                    shown = True
                    self.demo(step, ctx)
                elif cmd == "card":
                    card = step.card or mission.card
                    if card:
                        self.show_card(card)
                    else:
                        self.msg("No lesson card for this mission.", "info", 4)
            try:
                ok = step.goal(ctx)
            except Exception:
                log.exception("goal crashed for %s step %d", mission.id, idx)
                ok = False
            if ctx.feedback:
                self.msg(ctx.feedback[0], ctx.feedback[1], 7)
                ctx.feedback = None
            if ok:
                self.msg(step.done or "Nice!", "ok", 3)
                time.sleep(0.9)
                return StepResult(hinted, shown)
            if step.detached and s.attached and s.attached_session == "default":
                if not nagged_inside:
                    self.msg("This step happens outside Herdr. Detach first: `prefix+q`.", "bad", 30)
                    nagged_inside = True
            else:
                nagged_inside = False
            if acts:
                self.coach(step, ctx, acts)
            el = time.time() - start
            if step.timeout_hints and step.hints:
                if tier == 0 and el > NUDGE_AFTER:
                    self.show_hint(step.hints[0])
                    tier = 1
                elif tier == 1 and el > HINT_AFTER and len(step.hints) > 1:
                    self.show_hint(step.hints[1])
                    tier, hinted = 2, True

    def coach(self, step, ctx, acts):
        for pred, text in step.mistakes:
            try:
                if pred(ctx):
                    self.msg(text, "bad", 7)
                    return
            except Exception:
                log.exception("mistake predicate crashed")
        for a in acts:
            if a.kind != "key":
                continue
            info = a.info
            if info.get("held_ctrl"):
                self.msg(f"You held Ctrl for the second key too (`{info['key']}`). Press `ctrl+b`, "
                         "**let go**, then the key on its own.", "bad", 7)
                return
            if info.get("action") is None:
                habit = info.get("habit")
                key = info["key"]
                if habit:
                    what, instead = habit
                    tip = f" In Herdr that's `{instead}`." if instead.startswith("prefix") else \
                        (f" In Herdr: {instead}." if instead else "")
                    self.msg(f"`{key}` is tmux's {what}; Herdr doesn't bind it.{tip}", "bad", 7)
                else:
                    self.msg(f"`{key}` isn't bound to anything in Herdr. `prefix+?` lists every key.", "bad", 6)
                return
            act = info["action"]
            if step.expect and act not in step.expect and act not in IGNORE_KEYS:
                self.msg(f"That was `{info['key']}`: {describe(act)}. Not what this step wants; try again!",
                         "bad", 6)
                return

    def demo(self, step, ctx):
        if not step.demo:
            self.show_hint("No demo here. The answer: " + (step.hints[-1] if step.hints else step.prompt))
            return
        if not self.is_attached:
            self.msg("I can only show you while you're inside Herdr.", "info", 4)
            return
        self.msg("Watch the screen…", "info")
        time.sleep(0.8)
        for item in step.demo:
            if callable(item):
                item(ctx)
            else:
                self.msg(f"Pressing  `{item}`", "info")
                keys = []
                for part in item.split():
                    if part.startswith("prefix+"):
                        keys += ["prefix", part[len("prefix+"):]]
                    else:
                        keys.append(part)
                self.press(*keys, delay=0.5)
            time.sleep(0.8)
        self.msg("That's how! Now you try.", "info", 4)
        time.sleep(1.5)
        if step.setup:
            step.setup(ctx)
            time.sleep(0.2)
        s = self.refresh()
        ctx.s = ctx.base = s
        ctx.actions = []
        self.key_actions()

    def play_mission(self, m):
        """Play one mission. Returns stars (0 = skipped)."""
        if m.card:
            self.show_card(m.card)
        mem = {}
        ctx = Ctx(self.h, mem, self)
        t0 = time.time()
        hinted = shown = False
        n = len(m.steps)
        self.timer = (t0, m.par) if m.boss else None
        i = 0
        while i < n:
            title = f"{m.id} {m.title}" + (f" ({i + 1}/{n})" if n > 1 else "")
            try:
                r = self.run_step(m, i, m.steps[i], ctx, title)
            except Skip:
                self.timer = None
                self.msg(f"Skipped {m.id}. Come back to it from the World menu any time.", "info", 4)
                progress.record_mission(self.data, m, 0, 0, 0, True)
                self.save()
                time.sleep(1.2)
                return 0
            except Reset:
                while i > 0 and m.steps[i].setup is None:
                    i -= 1
                if i == 0:
                    mem.clear()
                self.msg("Reset! Starting the step again.", "info", 3)
                continue
            hinted |= r.hinted
            shown |= r.shown
            i += 1
        secs = time.time() - t0
        self.timer = None
        if shown:
            stars, xp = 1, 0
        elif hinted:
            stars, xp = 1, m.xp // 2
        elif secs <= m.par:
            stars, xp = 3, int(m.xp * 1.25)
        else:
            stars, xp = 2, m.xp
        gained = progress.record_mission(self.data, m, stars, xp, round(secs, 1), hinted or shown)
        self.save()
        self.bell()
        extra = "" if stars == 3 else ("  (hints halve XP)" if hinted and not shown else
                                        "  (beat par for ★★★)" if stars == 2 else "")
        self.hud.set(right=self.right_text())
        self.msg(f"Mission complete! {progress.stars_str(stars)}  +{gained} XP  in {secs:.0f}s{extra}", "ok", 4)
        time.sleep(2.2)
        return stars

    # ------------------------------------------------------------ modes

    def campaign(self):
        from .worlds import WORLDS, ORDER, mission_index
        from . import cards
        idx = mission_index(self.start) if self.start else self.first_incomplete(ORDER)
        if idx == 0 and not self.data["missions"]:
            self.show_card("welcome")
        while idx < len(ORDER):
            m = ORDER[idx]
            world = WORLDS[m.world]
            if world.missions[0] is m and world.card:
                self.show_card(world.card)
            before = progress.worlds_done(self.data, WORLDS)
            self.play_mission(m)
            after = progress.worlds_done(self.data, WORLDS)
            if after > before:
                self.show_card(text=cards.world_complete(world, self.data, WORLDS))
            if self.once:
                return
            idx += 1
        if all(progress.completed(self.data, m.id) for m in ORDER if not m.bonus):
            self.show_card("graduation")
        self.sandbox(finished=True)

    def first_incomplete(self, order):
        for i, m in enumerate(order):
            if not progress.completed(self.data, m.id) and not m.bonus:
                return i
        return 0

    def sandbox(self, finished=False):
        from . import setups
        self.mode = "sandbox"
        self.timer = None
        prompt = ("You've finished the campaign! Free play: try anything and I'll name every key."
                  if finished else "Free play: try anything and I'll name every key you press.")
        self.set_prompt("SANDBOX", prompt)
        self.msg("Tip: `prefix+?` lists every key. `herdling cheat` prints your cheat sheet.", "info")
        if not finished:
            self.wait_attached()
            setups.reset(Ctx(self.h, {}, self))
        while True:
            s, acts, evs = self.tick()
            pressed = [a for a in acts if a.kind == "key"]
            if pressed:
                a = pressed[-1]
                act = a.info.get("action")
                if act:
                    self.msg(f"`{a.info['key']}`  {describe(act)}", "info", 8)
                elif a.info.get("habit"):
                    self.msg(f"`{a.info['key']}` is tmux's {a.info['habit'][0]}; not bound in Herdr.", "bad", 8)
                else:
                    self.msg(f"`{a.info['key']}` isn't bound in Herdr.", "bad", 6)
            for a in acts:
                if a.kind == "mouse" and a.info.get("event") == "press" and not pressed:
                    self.msg(f"click ({a.info['button']}) at {a.info['x']},{a.info['y']}", "info", 3)
                if a.kind in actions.NARRATION and a.kind != "agent":
                    kid, text = actions.NARRATION[a.kind]
                    if pressed:
                        self.hud.set(prompt=text)
                    else:
                        key = KEYS[kid].keys if kid in KEYS else ""
                        self.msg(f"`{key}`  {text}" if key else text, "info", 8)
                if a.kind == "copy":
                    self.msg(f"Copied to your clipboard: {a.info['text'][:50]!r}", "ok", 6)

    def drills(self, review=False):
        from . import drills
        from .worlds import WORLDS
        drills.run(self, review=review, worlds=WORLDS)

    def main(self):
        log.info("engine start mode=%s start=%s", self.mode, self.start)
        self.hud.set(title="herdling", prompt="Loading…", right=self.right_text())
        try:
            self.snap = self.refresh()
            if self.mode == "campaign":
                self.campaign()
            elif self.mode == "sandbox":
                self.sandbox()
            elif self.mode == "dojo":
                self.drills()
            elif self.mode == "review":
                self.drills(review=True)
        except Quit:
            log.info("server gone or quitting; engine exiting")
        except Exception:
            log.exception("engine crashed")
            try:
                self.hud.set(title="herdling", prompt="The game engine crashed, sorry! Details: ~/.herdling/engine.log",
                             msg="Detach with `prefix+q` and run ./herdling again to resume.", kind="bad")
            except Exception:
                pass
        finally:
            self.save()
            self.finished.set()
            if self.proxy:
                self.proxy.quit()

    def start_thread(self):
        self.thread = threading.Thread(target=self.main, name="engine", daemon=True)
        self.thread.start()
