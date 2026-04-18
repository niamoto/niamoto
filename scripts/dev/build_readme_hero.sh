#!/usr/bin/env bash
# Compose the README hero split-view from two source screenshots:
# - docs/plans/caps/21.site-builder-home-page.png  (desktop app)
# - docs/assets/portal-nc/home.png                 (generated portal)
#
# Output: assets/screenshots/hero-split.png
#
# Requirements: ImageMagick 7 (magick), pngquant (optional, for compression).

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

APP_SHOT="docs/plans/caps/21.site-builder-home-page.png"
PORTAL_SHOT="docs/assets/portal-nc/home.png"
OUT="assets/screenshots/hero-split.png"

mkdir -p "$(dirname "$OUT")"

# Resize both sources to the same height, append horizontally, add a thin
# separator so both panels read as distinct surfaces. Flatten to 8-bit
# sRGB with palette compression to keep the file well under 800 kB.
magick \
  \( "$APP_SHOT"    -resize x900 \) \
  \( -size 4x900 xc:"#1f2937" \) \
  \( "$PORTAL_SHOT" -resize x900 \) \
  +append \
  -depth 8 \
  -strip \
  -define png:compression-level=9 \
  -define png:compression-strategy=2 \
  -colors 256 \
  "$OUT"

# Further compress if pngquant is available.
if command -v pngquant >/dev/null 2>&1; then
  pngquant --force --quality=70-90 --speed 1 --output "$OUT" -- "$OUT"
fi

echo "Wrote $OUT ($(du -h "$OUT" | cut -f1))"
