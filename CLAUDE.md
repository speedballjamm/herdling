# herdling

A game that teaches Herdr inside a real, sandboxed Herdr. Design and architecture: SPEC.md.
Missions are data in `game/worlds/wN.py`; the pretend programs that run in mission panes
(logs, tickers, inboxes, fake agents) are in `game/panes.py`.

## Constraints

- Python 3.9+, standard library only. No dependencies, no pyproject.
- Stock Herdr key bindings. Never touch the user's real `~/.config/herdr` or sessions; the
  game's Herdr lives under `$HERDLING_HOME/x` (default `~/.herdling/x`).

## Checks

```
python3 -m unittest tests/test_units.py     # <1s, no Herdr. Run after every change.
ruff check .                                # pyflakes rules (ruff.toml); CI runs it
python3 tests/test_missions.py 7            # plays world 7 with real keystrokes (~1 min)
python3 tests/test_missions.py              # every world, in parallel
python3 tests/test_modes.py [name]          # sandbox, dojo, review, hints, detach…
```

- The mission and mode tests need `herdr` and `tmux`. Run the worlds you touched before
  pushing: CI only runs them on PRs that change `game/**`, `tests/**` or `herdling`.
- World 7's copy/paste missions read the clipboard with `pbpaste`, so they only run on macOS.
- Every bug fix gets a test that fails without the fix: a unit test if the logic can be
  reached without Herdr, otherwise an assertion in the world's function in
  `tests/test_missions.py`. Check the test catches the bug by reverting the fix once.
- A mission clearing isn't proof it behaves: goals often pass before the player presses
  Enter. Assert on what the player would see next (see `assert_filed`).

## Debugging

- `tests/harness.py` runs the game in its own tmux server (`tmux -L hl-outer-<name>`) with
  its own `HERDLING_HOME` under `/tmp`. Keep that path short: Herdr's socket path must fit in
  about 104 bytes.
- A timed-out `wait` prints the title, screen and engine log tail. With
  `HERDLING_TEST_ARTIFACTS=dir`, failed games also save `screen.txt`, `engine.log`,
  `runtime.json`, `events.jsonl` and `proxy-debug.log` to `dir/<name>/`. CI uploads these
  as `evidence-<os>` when herdr-compat fails.
- In a game: `$HERDLING_HOME/engine.log` (engine), `run/runtime.json` (title, prompt, hints),
  `run/events.jsonl` (commands sent to the engine). `HERDLING_PROXY_DEBUG=file` logs why the
  HUD isn't drawn. Talk to the game's Herdr directly with
  `XDG_CONFIG_HOME=$HERDLING_HOME/x herdr session list`.
- `HERDLING_DOJO_SECS` shortens Dojo rounds; `HERDLING_ONCE=1` exits after one mission.

## Releasing

Bump `game/__init__.py` and the tag in `packaging/herdling.rb`'s url together (a unit test
checks they match). The repo's formula keeps the placeholder `sha256 "SHA256"`; the real
sha256 goes in `Formula/herdling.rb` in speedballjamm/homebrew-tap after the GitHub release
`vX.Y.Z` exists.
