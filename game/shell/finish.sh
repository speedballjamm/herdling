# Runs last when herdling starts your shell after a detach (see game/outside.py):
# after your own startup files, put the game's `herdr` wrapper first on PATH.
if [ -n "${HERDLING_ORIG_ENV:-}" ] && [ -f "$HERDLING_ORIG_ENV" ]; then . "$HERDLING_ORIG_ENV"; fi
PATH="$HERDLING_PATH_PREFIX:$PATH"
export PATH
: > "$HERDLING_READY"
