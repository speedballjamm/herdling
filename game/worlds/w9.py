"""World 9: make Herdr yours with config.toml."""
import subprocess

from .. import conf, herdr as herdr_mod, paths
from .common import Mission, P, R, Step, World, reset

THEMES = {"catppuccin", "catppuccin-latte", "terminal", "tokyo-night", "tokyo-night-day", "dracula", "nord",
          "gruvbox", "gruvbox-light", "one-dark", "one-light", "solarized", "solarized-light", "kanagawa",
          "kanagawa-lotus", "rose-pine", "rose-pine-dawn", "vesper"}


def config_issues():
    """Herdr's own verdict on the practice config (empty list = all good)."""
    try:
        r = subprocess.run([herdr_mod.herdr_bin(), "config", "check"], env=herdr_mod.game_env(),
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if r.returncode == 0:
        return []
    return [l for l in r.stdout.splitlines() + r.stderr.splitlines() if l and not l.startswith("config:")]


def reloaded(c):
    """Reloaded (prefix+shift+r) since the step began."""
    return c.pressed("reload_config")


def check_after_reload(c, ok):
    """After a reload that didn't do the job, say why (using Herdr's own checker)."""
    if reloaded(c) and not ok and not c.mem.get("checked"):
        c.mem["checked"] = True
        issues = config_issues()
        if issues:
            c.say("Herdr says: " + issues[0])
        else:
            c.say("Reloaded, but that setting isn't in the file yet. Did you save? (nano: ctrl+o, Enter)")
    if c.just_pressed("reload_config"):
        c.mem["checked"] = False


def theme_set(c):
    name = conf.get(conf.load(), "theme", "name")
    ok = isinstance(name, str) and name in THEMES and name != "catppuccin"
    check_after_reload(c, ok and reloaded(c))
    return ok and reloaded(c)


def key_bound(c):
    binding = conf.get(conf.load(), "keys", "last_pane")
    ok = bool(binding)
    check_after_reload(c, ok and reloaded(c))
    return ok and reloaded(c) and not config_issues()


def used_last_pane(c):
    if not c.pressed("last_pane"):
        return False
    return c.s.fpane == c.mem.get("start_pane")


def status_set(c):
    entries = conf.get(conf.load(), "ui", "tab_bar_right") or []
    ok = isinstance(entries, list) and any(isinstance(e, dict) and e.get("type") == "datetime" for e in entries)
    check_after_reload(c, ok and reloaded(c))
    return ok and reloaded(c)


def chord_bound(c):
    z = conf.get(conf.load(), "keys", "zoom")
    zs = z if isinstance(z, list) else [z]
    ok = any(isinstance(b, str) and not b.startswith("prefix") for b in zs)
    check_after_reload(c, ok and reloaded(c))
    return ok and reloaded(c) and not config_issues()


def two_panes(c):
    conf.ensure()
    reset(c, tabs=[("config", R(P("left"), P("right")))], focus_pane="left")
    c.mem["start_pane"] = c.s.pane_labelled("left").id if c.s.pane_labelled("left") else None


def installed(c):
    for e in c.events:
        if e.get("type") == "install":
            return True
    return False


EDIT = f"Open it with **herdling edit** (or: nano {paths.CONFIG_TILDE})."

WORLD = World(9, "Make It Yours", card="config", missions=[
    Mission("9.1", "A new look", xp=60, par=180, steps=[
        Step(f"Change the theme. {EDIT} Under [theme], make the name line **name = \"tokyo-night\"** "
             "(remove the #), save, then reload: `prefix+shift+r`",
             setup=two_panes,
             goal=theme_set,
             hints=["In nano: arrow down to the line, delete the #, change the name, ctrl+o Enter to save, "
                    "ctrl+x to leave. Then prefix+shift+r.",
                    "The line should read exactly:  name = \"tokyo-night\"   (any theme from the list works)"],
             keys=["reload", "conf-theme"],
             done="New colours, no restart. Edit, save, `prefix+shift+r`: that's the config loop."),
    ]),
    Mission("9.2", "A key of your own", xp=80, par=240, steps=[
        Step("Herdr has a 'last pane' action with no key. Give it one: under [keys] add "
             "**last_pane = \"prefix+semicolon\"**, save, `prefix+shift+r`.",
             setup=two_panes,
             goal=key_bound,
             hints=[f"{EDIT} The line goes after the [keys] heading.",
                    "last_pane = \"prefix+semicolon\"  then save, and prefix+shift+r"],
             keys=["conf-key"],
             done="Bound. Every action in `prefix+?` has a name you can bind like that."),
        Step("Try it: go to the right pane (`prefix+l`), then jump back with `prefix+;`",
             goal=used_last_pane,
             hints=["`prefix+l`, then `prefix+;` (semicolon)."],
             done="Your own shortcut, in your own config."),
    ]),
    Mission("9.3", "A clock", xp=60, par=180, steps=[
        Step("Put a clock in the tab bar: under [ui] make it "
             "**tab_bar_right = [{ type = \"datetime\", format = \"%H:%M\" }]**, save, `prefix+shift+r`.",
             setup=two_panes,
             goal=status_set,
             hints=[f"{EDIT} Replace the commented tab_bar_right line under [ui].",
                    "tab_bar_right = [{ type = \"datetime\", format = \"%H:%M\" }]"],
             keys=["conf-status"],
             done="Top right: the time. Try hostname, zoom, text, or a command's output next."),
    ]),
    Mission("9.4", "No prefix needed", xp=60, par=240, bonus=True, steps=[
        Step("Add a direct chord for zoom: under [keys], **zoom = [\"prefix+z\", \"ctrl+alt+z\"]**, "
             "save, `prefix+shift+r`. Then press ctrl+alt+z.",
             setup=two_panes,
             goal=lambda c: chord_bound(c) and bool(c.s.tab and c.s.tab.zoomed),
             hints=["ctrl+alt chords are the safest 'no prefix' keys across terminals. On a Mac, alt is Option.",
                    "If ctrl+alt+z does nothing, your terminal kept it: `prefix+z` still works."],
             done="Prefix keys never clash with your programs; direct chords are faster. Mix as you like."),
    ]),
    Mission("9.5", "Take it home", xp=50, par=600, steps=[
        Step("Your config is ready. Want it as your real Herdr config? Type **herdling install** in a "
             "pane (it shows you the file and asks first; your old one is backed up).",
             setup=two_panes,
             goal=installed,
             hints=["herdling install. You can say no: the practice copy stays in ~/.herdling/."]),
    ]),
])
