#!/bin/bash
# Revert the Tauri updater manifest (latest.json) to a previous version.
#
# The updater endpoint is https://github.com/niamoto/niamoto/releases/latest/download/latest.json
# which is served from the `latest.json` asset attached to GitHub's "Latest" release.
# This script downloads the `latest.json` from a target version's release and
# re-uploads it on the current "Latest" release, so installed apps stop proposing
# the newer update.
#
# Usage: scripts/build/revert_latest_json.sh <target-version> [--yes]
# Example: scripts/build/revert_latest_json.sh 0.15.5

set -euo pipefail

RELEASE_REPO="${RELEASE_REPO:-niamoto/niamoto}"
TARGET_VERSION=""
ASSUME_YES=0

usage() {
  cat <<EOF
Usage: $(basename "$0") <target-version> [--yes]

Arguments:
  target-version    Version cible (ex: 0.15.5 ou v0.15.5)
  --yes             Ne pas demander de confirmation

Variables d'environnement:
  RELEASE_REPO      Dépôt GitHub (défaut: niamoto/niamoto)
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --yes|-y) ASSUME_YES=1 ;;
    --help|-h) usage; exit 0 ;;
    -*) echo "Option inconnue: $1" >&2; usage; exit 1 ;;
    *)
      if [ -n "$TARGET_VERSION" ]; then
        echo "Argument en trop: $1" >&2; exit 1
      fi
      TARGET_VERSION="$1"
      ;;
  esac
  shift
done

[ -n "$TARGET_VERSION" ] || { usage; exit 1; }
command -v gh >/dev/null 2>&1 || { echo "GitHub CLI (gh) requis" >&2; exit 1; }

TARGET_TAG="$TARGET_VERSION"
[[ "$TARGET_TAG" == v* ]] || TARGET_TAG="v$TARGET_TAG"

LATEST_TAG="$(gh release view --repo "$RELEASE_REPO" --json tagName --jq .tagName)"
[ -n "$LATEST_TAG" ] || { echo "Impossible de déterminer la release 'Latest'" >&2; exit 1; }

echo "Dépôt      : $RELEASE_REPO"
echo "Latest     : $LATEST_TAG"
echo "Cible      : $TARGET_TAG"

if [ "$LATEST_TAG" = "$TARGET_TAG" ]; then
  echo "La release Latest est déjà $TARGET_TAG — rien à faire." >&2
  exit 0
fi

if [ "$ASSUME_YES" -ne 1 ]; then
  read -r -p "Remplacer latest.json de $LATEST_TAG par celui de $TARGET_TAG ? [y/N] " reply
  case "$reply" in
    y|Y|yes) ;;
    *) echo "Annulé." ; exit 0 ;;
  esac
fi

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/niamoto-revert-XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT

echo "Téléchargement de latest.json depuis $TARGET_TAG..."
gh release download "$TARGET_TAG" \
  --repo "$RELEASE_REPO" \
  --pattern latest.json \
  --dir "$WORK_DIR"

SERVED_VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$WORK_DIR/latest.json")"
echo "Manifest version: $SERVED_VERSION"

echo "Upload vers $LATEST_TAG (--clobber)..."
gh release upload "$LATEST_TAG" "$WORK_DIR/latest.json" \
  --repo "$RELEASE_REPO" \
  --clobber

echo "OK — l'updater servira $SERVED_VERSION."
