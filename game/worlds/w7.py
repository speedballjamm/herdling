"""World 7: copy mode, scrollback, copy and paste."""
import random

from .common import (Mission, P, R, Step, World, answered, copied_has, pane_contains, rand_code, reset)


def buried(before=220, after=60, word="SECRET"):
    """A pane whose log has a code buried `before` lines up."""
    def setup(c):
        code = rand_code()
        c.mem["code"] = code
        reset(c, tabs=[("logs", P("server-log", "log", random.randint(1, 10 ** 6), f"{word}: {code}", before, after))])
    return setup


def short_code(c):
    code = rand_code()
    c.mem["code"] = code
    reset(c, tabs=[("copy", P("notes", "banner", f"Today's deploy code is {code}  (copy it!)"))])


def two_panes(c):
    code = rand_code()
    c.mem["code"] = code
    reset(c, tabs=[("copy", R(P("from", "banner", f"Copy me: {code}"), P("to")))], focus_pane="from")


def incident(c):
    first = f"req-{random.randint(10000, 99999)}"
    decoys = [f"req-{random.randint(10000, 99999)}" for _ in range(3)]
    c.mem["code"], c.mem["decoys"] = first, decoys
    reset(c, tabs=[("incident", R(P("incident", "incident", random.randint(1, 10 ** 6), first, ",".join(decoys), 0.02),
                                  P("ticket", "banner", "TICKET #4411: paste the FIRST error's request id here"),
                                  ratio=0.62))], focus_pane="incident")


def ticket_has(c):
    s = c.s
    p = s.pane_labelled("ticket")
    if not p:
        return False
    text = c.read(p.id)
    lines = [l for l in text.splitlines() if "TICKET #" not in l]
    body = "\n".join(lines)
    if c.mem["code"] in body:
        return True
    for d in c.mem.get("decoys", []):
        if d in body:
            c.say("That's an ERROR, but not the FIRST one. Look further up.")
    return False


def in_copy(c):
    return c.tracker_mode() == "copy"


WORLD = World(7, "Copy Mode", card="copy", missions=[
    Mission("7.1", "Look back", xp=60, par=90, steps=[
        Step("A code scrolled off the top of this log. Enter copy mode: `prefix+[`",
             setup=buried(),
             goal=lambda c: c.pressed("copy_mode"),
             hints=["Prefix, then [ (left square bracket).", "`ctrl+b` then `[`"],
             keys=["copy-mode"], demo=["prefix+["],
             done="COPY mode: the pane holds still for you. (Its program keeps running.)"),
        Step("Scroll up to find the **SECRET** line: `k`, `PageUp`, or `ctrl+u` (half a page). "
             "Then `q` to leave, and type **herdling answer CODE**.",
             goal=lambda c: answered(c, c.mem["code"]),
             hints=["It's about 220 lines up. ctrl+u a few times is quickest. The mouse wheel works too.",
                    "When you see SECRET: WORD-123, press q, then type: herdling answer WORD-123"],
             keys=["copy-move"],
             done="Copy mode lets you read everything the pane printed, however long ago."),
    ]),
    Mission("7.2", "Search", xp=60, par=90, steps=[
        Step("Another buried code, further up. In copy mode, search backwards: `?` then type "
             "**PASSWORD**, Enter. Then answer with **herdling answer CODE**.",
             setup=buried(before=400, after=120, word="PASSWORD"),
             goal=lambda c: answered(c, c.mem["code"], strip=("PASSWORD:",)),
             hints=["`prefix+[` first. ? searches up (back in time), / searches down. n repeats.",
                    "`prefix+[` `?` PASSWORD `enter`, read it, `q`, herdling answer …"],
             expect=["copy_mode"], keys=["copy-search"],
             done="Searching beats scrolling. Uppercase letters make the search case-sensitive."),
    ]),
    Mission("7.3", "Copy that", xp=70, par=90, steps=[
        Step("Copy the deploy code: `prefix+[`, move onto it, `v` to start selecting, `E` to "
             "reach the end of the code, `y` to copy.",
             setup=short_code,
             goal=lambda c: copied_has(c, c.mem["code"]),
             hints=["In copy mode: k moves up, w jumps a word, 0 goes to the line start. Space also selects, "
                    "Enter also copies.",
                    "`prefix+[` `?` then the code's first word, `enter`, `v`, `E`, `y`"],
             keys=["copy-select"],
             done="Copied to your system clipboard: it pastes anywhere, even outside Herdr."),
    ]),
    Mission("7.4", "Paste it over there", xp=60, par=90, steps=[
        Step("Copy the code in the left pane (any way you like), then click the right pane and "
             "**paste** it with your terminal's paste (Cmd+V on a Mac, Ctrl+Shift+V on Linux).",
             setup=two_panes,
             goal=lambda c: bool(c.s.pane_labelled("to")) and pane_contains(c, c.s.pane_labelled("to").id,
                                                                            c.mem["code"]),
             hints=["Herdr has no paste key of its own: your terminal's paste goes straight to the focused pane.",
                    "Copy with `prefix+[` … `y` (or drag over it), `prefix+l`, then Cmd+V"],
             keys=["paste"],
             done="Copy in Herdr, paste like anywhere else."),
    ]),
    Mission("7.5", "Drag to copy", xp=40, par=40, bonus=True, steps=[
        Step("Use the mouse: **drag** across the deploy code. It's copied the moment you let go.",
             setup=short_code,
             goal=lambda c: c.dragged() and copied_has(c, c.mem["code"]),
             hints=["Press on the first letter of the code, drag to its last digit, let go. "
                    "(Double-click selects a word, too.)"],
             keys=["drag-copy"],
             done="No copy mode needed. A small 'copied' notice pops up at the bottom."),
    ]),
    Mission("7.6", "BOSS: Log detective", xp=200, par=180, boss=True, steps=[
        Step("BOSS! Payments are failing. In the incident log, find the request id (req-…) of the "
             "**FIRST** ERROR, copy it, and paste it into the **ticket** pane.",
             setup=incident,
             goal=ticket_has,
             hints=["Copy mode, then `?` ERROR searches up; `N` goes the other way. Keep going to the first one.",
                    "Copy the req-12345 with v … y, `prefix+l` to the ticket pane, then paste."]),
    ]),
])
