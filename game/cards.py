"""Lesson cards: short explanations shown full-screen before new ideas.

Markup: `keys` become key chips, **bold** is bold. Keep lines under ~74 chars.
"""
from . import progress

CARDS = {
    "welcome": {
        "title": "Welcome to herdling",
        "body": """\
**Herdr** is a terminal workspace manager for AI coding agents. Like tmux,
a background **server** keeps your terminals running; you attach to see them.

  the Herdr **server** (runs in the background, survives you leaving)
   └─ **workspace** "api"        one per project (the sidebar lists them)
       ├─ **tab** "code"         a screen layout inside the project
       │   ├─ **pane**           a real terminal ┐ split side by side
       │   └─ **pane**           a real terminal ┘ or stacked
       └─ **tab** "logs"
  and **agents**: Herdr spots Claude, Codex & co in panes and shows
  whether each is working, blocked on a question, or done.

**You are inside a real Herdr right now** (a private practice copy).
The three coloured lines at the very bottom are the **game**: your
mission, then tips. Everything above them is Herdr itself.

Stuck? Type these in any pane:  `herdling hint`  `herdling skip`
`herdling show` (watch it done)   `herdling task` (reprint the task)
""",
    },
    "prefix": {
        "title": "The prefix key",
        "body": """\
Most Herdr shortcuts start with the **prefix**: `ctrl+b`

  `ctrl+b` means: **hold Ctrl, tap b, then let go of both.**

Then press the action key **on its own**. So `prefix+v` is two moves:

   1. Ctrl+b   (let go!)        2. v

The prefix tells Herdr "the next key is for you, not the shell".
Without it, keys go straight to the program in the pane, as normal.

Herdr shows a **PREFIX** bar at the bottom while it waits for that
second key (so does the game's bar). `esc` cancels.

Written like Herdr's own help: `prefix+shift+n` = prefix, then Shift+n.
Coming from tmux? Same idea, same ctrl+b, but different action keys.
""",
    },
    "mouse": {
        "title": "Mouse first",
        "body": """\
Unlike tmux, Herdr is built for the mouse. Everything is clickable:

  • click a **pane** to focus it; drag a **border** to resize
  • click a **tab** at the top, or **+** for a new one
  • click a **workspace** or an **agent** in the sidebar on the left
  • **right-click** anything for a menu of what you can do there
  • **drag** over text to select it: it's copied straight away

You never *need* a key binding. The keys are for speed, and this game
teaches both: a mouse way, then the keys that save you the reach.
""",
    },
    "panes": {
        "title": "World 1: Panes",
        "body": """\
A **pane** is a rectangle with its own shell. Split one into two:

   `prefix+v`  side by side          `prefix+minus`  stacked
   ┌─────┬─────┐                     ┌───────────┐
   │     │     │                     │           │
   │     │     │                     ├───────────┤
   │     │     │                     │           │
   └─────┴─────┘                     └───────────┘

Memory trick: **v** draws a **v**ertical line; **-** draws a horizontal one.

One pane is **focused** (brighter border; your typing goes there).
Move with vim's keys:  `prefix+h` ←  `prefix+j` ↓  `prefix+k` ↑  `prefix+l` →
or cycle with `prefix+tab`. Or just click the pane you want.

tmux habits that **don't** work here: `%` `"` and prefix+arrows.
""",
    },
    "close": {
        "title": "Closing panes",
        "body": """\
Two ways to close a pane:

  • `prefix+x`  closes the focused pane **immediately** (no y/n question,
    unlike tmux: be sure first)
  • type `exit` (or press ctrl+d) in the shell. When a pane's program
    ends, the pane closes.

Closing a tab's last pane closes the tab; closing a workspace's last
tab closes the workspace. The Herdr server keeps running regardless.
""",
    },
    "pane_power": {
        "title": "World 2: Pane power",
        "body": """\
You can split. Now **control** your panes:

  `prefix+z`             zoom: the focused pane fills the tab (again: undo)
  `prefix+r`             resize mode: h/l move a side border, j/k a
                         top/bottom one; tap as often as you like, `esc` done
  `prefix+shift+h/j/k/l` swap the pane with its neighbour that way
  `prefix+b`             collapse / expand the sidebar

With the mouse: **drag** any border to resize.

Zoom is the one you'll use most: work in a small pane, zoom it to full
size to read something, then zoom back out.
""",
    },
    "resize": {
        "title": "Resize mode",
        "body": """\
tmux resizes with a key per nudge. Herdr has a **mode** instead:

   `prefix+r`   enter resize mode   (RESIZE shows at the bottom)
   `h` `l`       move the border left / right
   `j` `k`       move the border down / up
   `esc`         done

No holding keys, no repeating the prefix: tap h/l/j/k until it looks
right, then escape. Or skip the keys and drag the border with the mouse.
""",
    },
    "blueprint": {
        "title": "Boss: Blueprint",
        "body": """\
Build this layout, starting from a single pane:

        ┌──────────────────┬─────────┐
        │                  │    B    │
        │                  ├─────────┤
        │        A         │    C    │
        │                  ├─────────┤
        │                  │    D    │
        └──────────────────┴─────────┘

Then make A **wider than half** the screen, and finally
**zoom the bottom-right pane (D)**.
""",
    },
    "tabs": {
        "title": "World 3: Tabs",
        "body": """\
A **tab** is a whole layout of panes inside a workspace, like browser tabs.
Use them for different views of one project: `code`, `server`, `logs`.

  `prefix+c`          new tab (Herdr asks for a name: type it, Enter)
  `prefix+n` / `p`    next / previous tab
  `prefix+1` … `9`    jump to tab N (counting from the left)
  `prefix+shift+t`    rename the tab
  `prefix+shift+x`    close the tab (no confirmation)

The tab bar is the top row. Click a tab to switch, click **+** for a new
one, right-click a tab for a menu.

tmux calls these **windows**, and uses c, n, p and numbers the same way.
""",
    },
    "workspaces": {
        "title": "World 4: Workspaces",
        "body": """\
A **workspace** is a project: one per repo, task or investigation. Each has
its own tabs and panes. The sidebar's top half ("spaces") lists them.

  `prefix+shift+n`    new workspace (named after its folder)
  `prefix+shift+w`    rename it
  `prefix+w`          navigate mode: ↑/↓ pick a workspace, Enter opens,
                      1-9 jumps, esc leaves
  `prefix+g`          goto: a searchable tree of **every** pane anywhere
  `prefix+shift+d`    close the workspace (asks to confirm)

The sidebar shows each workspace's agents too (World 5), so you can see
at a glance which project needs you.
""",
    },
    "navigate": {
        "title": "Navigate mode",
        "body": """\
`prefix+w` opens **navigate mode**: a keyboard remote for the sidebar.

   ↑ ↓          move between workspaces
   Enter        open the highlighted one
   1 … 9        jump straight to workspace N
   h j k l      move between panes (← → work too)
   tab          cycle panes
   esc          back to normal

The bottom bar says NAVIGATE while it's on, and it stays on until you
leave: handy when you're hopping around a lot.
""",
    },
    "agents": {
        "title": "World 5: The herd",
        "body": """\
This is what Herdr is for. Run coding agents (Claude Code, Codex, Gemini,
pi, OpenCode…) in panes, and Herdr **recognises** them and tracks each one:

   **working**   busy: leave it alone
   **blocked**   waiting for YOU: a question, an approval
   **done**      finished, and you haven't looked yet
   **idle**      finished and seen: ready for more

The sidebar's lower half lists every agent in every workspace, with a
coloured dot for its state. Workspaces show their agents' state too.

When a background agent needs you, Herdr pops up a notice. Then:
   `prefix+o`    jump straight to the agent that needs you
   or **click** its row in the agents list.

The agents here are pretend (so you don't need any installed), but
they report state to Herdr exactly the way the real integrations do.
""",
    },
    "sessions": {
        "title": "World 6: Detach & sessions",
        "body": """\
Herdr's **server** runs in the background and owns every pane. The screen
you're looking at is just a **client** attached to it. So you can:

   `prefix+q`     **detach**: the client quits, the server keeps everything
                 running (builds, servers, agents, all of it)
   `herdr`        attach again, from any terminal, later

That's why people run agents in Herdr: close the laptop lid, lose the SSH
connection, and the work carries on. Come back and pick up where it is.

After you detach you'll land in **your own shell**. While the game runs,
herdr commands there go to the game's Herdr.
""",
    },
    "detach": {
        "title": "Detach",
        "body": """\
`prefix+q` detaches. Nothing stops: it only closes this view.

    you ──(client)──┐
                    ├── Herdr server ── panes, agents, jobs…
    later ─(herdr)──┘

(tmux users: it's `prefix+q`, not `d`.)

To really stop everything: `herdr server stop` (don't, yet!).
""",
    },
    "named_sessions": {
        "title": "Named sessions",
        "body": """\
Normally you want one Herdr and lots of **workspaces** inside it. But
sometimes you want a completely separate Herdr: its own server, panes,
workspaces and socket. That's a **named session**:

   `herdr session attach work`    attach to "work" (starting it if needed)
   `herdr --session work`         the same
   `herdr session list`           what exists, and what's running
   `herdr session stop work`      stop it (its panes end)
   `herdr session delete work`    forget a stopped one

Plain `herdr` always means the **default** session.
""",
    },
    "copy": {
        "title": "World 7: Copy mode",
        "body": """\
`prefix+[` enters **copy mode** on the focused pane: it stops following
the output so you can read, search and copy. (The program keeps running.)

  move      `k` `j` (lines)  `ctrl+u` `ctrl+d` (half pages)  PageUp/PageDown
            `w` `b` `e` words, `W` `B` `E` whole WORDS, `{` `}` paragraphs
  search    `?` up (back in time), `/` down, then `n` / `N` repeat
  select    `v` (or Space) starts, move to the end, `y` (or Enter) copies
  leave     `q` or `esc`

Copies go to your **system clipboard**; paste with your terminal's normal
paste (Cmd+V / Ctrl+Shift+V). With the mouse: **drag** to copy, **wheel**
to scroll back, no copy mode needed.
""",
    },
    "cli": {
        "title": "World 8: The command line",
        "body": """\
Everything you can click, a script can do. Inside a Herdr pane, the `herdr`
command talks to the Herdr that owns it, and prints JSON:

   `herdr pane current`                   which pane am I? (id like w1:p2)
   `herdr workspace list` / `tab list` / `pane list`
   `herdr pane split --current --direction right --no-focus`
   `herdr pane run ID "npm test"`          type a command into another pane
   `herdr pane read ID`                    read another pane's output
   `herdr pane wait-output ID --match OK`  wait until it prints something
   `herdr tab create --label build`
   `herdr notification show "done!"`

This is how coding agents use Herdr: they split a pane, run the tests in
it, read the result, and never steal your cursor.
""",
    },
    "config": {
        "title": "World 9: Make it yours",
        "body": """\
Herdr reads **~/.config/herdr/config.toml**. In this game, it reads a
practice copy: **~/.herdling/config.toml** (open it with `herdling edit`).

   [theme]
   name = "tokyo-night"             # sections in [brackets], then key = value

   [keys]
   last_pane = "prefix+semicolon"   # any action from prefix+? can be bound

   [ui]
   tab_bar_right = [{ type = "datetime", format = "%H:%M" }]

Save, then `prefix+shift+r` reloads it: no restart. `herdr config check`
tells you if anything is wrong. `herdr --default-config` lists every option.
""",
    },
    "final": {
        "title": "Final boss: A day in the life",
        "body": """\
One last job, and it's a whole working day:

  • set up a new project with the right tabs and panes
  • an agent starts working; answer it when it needs you
  • errors appear in the logs: dig the first one out of the scrollback
  • go home (detach), come back (attach), and review the agent's work

Everything you've learned, in one go. Hints are there if you need them.
Good luck, shepherd.
""",
    },
    "graduation": {
        "title": "You herded it all!",
        "body": """\
You've cleared every core mission. You can now:

  • split, move, zoom, resize, swap and name panes
  • juggle tabs and whole workspaces, by key and by mouse
  • keep an eye on a herd of agents and jump to the one that needs you
  • detach, reattach, and run separate named sessions
  • dig through scrollback, copy and paste
  • drive Herdr from scripts with the herdr CLI
  • make Herdr yours with config.toml

Everything you learned works in a normal `herdr`. Run it in a project
folder and start an agent: `herdr` → `claude` (or codex, pi…).
The sandbox is yours now; your cheat sheet: `herdling cheat`.

Made by James Moult. If herdling helped, a star or a sponsor keeps
it going: github.com/sponsors/speedballjamm   (thank you!)
""",
    },
}


def world_complete(world, data, worlds):
    stars = sum(data["missions"].get(m.id, {}).get("stars", 0) for m in world.missions)
    total = 3 * len(world.missions)
    bonus = [m for m in world.missions if m.bonus and not progress.completed(data, m.id)]
    body = (f"World {world.num}, **{world.title}**: cleared!\n\n"
            f"Stars: {stars} / {total}      Rank: **{progress.rank(data, worlds)}**      XP: {data['xp']}\n\n")
    if bonus:
        body += "Bonus missions still open (World select in the menu):\n"
        body += "".join(f"  • {m.id} {m.title}\n" for m in bonus)
    body += "\nKeys you learned here are now in `herdling cheat` and in the Review deck."
    return {"title": "World complete!", "body": body}
