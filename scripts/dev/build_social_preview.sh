#!/usr/bin/env bash
# Build a 1280x640 social preview for GitHub from the hero split asset.
#
# Output: assets/social-preview-1280x640.png
#
# Tip: upload manually in GitHub Settings -> Social preview.
# This script produces a reasonable default; iterate in Figma/Sketch if
# you need more refined typography.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

HERO="assets/screenshots/hero-split.png"
LOGO="assets/niamoto_logo.png"
OUT="assets/social-preview-1280x640.png"

if [ ! -f "$HERO" ]; then
  echo "Missing $HERO. Run scripts/dev/build_readme_hero.sh first." >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT")"

# Start from a dark card, place the hero centered, overlay the logo in
# the top-left corner.
magick \
  -size 1280x640 xc:"#0f172a" \
  \( "$HERO" -resize 1280x -gravity center -extent 1280x580 +repage \) \
  -gravity south -compose Over -composite \
  \( "$LOGO" -resize 120x120 \) \
  -gravity northwest -geometry +32+32 -compose Over -composite \
  -depth 8 \
  -strip \
  -colors 256 \
  "$OUT"

echo "Wrote $OUT ($(du -h "$OUT" | cut -f1))"
