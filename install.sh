#!/bin/sh
# Install herdling: curl -fsSL https://raw.githubusercontent.com/speedballjamm/herdling/main/install.sh | sh
#
# Puts the game in ~/.local/share/herdling and a `herdling` command in ~/.local/bin.
# Override with HERDLING_DIR / HERDLING_BIN. Re-run to update.
set -eu

REPO="speedballjamm/herdling"
DIR="${HERDLING_DIR:-$HOME/.local/share/herdling}"
BIN="${HERDLING_BIN:-$HOME/.local/bin}"

say() { printf '%s\n' "$*"; }
die() { say "herdling: $*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "needs python3 (3.9 or newer)"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' || die "needs Python 3.9 or newer"
command -v curl >/dev/null 2>&1 || die "needs curl"
command -v tar >/dev/null 2>&1 || die "needs tar"

TAG="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
  | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -n 1)"
[ -n "$TAG" ] || die "couldn't find the latest release"

say "Installing herdling ${TAG}..."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL "https://github.com/$REPO/archive/refs/tags/$TAG.tar.gz" | tar -xz -C "$TMP"
rm -rf "$DIR"
mkdir -p "$(dirname "$DIR")" "$BIN"
mv "$TMP"/herdling-* "$DIR"
ln -sf "$DIR/herdling" "$BIN/herdling"

say "Installed: $BIN/herdling"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) say "Add $BIN to your PATH, e.g.:  echo 'export PATH=\"$BIN:\$PATH\"' >> ~/.profile" ;;
esac
command -v herdr >/dev/null 2>&1 || say "You'll also need Herdr 0.9+: curl -fsSL https://herdr.dev/install.sh | sh"
say "Then run:  herdling"
