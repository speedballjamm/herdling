"""Fast tests: no Herdr needed.

    python3 -m unittest tests/test_units.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import actions, conf, hud, markup, state  # noqa: E402
from game.card import CardView  # noqa: E402
from game.cards import CARDS  # noqa: E402
from game.engine import key_bytes  # noqa: E402
from game.keyin import Decoder, KeyTracker, normalise  # noqa: E402
from game.keys import BY_ID  # noqa: E402
from game.worlds import ORDER, WORLDS  # noqa: E402


def keys(data):
    return [e[1] for e in Decoder().feed(data) if e[0] == "key"]


class DecoderTest(unittest.TestCase):
    def test_legacy(self):
        self.assertEqual(keys(b"\x02v-N?\t\r"), ["ctrl+b", "v", "minus", "shift+n", "?", "tab", "enter"])

    def test_kitty(self):
        self.assertEqual(keys(b"\x1b[98;5u"), ["ctrl+b"])
        self.assertEqual(keys(b"\x1b[98;5:3u"), [])          # release
        self.assertEqual(keys(b"\x1b[110;2u"), ["shift+n"])
        self.assertEqual(keys(b"\x1b[47:63;2u"), ["?"])       # shift+/ with alternate key
        self.assertEqual(keys(b"\x1b[27u"), ["esc"])
        self.assertEqual(keys(b"\x1b[9;2u"), ["shift+tab"])
        self.assertEqual(keys(b"\x1b[122;7u"), ["ctrl+alt+z"])
        self.assertEqual(keys(b"\x1b[57441u"), [])            # bare shift press

    def test_special(self):
        self.assertEqual(keys(b"\x1b[A\x1b[1;5C\x1b[Z\x1bOB"), ["up", "ctrl+right", "shift+tab", "down"])
        self.assertEqual(keys(b"\x1bx\x1b\x1a"), ["alt+x", "ctrl+alt+z"])

    def test_replies_are_not_keys(self):
        self.assertEqual(keys(b"\x1b[?62;22c\x1b]11;rgb:0/0/0\x1b\\\x1b[?0u"), [])

    def test_mouse_and_paste(self):
        ev = Decoder().feed(b"\x1b[<0;10;5M\x1b[<32;11;5M\x1b[<0;11;5m\x1b[200~hi there\x1b[201~")
        self.assertEqual([e[1]["kind"] for e in ev[:3]], ["press", "drag", "release"])
        self.assertEqual(ev[3], ("paste", "hi there"))

    def test_split_across_reads(self):
        d = Decoder()
        self.assertEqual(d.feed(b"\x1b[98"), [])
        self.assertEqual(d.feed(b";5u"), [("key", "ctrl+b")])
        self.assertEqual(d.feed(b"\x1b"), [])
        self.assertEqual(d.flush(), [("key", "esc")])


class TrackerTest(unittest.TestCase):
    def feed(self, t, *names):
        out = []
        for n in names:
            out += t.feed(("key", n))
        return out

    def test_prefix_actions(self):
        t = KeyTracker()
        out = self.feed(t, "ctrl+b", "v")
        self.assertIn({"kind": "hkey", "key": "prefix+v", "action": "split_vertical", "mode": "prefix"}, out)
        self.assertEqual(t.mode, "terminal")

    def test_tmux_habit_and_held_ctrl(self):
        t = KeyTracker()
        out = self.feed(t, "ctrl+b", "%")
        self.assertEqual([o for o in out if o["kind"] == "hkey"][0]["habit"][1], "prefix+v")
        out = self.feed(t, "ctrl+b", "ctrl+v")
        self.assertTrue([o for o in out if o["kind"] == "hkey"][0]["held_ctrl"])

    def test_modes(self):
        t = KeyTracker()
        self.feed(t, "ctrl+b", "[")
        self.assertEqual(t.mode, "copy")
        self.feed(t, "v", "e")
        self.assertEqual(t.mode, "copy")
        self.feed(t, "y")
        self.assertEqual(t.mode, "terminal")
        self.feed(t, "ctrl+b", "r", "h", "h")
        self.assertEqual(t.mode, "resize")
        self.feed(t, "esc")
        self.assertEqual(t.mode, "terminal")
        self.feed(t, "ctrl+b", "g", "/", "s", "enter")
        self.assertEqual(t.mode, "terminal")

    def test_custom_keymap(self):
        text = '[keys]\nprefix = "ctrl+a"\nlast_pane = "prefix+semicolon"\nzoom = ["prefix+z", "ctrl+alt+z"]\n'
        prefix, pk, direct = conf.keymap(conf.parse(text))
        self.assertEqual(prefix, "ctrl+a")
        self.assertEqual(pk[";"], "last_pane")
        self.assertEqual(direct["ctrl+alt+z"], "zoom")
        t = KeyTracker(prefix, pk, direct)
        out = self.feed(t, "ctrl+a", ";")
        self.assertEqual([o for o in out if o["kind"] == "hkey"][0]["action"], "last_pane")
        out = self.feed(t, "ctrl+alt+z")
        self.assertEqual(out[0]["action"], "zoom")

    def test_normalise(self):
        self.assertEqual(normalise("minus"), "minus")
        self.assertEqual(normalise("-"), "minus")
        self.assertEqual(normalise("shift+N"), "shift+n")
        self.assertEqual(normalise("ctrl+B"), "ctrl+b")
        self.assertEqual(normalise("semicolon"), ";")


class ConfTest(unittest.TestCase):
    def test_parse(self):
        d = conf.parse('onboarding = false  # c\n[theme]\nname = "tokyo-night"\n[ui]\n'
                       'tab_bar_right = [{ type = "datetime", format = "%H:%M" }, { type = "zoom" }]\n'
                       '[[keys.command]]\nkey = "prefix+alt+g"\ncommand = "lazygit # not a comment"\n')
        self.assertIs(d[""]["onboarding"], False)
        self.assertEqual(conf.get(d, "theme", "name"), "tokyo-night")
        self.assertEqual(conf.get(d, "ui", "tab_bar_right")[0], {"type": "datetime", "format": "%H:%M"})
        self.assertEqual(d["keys.command"][0]["command"], "lazygit # not a comment")

    def test_multiline_array(self):
        d = conf.parse('[ui]\ntab_bar_right = [\n  { type = "zoom" },\n  { type = "hostname" },\n]\n')
        self.assertEqual(len(conf.get(d, "ui", "tab_bar_right")), 2)

    def test_base_config_parses(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "game", "game.toml")) as f:
            d = conf.parse(f.read())
        self.assertEqual(conf.get(d, "ui.toast", "delivery"), "herdr")


RAW = {
    "focused_workspace_id": "w1", "focused_tab_id": "w1:t1", "focused_pane_id": "w1:p1",
    "workspaces": [{"workspace_id": "w1", "label": "home", "number": 1, "focused": True, "active_tab_id": "w1:t1"}],
    "tabs": [{"tab_id": "w1:t1", "workspace_id": "w1", "label": "1", "number": 1, "focused": True}],
    "panes": [{"pane_id": "w1:p1", "workspace_id": "w1", "tab_id": "w1:t1", "focused": True}],
    "layouts": [{"tab_id": "w1:t1", "workspace_id": "w1", "zoomed": False, "focused_pane_id": "w1:p1",
                 "area": {"x": 0, "y": 0, "width": 94, "height": 36},
                 "panes": [{"pane_id": "w1:p1", "rect": {"x": 0, "y": 0, "width": 94, "height": 36}}],
                 "splits": []}],
    "agents": [],
}


def split_raw(direction="right"):
    import copy
    r = copy.deepcopy(RAW)
    r["panes"].append({"pane_id": "w1:p2", "workspace_id": "w1", "tab_id": "w1:t1", "focused": False})
    lay = r["layouts"][0]
    if direction == "right":
        lay["panes"] = [{"pane_id": "w1:p1", "rect": {"x": 0, "y": 0, "width": 47, "height": 36}},
                        {"pane_id": "w1:p2", "rect": {"x": 47, "y": 0, "width": 47, "height": 36}}]
    else:
        lay["panes"] = [{"pane_id": "w1:p1", "rect": {"x": 0, "y": 0, "width": 94, "height": 18}},
                        {"pane_id": "w1:p2", "rect": {"x": 0, "y": 18, "width": 94, "height": 18}}]
    lay["splits"] = [{"id": "s", "direction": direction, "ratio": 0.5,
                      "rect": {"x": 0, "y": 0, "width": 94, "height": 36}}]
    return r


class ActionsTest(unittest.TestCase):
    def test_splits(self):
        a = state.Snapshot(RAW, {"cols": 120})
        for d in ("right", "down"):
            kinds = [x.kind for x in actions.classify(a, state.Snapshot(split_raw(d), {"cols": 120}))]
            self.assertIn(f"split-{d}", kinds)

    def test_focus_direction_and_sidebar(self):
        r1 = split_raw("right")
        r2 = split_raw("right")
        r2["focused_pane_id"] = r2["layouts"][0]["focused_pane_id"] = "w1:p2"
        acts = actions.classify(state.Snapshot(r1, {"cols": 120}), state.Snapshot(r2, {"cols": 120}))
        self.assertEqual([x.info["dir"] for x in acts if x.kind == "focus"], ["right"])
        r3 = split_raw("right")
        r3["layouts"][0]["area"]["width"] = 116
        acts = actions.classify(state.Snapshot(r1, {"cols": 120}), state.Snapshot(r3, {"cols": 120}))
        self.assertIn("sidebar", [x.kind for x in acts])

    def test_corners(self):
        s = state.Snapshot(split_raw("right"), {"cols": 120})
        self.assertEqual(s.tab.corner("tl").id, "w1:p1")
        self.assertEqual(s.tab.corner("br").id, "w1:p2")


class HudTest(unittest.TestCase):
    def test_lines_are_exact_width(self):
        h = hud.Hud()
        h.set(title="1.2 Stacked", prompt="Split this pane top / bottom: `prefix+minus` " * 4,
              right="Herdling · 120 XP", msg="nice `prefix+v` **bold**", kind="ok", mode="prefix")
        for cols in (80, 101, 160):
            for line in h.lines(cols):
                self.assertEqual(markup.width(line), cols)

    def test_wrap_never_splits_chips(self):
        first, rest = markup.wrap("press `prefix+shift+n` then `prefix+shift+w` please", 20)
        self.assertEqual(first.count("`") % 2, 0)
        self.assertEqual(rest.count("`") % 2, 0)


class ContentTest(unittest.TestCase):
    def test_cards_fit(self):
        for cid, card in CARDS.items():
            for line in card["body"].splitlines():
                self.assertLessEqual(markup.visible_len(line), 78, f"card {cid}: {line!r}")
            view = CardView(card)
            self.assertIn(card["title"].split()[0], view.render(100, 40))

    def test_missions(self):
        ids = [m.id for m in ORDER]
        self.assertEqual(len(ids), len(set(ids)))
        for m in ORDER:
            self.assertTrue(m.steps[0].setup or m.id == "0.2" or m.id == "0.3" or m.id == "0.4",
                            f"{m.id} has no setup on its first step")
            for s in m.steps:
                for k in s.keys:
                    self.assertIn(k, BY_ID, f"{m.id}: unknown key id {k}")
                self.assertEqual(s.prompt.count("`") % 2, 0, f"{m.id}: unbalanced chips in {s.prompt!r}")
        self.assertEqual([w.num for w in WORLDS], list(range(len(WORLDS))))

    def test_key_bytes(self):
        self.assertEqual(key_bytes("prefix"), b"\x02")
        self.assertEqual(key_bytes("shift+l"), b"L")
        self.assertEqual(key_bytes("minus"), b"-")
        self.assertEqual(key_bytes("prefix", "ctrl+a"), b"\x01")


if __name__ == "__main__":
    unittest.main()
