"""Talk to the game's sandboxed Herdr server over its socket API.

One JSON request per connection (that's how Herdr's socket works); each call
takes well under a millisecond, so the engine can poll the whole session
snapshot ten times a second.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time

from . import paths


class HerdrError(Exception):
    def __init__(self, code, message):
        super().__init__(f"{code}: {message}")
        self.code = code


def herdr_bin():
    return shutil.which("herdr") or os.path.expanduser("~/.local/bin/herdr")


def version():
    try:
        out = subprocess.run([herdr_bin(), "--version"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    parts = out.split()
    if len(parts) < 2:
        return None
    try:
        return tuple(int(x) for x in parts[1].split(".")[:3])
    except ValueError:
        return (99, 0, 0)


def user_shell():
    return os.environ.get("HERDLING_SHELL") or os.environ.get("SHELL") or "/bin/sh"


def game_env(base=None):
    """Environment for the game's Herdr server, clients, and the CLI inside it."""
    env = dict(base if base is not None else os.environ)
    for k in ("HERDR_ENV", "HERDR_SOCKET_PATH", "HERDR_SESSION", "HERDR_PANE_ID", "HERDR_TAB_ID",
              "HERDR_WORKSPACE_ID", "TMUX", "TMUX_PANE"):
        env.pop(k, None)
    # the pane shell wrapper restores the player's own XDG_CONFIG_HOME (see bin/hl-shell)
    if "HERDLING_ORIG_XDG" not in env:
        env["HERDLING_ORIG_XDG"] = env.get("XDG_CONFIG_HOME", "")
    env["XDG_CONFIG_HOME"] = paths.XDG
    env["HERDR_CONFIG_PATH"] = paths.CONFIG
    env["HERDLING_SHELL"] = user_shell()
    # Herdr starts $SHELL in new panes; the wrapper undoes the sandbox env, then runs yours.
    env["SHELL"] = os.path.join(paths.BIN, "hl-shell")
    env["HERDLING_GAME"] = "1"
    env["HERDLING_HOME"] = paths.HOME
    env["HERDLING_PYTHON"] = sys.executable
    parts = env.get("PATH", "").split(os.pathsep)
    for d in (os.path.dirname(herdr_bin()), paths.BIN):   # `herdling` and `herdr` work in every pane
        if d not in parts:
            parts.insert(0, d)
    env["PATH"] = os.pathsep.join(parts)
    return env


class Herdr:
    def __init__(self, session=None):
        self.session = session
        self.sock = paths.session_socket(session)

    # ------------------------------------------------------------ raw API

    def call(self, method, timeout=5, **params):
        params = {k: v for k, v in params.items() if v is not None}
        s = socket.socket(socket.AF_UNIX)
        s.settimeout(timeout)
        try:
            s.connect(self.sock)
            s.sendall((json.dumps({"id": "hl", "method": method, "params": params}) + "\n").encode())
            buf = b""
            while not buf.endswith(b"\n"):
                d = s.recv(1 << 20)
                if not d:
                    break
                buf += d
        except (OSError, socket.timeout) as e:
            raise HerdrError("socket", str(e))
        finally:
            s.close()
        try:
            msg = json.loads(buf)
        except ValueError:
            raise HerdrError("protocol", buf[:200].decode(errors="replace"))
        if "error" in msg:
            raise HerdrError(msg["error"].get("code", "error"), msg["error"].get("message", ""))
        return msg.get("result", {})

    def try_call(self, method, **params):
        try:
            return self.call(method, **params)
        except HerdrError:
            return None

    def alive(self):
        return self.try_call("ping") is not None

    def snapshot_raw(self):
        r = self.try_call("session.snapshot")
        return r.get("snapshot") if r else None

    # ------------------------------------------------------------ CLI

    def cli(self, *args, timeout=10):
        """Run the real `herdr` CLI against the sandbox (e.g. session management)."""
        argv = [herdr_bin()] + (["--session", self.session] if self.session else []) + list(args)
        try:
            return subprocess.run(argv, env=game_env(), capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(argv, 1, "", "timeout")

    # ------------------------------------------------------------ server lifecycle

    def start_server(self, log=None):
        if self.alive():
            return True
        argv = [herdr_bin()] + (["--session", self.session] if self.session else []) + ["server"]
        out = open(log, "a") if log else subprocess.DEVNULL
        subprocess.Popen(argv, env=game_env(), cwd=os.path.expanduser("~"), stdout=out, stderr=out,
                         stdin=subprocess.DEVNULL, start_new_session=True)
        for _ in range(100):
            if self.alive():
                return True
            time.sleep(0.05)
        return False

    def stop_server(self):
        if self.try_call("server.stop") is None:
            return
        for _ in range(60):
            if not os.path.exists(self.sock) or not self.alive():
                return
            time.sleep(0.05)


def sessions():
    """[{name, running, default}] for every session in the sandbox."""
    r = Herdr().cli("session", "list", "--json")
    try:
        return json.loads(r.stdout).get("sessions", [])
    except ValueError:
        return []


def running_sessions():
    return [s["name"] for s in sessions() if s.get("running")]
