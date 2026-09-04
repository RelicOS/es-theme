#!/bin/sh
# Fetch the IBM Plex TrueType files the theme references (SIL OFL 1.1).
# Source: https://github.com/IBM/plex (release v6.4.0, TrueType.zip, ~34 MB).
# Only the six weights the theme uses are kept, in art/fonts/.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
DEST="$ROOT/art/fonts"
URL="https://github.com/IBM/plex/releases/download/v6.4.0/TrueType.zip"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "downloading $URL"
curl -fL -o "$TMP/plex.zip" "$URL"
unzip -q "$TMP/plex.zip" -d "$TMP/plex"

mkdir -p "$DEST"
for f in IBMPlexSans-Regular IBMPlexSans-Medium IBMPlexSans-SemiBold IBMPlexSans-Bold \
         IBMPlexMono-Regular IBMPlexMono-Medium; do
  src=$(find "$TMP/plex" -name "$f.ttf" | head -n 1)
  [ -n "$src" ] || { echo "missing $f.ttf in archive" >&2; exit 1; }
  cp "$src" "$DEST/$f.ttf"
  echo "  $f.ttf"
done
find "$TMP/plex" -iname "OFL.txt" | head -n 1 | xargs -r -I{} cp {} "$DEST/OFL.txt"
echo "fonts in $DEST"
