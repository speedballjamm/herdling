"""Read the practice config.toml well enough to follow along (Python 3.9 has no tomllib).

Handles what Herdr configs use: [section], [[array]], key = "string" | 'string' |
number | true/false | [single, line, arrays] | { inline tables }, and # comments.
"""
import os
import re
import shutil

from . import paths

KEY_RE = re.compile(r'^\s*("?)([A-Za-z0-9_.\-]+)\1\s*=\s*(.*)$')


def _strip_comment(line):
    out, q = [], None
    for ch in line:
        if q:
            out.append(ch)
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out).strip()


def _split_top(s, sep=","):
    parts, depth, q, cur = [], 0, None, []
    for ch in s:
        if q:
            cur.append(ch)
            if ch == q:
                q = None
            continue
        if ch in "\"'":
            q = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == sep and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


def value(s):
    s = s.strip()
    if not s:
        return ""
    if s[0] in "\"'" and s[-1] == s[0] and len(s) >= 2:
        return s[1:-1]
    if s[0] == "[" and s.endswith("]"):
        return [value(x) for x in _split_top(s[1:-1])]
    if s[0] == "{" and s.endswith("}"):
        out = {}
        for part in _split_top(s[1:-1]):
            m = KEY_RE.match(part)
            if m:
                out[m.group(2)] = value(m.group(3))
        return out
    if s in ("true", "false"):
        return s == "true"
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return s


def parse(text):
    """-> {"": {top-level keys}, "keys": {...}, "ui.toast": {...}, "keys.command": [{...}, ...]}"""
    data = {"": {}}
    cur = data[""]
    pending = ""
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if pending:
            line = pending + " " + line
            if line.count("[") > line.count("]") or line.count("{") > line.count("}"):
                pending = line
                continue
            pending = ""
        if not line:
            continue
        if line.startswith("[["):
            name = line.strip("[] ")
            data.setdefault(name, [])
            cur = {}
            data[name].append(cur)
            continue
        if line.startswith("["):
            name = line.strip("[] ")
            cur = data.setdefault(name, {})
            continue
        m = KEY_RE.match(line)
        if not m:
            continue
        v = m.group(3)
        if v.count("[") > v.count("]") or v.count("{") > v.count("}"):
            pending = line
            continue
        cur[m.group(2)] = value(v)
    return data


def load(path=None):
    try:
        with open(path or paths.CONFIG) as f:
            return parse(f.read())
    except OSError:
        return {"": {}}


def get(data, section, key, default=None):
    sec = data.get(section, {})
    return sec.get(key, default) if isinstance(sec, dict) else default


def ensure():
    """Create the practice config from the game's base copy if it doesn't exist yet."""
    paths.ensure()
    if not os.path.exists(paths.CONFIG):
        shutil.copy(paths.BASE_CONF, paths.CONFIG)


def keymap(data=None):
    """(prefix, {key after prefix: action}, {direct chord: action}) from the config, over Herdr's defaults."""
    from .keyin import DEFAULT_PREFIX_KEYS, normalise, parse_binding
    data = data or load()
    keys = data.get("keys", {}) if isinstance(data.get("keys"), dict) else {}
    prefix = keys.get("prefix", "ctrl+b") or "ctrl+b"
    prefix_keys = dict(DEFAULT_PREFIX_KEYS)
    direct = {}
    for action, binding in keys.items():
        if action in ("prefix", "indexed") or isinstance(binding, dict):
            continue
        bindings = binding if isinstance(binding, list) else [binding]
        # a custom binding replaces the default for that action
        for k in [k for k, a in prefix_keys.items() if a == action or a.startswith(action + "_")]:
            del prefix_keys[k]
        for b in bindings:
            if not isinstance(b, str) or not b:
                continue
            if action in ("switch_tab", "switch_workspace", "focus_agent") and b.endswith("1..9"):
                kind, base = parse_binding(b[:-4] + "1")
                mods = base[:-1]
                for i in range(1, 10):
                    target = prefix_keys if kind == "prefix" else direct
                    target[normalise(mods + str(i))] = f"{action}_{i}"
                continue
            kind, k = parse_binding(b)
            (prefix_keys if kind == "prefix" else direct)[k] = action
    for cmd in data.get("keys.command", []) or []:
        if isinstance(cmd, dict) and cmd.get("key"):
            kind, k = parse_binding(cmd["key"])
            (prefix_keys if kind == "prefix" else direct)[k] = "custom_command"
    return normalise(prefix), prefix_keys, direct
