#!/bin/sh
# Records docs/demo.gif by playing the first missions with real keystrokes.
# Needs tmux, asciinema 3 and agg:  brew install tmux asciinema agg
# Run from anywhere:  sh docs/record-demo.sh
set -eu
cd "$(dirname "$0")/.."
T="tmux -L hldemo"
HOME_DIR=/tmp/hl-demo          # short: Herdr's socket path must fit in ~104 bytes
CAST="$(mktemp -d)/demo.cast"

$T kill-server 2>/dev/null || true
rm -rf "$HOME_DIR"
# a throwaway $HOME with a plain prompt, so the GIF shows no real user or hostname
mkdir -p "$HOME_DIR/home"
printf 'PS1="\\W \\$ "\n' > "$HOME_DIR/home/.bash_profile"
$T -f /dev/null new-session -d -x 130 -y 32 \
  "env -u TMUX -u HERDR_ENV HOME=$HOME_DIR/home SHELL=/bin/bash BASH_SILENCE_DEPRECATION_WARNING=1 HERDLING_HOME=$HOME_DIR $PWD/herdling play 1.1; sleep 5"
$T set -g status off
$T set -g escape-time 0

asciinema rec --headless --window-size 130x32 --overwrite -c "$T attach" "$CAST" &
REC=$!

key() { sleep "$1"; shift; $T send-keys "$@"; }
key 4   Enter            # past the lesson card
key 2.5 C-b; key 0.3 v   # 1.1 side by side
key 3.5 C-b; key 0.3 %   # 1.2: a tmux habit… the game points to the Herdr key
key 3.5 C-b; key 0.3 -   # …and the right one
key 3.5 C-b; key 0.3 h   # 1.3 hop left
key 2   C-b; key 0.3 l   # and right
sleep 4

$T kill-server
wait "$REC" || true
agg --font-size 16 --theme monokai --idle-time-limit 2 "$CAST" docs/demo.gif
echo "wrote docs/demo.gif"
