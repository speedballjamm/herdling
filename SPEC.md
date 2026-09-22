# herdling: a game that teaches Herdr

> Learn Herdr by using real Herdr. Instructions sit in a bar under Herdr and the game
> watches what you do.

A sibling of [tmuse](../tmuse), which teaches tmux the same way. The game design (worlds,
missions, XP, stars, Dojo, Review, Sandbox) is carried over; the plumbing is new, because
Herdr isn't tmux.

---

## 1. Goals

| Goal | What it means in practice |
|---|---|
| **Assume zero knowledge** | World 0 covers "what is Herdr?", "hold Ctrl, press b, let go", and clicking. |
| **Real skills, not trivia** | Real keys and real clicks in a **real Herdr**, with stock key bindings. |
| **Teach what makes Herdr Herdr** | Workspaces, the sidebar, **agent states**, notifications, the CLI and socket API, not just "tmux with other keys". |
| **Mouse and keyboard** | Herdr is mouse-first; most topics have a click-it mission beside the key missions. |
| **Fun** | Missions, XP, ranks, streaks, boss levels, timed drills. |
| **Sticky** | Spaced-repetition review brings back the keys you fumbled. |
| **Safe** | A sandboxed Herdr. Never touches your sessions or `~/.config/herdr` unless you say so. |

---

## 2. Architecture

tmux let tmuse put its HUD in tmux's own multi-line status bar and read exact key
presses from tmux's message log. Herdr has neither, so herdling sits **in front of** the
Herdr client instead:

```
 ┌──────────────────────────── your terminal ────────────────────────────┐
 │ ┌ Herdr client (in a pty, told the screen is 3 rows shorter) ───────┐ │
 │ │ spaces        │  code   server   +                                 │ │
 │ │ · shop        │┌──────────────────┐┌──────────────────┐            │ │
 │ │               ││ claude (agent)   ││ $                │            │ │
 │ │ agents        ││                  ││                  │            │ │
 │ │ ● shop·code   │└──────────────────┘└──────────────────┘            │ │
 │ └────────────────────────────────────────────────────────────────────┘ │
 │ ▶ 5.2 A tap on the shoulder │ When the notice pops up, press prefix+o  │ ← HUD (drawn by
 │   (continuation)                                                       │    the proxy)
 │ PREFIX ✔ feedback / hints                        Herdling · 340 XP     │
 └─────────────────────────────────────────────────────────────────────────┘
        ▲ keys & mouse (copied to the key watcher)    ▲ 10×/s session.snapshot
        │                                              │
  ┌─────┴──────────── launcher process ────────────────┴──────────────────┐
  │ proxy.py   pty passthrough; HUD rows; lesson cards; clipboard (OSC 52)  │
  │ keyin.py   decodes legacy + kitty-protocol keys and SGR mouse; tracks   │
  │            Herdr's mode (prefix, copy, resize, navigate…)               │
  │ engine.py  (thread) mission state machine, goals, hints, coaching       │
  │ herdr.py   JSON socket API client                                       │
  └──────────────────────────────────────────────────────────────────────────┘
                        │ one-shot JSON requests over the unix socket
                 Herdr server (sandbox: XDG_CONFIG_HOME=~/.herdling/x)
```

### Key decisions

1. **Sandbox via XDG.** `XDG_CONFIG_HOME=~/.herdling/x` gives the game its own Herdr
   config dir: server, sockets, named sessions, logs, plugins. The game's server is the
   sandbox's *default* session, so plain `herdr` re-attaches, exactly as in real life.
   `HERDR_CONFIG_PATH` points at the practice config `~/.herdling/config.toml`.
2. **Pane shells undo the sandbox.** Herdr starts `$SHELL` in new panes; the game sets
   `SHELL` to `game/bin/hl-shell`, which restores your `XDG_CONFIG_HOME` (so git, nvim…
   find their config) and execs your real shell (login shell on macOS, like Herdr's
   `shell_mode = "auto"`). `herdr` inside a pane still reaches the game via the
   `HERDR_SOCKET_PATH` Herdr injects.
3. **The HUD lives under Herdr, not inside it.** The proxy tells Herdr the terminal is
   three rows shorter and draws the HUD in those rows (saving and restoring the cursor,
   inside a synchronized update, only at escape-sequence boundaries, redrawn after any
   erase). Herdr can't draw over it, and collapsing the sidebar can't hide it.
4. **Lesson cards are drawn by the proxy** over the whole screen. Herdr's output is
   swallowed meanwhile; afterwards the proxy shrinks the pty by one row for 80ms, which
   makes Herdr repaint everything. (Focus-in events don't trigger a repaint.) The engine
   ignores size-based changes during that wobble.
5. **State-based verification.** One `session.snapshot` call (~0.3ms) returns every
   workspace, tab, pane, layout rect, split direction and ratio, zoom flag, focus, and
   agent state. `actions.py` diffs snapshots into actions (`split-right`, `focus` with a
   direction, `swap`, `resize`, `sidebar`, `new-tab`, `agent`…), so mouse and CLI
   actions count as well as keys.
6. **Exact keys from the input stream.** Herdr turns on the kitty keyboard protocol
   (`CSI > 7 u`) and SGR mouse. The decoder understands those and legacy bytes; the
   tracker maps `prefix+key` to Herdr's action names and follows modes. This powers
   coaching ("`prefix+%` is tmux's split; in Herdr that's `prefix+v`"), the sandbox
   narration, and goals that leave no state behind (opening help, copy mode).
7. **Pretend agents.** `panes.py agent` is a tiny fake coding agent that reports
   `working` / `blocked` / `idle` through `pane.report_agent`, exactly like Herdr's real
   integrations. The agent missions need no Claude or Codex install.
8. **Clipboard.** On macOS Herdr copies with `pbcopy`, so copy goals read the clipboard
   (`pbpaste`, or `wl-paste` / `xclip` / `xsel`); OSC 52 writes seen by the proxy count too.
9. **Detach is real.** `prefix+q` ends the client; the launcher shows a practice prompt
   that runs real `herdr` commands (session list/attach/stop/delete, status, workspace
   list…) against the sandbox. `herdr`, `herdr --session NAME` and
   `herdr session attach NAME` re-enter through the proxy.

### Tech

- **Python 3.9+, standard library only.** `herdr ≥ 0.9`.
- Entry point `./herdling`; progress in `~/.herdling/progress.json`.
- Tests run the whole game inside an outer tmux, type real keystrokes and mouse
  sequences, and read the screen and Herdr's API.

---

## 3. Notation

The game writes keys the way Herdr's own help (`prefix+?`) does:

| Written | Means |
|---|---|
| `ctrl+b` | Hold **Ctrl**, press **b**, let go. This is the **prefix**. |
| `prefix+v` | Prefix, *then* press `v`. Two separate steps. |
| `prefix+shift+n` | Prefix, then Shift+n (a capital N). |
| `prefix+minus` | Prefix, then the `-` key. |

---

## 4. Curriculum (as built)

61 missions (53 core, 8 bonus). **Boss** missions are timed against par.

- **World 0 · Hello, Herdr:** a pane is a terminal; the prefix and `esc`; `prefix+?` and
  its `/` filter; clicking `+` and tabs.
- **World 1 · Panes 101:** `prefix+v`, `prefix+minus`, `prefix+h/j/k/l`, four corners,
  `prefix+tab`, `prefix+x` (no confirmation) and `exit`, `prefix+shift+p` names, click to
  focus (bonus). Boss: *The Quad*.
- **World 2 · Pane Power:** `prefix+z`, resize mode `prefix+r` + h/l/j/k + esc, drag a
  border (bonus), swap `prefix+shift+h/l`, sidebar `prefix+b`. Boss: *Blueprint*.
- **World 3 · Tabs:** `prefix+c` (named), `prefix+n`/`p`, `prefix+1..9`,
  `prefix+shift+t`, `prefix+shift+x`, click a tab (bonus). Boss: *Mission Control*.
- **World 4 · Workspaces:** `prefix+shift+n`, `prefix+shift+w`, navigate mode `prefix+w`
  (↑↓ Enter, digits), goto `prefix+g` with `/` search, `prefix+shift+d` + confirm,
  click a space (bonus). Boss: *The Juggler*.
- **World 5 · The Herd:** answer a blocked agent; a notification from another
  workspace and `prefix+o`; click an agent row; done vs idle. Boss: *Herding cats* (four
  agents, three projects).
- **World 6 · Detach & Sessions:** `prefix+q` and `herdr`; `herdr session list`; a named
  session (`herdr session attach work`, stop, delete (bonus)). Boss: *Survive the
  disconnect*.
- **World 7 · Copy Mode:** `prefix+[` and scrolling, `?` search, `v … y` copy, paste
  into another pane, drag to copy (bonus). Boss: *Log detective*.
- **World 8 · The Command Line:** `herdr pane current`, `workspace list`,
  `pane split --current --no-focus`, `pane run`, `pane read`, `tab create`,
  `notification show` (bonus). Boss: *Fleet*, a 3-pane tab built with commands.
- **World 9 · Make It Yours:** theme, a custom binding (`last_pane = "prefix+semicolon"`,
  then use it), a `tab_bar_right` clock, a `ctrl+alt` direct chord (bonus), and
  `herdling install`. Goals use `herdr config check` to explain mistakes.
- **World 10 · Final Boss:** *A day in the life*: set up a project, answer an agent,
  find the first error in streaming logs, detach, reattach, zoom into the agent's work.

---

## 5. Game systems

Carried over from tmuse: XP per mission (bonus for no hints and beating par), stars
(1–3), streaks, ranks (Lost Lamb → Herdling → Pane Wrangler → Layout Rancher → Tab
Tamer → Space Shepherd → Agent Whisperer → Session Keeper → Scrollback Sleuth → Script
Drover → Config Smith → Herd Master), tiered hints (free nudge after 20s, the exact key
after 45s at half XP, `herdling show` demos with the real keys at no XP), Dojo, Review
(Leitner boxes), Sandbox, cheat sheet, title menu with world select and settings.

---

## 6. Known limits

- The mode tracker infers Herdr's mode from keys, so a mouse click that closes a dialog
  can leave it briefly out of step. It never gates core progress on its own; the HUD
  badge only shows modes with unambiguous exits (prefix, copy, resize, navigate).
- Herdr only pops notifications for agents outside the tab you're looking at; missions
  that rely on `prefix+o` put the agent elsewhere.
- Herdr won't zoom a tab's only pane.
- Direct `ctrl+alt` chords depend on the terminal passing them through (bonus only).
