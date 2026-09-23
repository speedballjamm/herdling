"""Every key and command the game teaches. Drives the cheat sheet, sandbox
narration and spaced-repetition review.

Keys are written like Herdr's own help panel (prefix+?): `prefix+v` means press
the prefix (Ctrl+b), let go, then press v.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Key:
    id: str
    keys: str       # how to press it, e.g. "prefix+v"
    desc: str
    world: int
    action: str = ""   # Herdr's config name for it (keys.<action> in config.toml)
    group: str = ""


KEYS = [
    # World 0
    Key("prefix", "ctrl+b", "The prefix: press it, let go, then press an action key", 0, "prefix", "Basics"),
    Key("help", "prefix+?", "Show every key binding (/ filters, esc closes)", 0, "help", "Basics"),
    Key("mouse", "click", "Herdr is mouse-first: click panes, tabs, workspaces, +", 0, "", "Basics"),
    # World 1
    Key("split-right", "prefix+v", "Split: new pane on the right", 1, "split_vertical", "Panes"),
    Key("split-down", "prefix+minus", "Split: new pane below (the - key)", 1, "split_horizontal", "Panes"),
    Key("focus", "prefix+h/j/k/l", "Move to the pane left / down / up / right", 1, "focus_pane_left", "Panes"),
    Key("cycle", "prefix+tab", "Cycle to the next pane (shift+tab: previous)", 1, "cycle_pane_next", "Panes"),
    Key("close-pane", "prefix+x", "Close the focused pane (no confirmation!)", 1, "close_pane", "Panes"),
    Key("exit", "exit", "Typing exit (or ctrl+d) in a shell closes its pane", 1, "", "Panes"),
    Key("rename-pane", "prefix+shift+p", "Name the focused pane", 1, "rename_pane", "Panes"),
    Key("click-pane", "click a pane", "Click a pane to focus it", 1, "", "Panes"),
    # World 2
    Key("zoom", "prefix+z", "Zoom the focused pane to fill the tab (again to undo)", 2, "zoom", "Pane power"),
    Key("resize", "prefix+r", "Resize mode: h/l width, j/k height, esc done", 2, "resize_mode", "Pane power"),
    Key("drag-border", "drag a border", "Drag a split border with the mouse to resize", 2, "", "Pane power"),
    Key("swap", "prefix+shift+h/j/k/l", "Swap the pane with its neighbour", 2, "swap_pane_left", "Pane power"),
    Key("sidebar", "prefix+b", "Collapse / expand the sidebar", 2, "toggle_sidebar", "Pane power"),
    # World 3
    Key("new-tab", "prefix+c", "New tab (type a name, Enter)", 3, "new_tab", "Tabs"),
    Key("next-tab", "prefix+n", "Next tab", 3, "next_tab", "Tabs"),
    Key("prev-tab", "prefix+p", "Previous tab", 3, "previous_tab", "Tabs"),
    Key("switch-tab", "prefix+1..9", "Jump to tab N", 3, "switch_tab", "Tabs"),
    Key("rename-tab", "prefix+shift+t", "Rename the tab", 3, "rename_tab", "Tabs"),
    Key("close-tab", "prefix+shift+x", "Close the tab", 3, "close_tab", "Tabs"),
    Key("click-tab", "click a tab", "Click a tab (or the +) in the tab bar", 3, "", "Tabs"),
    # World 4
    Key("new-ws", "prefix+shift+n", "New workspace (a project)", 4, "new_workspace", "Workspaces"),
    Key("rename-ws", "prefix+shift+w", "Rename the workspace", 4, "rename_workspace", "Workspaces"),
    Key("navigate", "prefix+w", "Navigate mode: ↑/↓ workspaces, Enter opens, esc back", 4, "workspace_picker",
        "Workspaces"),
    Key("goto", "prefix+g", "Goto: search every pane in every workspace", 4, "goto", "Workspaces"),
    Key("close-ws", "prefix+shift+d", "Close the workspace (Enter confirms)", 4, "close_workspace", "Workspaces"),
    Key("click-ws", "click a space", "Click a workspace in the sidebar", 4, "", "Workspaces"),
    # World 5
    Key("agents-panel", "sidebar: agents", "The sidebar lists every agent and its state", 5, "", "Agents"),
    Key("open-notif", "prefix+o", "Jump to the agent that just needed you", 5, "open_notification_target",
        "Agents"),
    Key("click-agent", "click an agent", "Click an agent row to jump to it", 5, "", "Agents"),
    # World 6
    Key("detach", "prefix+q", "Detach: leave Herdr, everything keeps running", 6, "detach", "Sessions"),
    Key("herdr", "herdr", "(outside) Start or re-attach to your session", 6, "", "Sessions"),
    Key("session-list", "herdr session list", "(outside) List sessions", 6, "", "Sessions"),
    Key("session-attach", "herdr session attach NAME", "(outside) Attach to (or create) a named session", 6, "",
        "Sessions"),
    Key("session-stop", "herdr session stop NAME", "(outside) Stop a session and its panes", 6, "", "Sessions"),
    Key("session-delete", "herdr session delete NAME", "(outside) Delete a stopped session", 6, "", "Sessions"),
    # World 7
    Key("copy-mode", "prefix+[", "Copy mode: scroll the past (q leaves)", 7, "copy_mode", "Copy mode"),
    Key("copy-move", "k j PgUp PgDn", "Move / scroll in copy mode (ctrl+u / ctrl+d half pages)", 7, "",
        "Copy mode"),
    Key("copy-top", "g G", "Jump to the oldest / newest line in copy mode", 7, "", "Copy mode"),
    Key("copy-search", "/ and ?", "Search forward / back in copy mode (n / N repeat)", 7, "", "Copy mode"),
    Key("copy-select", "v … y", "Select (v or Space), then copy (y or Enter)", 7, "", "Copy mode"),
    Key("drag-copy", "drag to select", "Drag with the mouse to copy, no copy mode needed", 7, "", "Copy mode"),
    Key("paste", "Cmd+V", "Paste with your terminal's normal paste", 7, "", "Copy mode"),
    # World 8
    Key("cli-list", "herdr workspace list", "(in a pane) See workspaces, tabs, panes as JSON", 8, "", "CLI"),
    Key("cli-split", "herdr pane split", "(in a pane) Split from a script", 8, "", "CLI"),
    Key("cli-run", "herdr pane run ID CMD", "(in a pane) Run a command in another pane", 8, "", "CLI"),
    Key("cli-read", "herdr pane read ID", "(in a pane) Read another pane's output", 8, "", "CLI"),
    Key("cli-tab", "herdr tab create", "(in a pane) Make a tab from a script", 8, "", "CLI"),
    Key("cli-notify", "herdr notification show", "(in a pane) Pop up a notification", 8, "", "CLI"),
    # World 9
    Key("reload", "prefix+shift+r", "Reload config.toml", 9, "reload_config", "Config"),
    Key("conf-theme", "[theme] name", "Config: pick a theme", 9, "", "Config"),
    Key("conf-key", "[keys] action = \"…\"", "Config: bind a key", 9, "", "Config"),
    Key("conf-status", "[ui] tab_bar_right", "Config: a status area in the tab bar", 9, "", "Config"),
]

BY_ID = {k.id: k for k in KEYS}

# Herdr action (from the key watcher) -> key id, for narration and review.
BY_ACTION = {}
for _k in KEYS:
    if _k.action:
        BY_ACTION.setdefault(_k.action, _k.id)
for _a in ("focus_pane_down", "focus_pane_up", "focus_pane_right"):
    BY_ACTION[_a] = "focus"
for _a in ("swap_pane_down", "swap_pane_up", "swap_pane_right"):
    BY_ACTION[_a] = "swap"
BY_ACTION["cycle_pane_previous"] = "cycle"
for _i in range(1, 10):
    BY_ACTION[f"switch_tab_{_i}"] = "switch-tab"

ACTION_TEXT = {
    "help": "keybinds panel", "settings": "settings", "detach": "detach", "reload_config": "reload config",
    "open_notification_target": "jump to the agent that needs you", "workspace_picker": "navigate mode",
    "goto": "goto: search every pane", "new_workspace": "new workspace", "new_worktree": "new git worktree",
    "rename_workspace": "rename workspace", "close_workspace": "close workspace", "new_tab": "new tab",
    "rename_tab": "rename tab", "previous_tab": "previous tab", "next_tab": "next tab", "close_tab": "close tab",
    "rename_pane": "rename pane", "edit_scrollback": "open scrollback in your editor", "copy_mode": "copy mode",
    "zoom": "zoom", "resize_mode": "resize mode", "toggle_sidebar": "toggle sidebar",
    "focus_pane_left": "focus pane left", "focus_pane_down": "focus pane down", "focus_pane_up": "focus pane up",
    "focus_pane_right": "focus pane right", "cycle_pane_next": "next pane", "cycle_pane_previous": "previous pane",
    "split_vertical": "split right", "split_horizontal": "split down", "close_pane": "close pane",
    "swap_pane_left": "swap pane left", "swap_pane_down": "swap pane down", "swap_pane_up": "swap pane up",
    "swap_pane_right": "swap pane right", "send_prefix": "send ctrl+b to the program", "cancel": "cancel",
    "last_pane": "last pane", "next_workspace": "next workspace", "previous_workspace": "previous workspace",
}


def describe(action):
    if action and action.startswith("switch_tab_"):
        return f"go to tab {action[-1]}"
    return ACTION_TEXT.get(action, action or "")


def get(kid):
    return BY_ID[kid]
