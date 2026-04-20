#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TARGET_TRIPLE=""
APP_PATH=""
RELEASE_TAG=""
RELEASE_REPO="niamoto/niamoto"
OUTPUT_DIR=""
SIGNING_IDENTITY="${APPLE_SIGNING_IDENTITY:-}"
KEYCHAIN_PATH="${NIAMOTO_SIGNING_KEYCHAIN:-}"
SKIP_NOTARIZE=0
SKIP_UPLOAD=0
AD_HOC_SIGNING=0
TAURI_CLI_NPM_VERSION="${NIAMOTO_TAURI_CLI_VERSION:-2.9.2}"

APP_ARCHIVE_PATH=""
APP_SIG_PATH=""
DMG_PATH=""
LATEST_JSON_PATH=""
ARCH_SUFFIX=""
PLATFORM_KEY=""
PLATFORM_APP_KEY=""
VERSION=""
WORK_DIR=""
UPDATER_PRIVATE_KEY_FILE=""

usage() {
  cat <<'EOF'
Usage: scripts/build/finalize_macos_release.sh [options]

Répare et republie les artefacts macOS finaux à partir du bundle .app généré.

Options:
  --app PATH              Chemin vers Niamoto.app
  --target TRIPLE         Triple cible Tauri/PyInstaller
  --release-tag TAG       Tag GitHub Release (ex: v0.15.4)
  --release-repo REPO     Dépôt GitHub owner/name (défaut: niamoto/niamoto)
  --output-dir PATH       Dossier de sortie des artefacts refabriqués
  --identity STRING       Identité Developer ID Application à utiliser
  --ad-hoc                Utilise une signature ad hoc locale
  --keychain PATH         Trousseau à utiliser pour codesign
  --skip-notarize         N'exécute pas la notarisation Apple
  --skip-upload           N'upload pas les artefacts vers GitHub Release
  --help                  Affiche cette aide

Variables d'environnement utiles:
  APPLE_SIGNING_IDENTITY            Identité codesign par défaut
  NIAMOTO_SIGNING_KEYCHAIN          Trousseau codesign facultatif
  APPLE_ID                          Requis sauf avec --skip-notarize
  APPLE_PASSWORD                    Requis sauf avec --skip-notarize
  APPLE_TEAM_ID                     Requis sauf avec --skip-notarize
  TAURI_SIGNING_PRIVATE_KEY         Clé privée minisign updater
  TAURI_SIGNING_PRIVATE_KEY_PATH    Chemin vers la clé privée minisign updater
  TAURI_SIGNING_PRIVATE_KEY_PASSWORD Mot de passe minisign updater (mettre une chaîne vide si la clé n'en a pas)
EOF
}

log() {
  printf "%b%s%b\n" "$BLUE" "$1" "$NC"
}

warn() {
  printf "%b%s%b\n" "$YELLOW" "$1" "$NC"
}

fail() {
  printf "%b%s%b\n" "$RED" "$1" "$NC" >&2
  exit 1
}

success() {
  printf "%b%s%b\n" "$GREEN" "$1" "$NC"
}

detect_target_triple() {
  local arch
  arch="$(uname -m)"
  case "$arch" in
    arm64)
      printf '%s\n' "aarch64-apple-darwin"
      ;;
    x86_64)
      printf '%s\n' "x86_64-apple-darwin"
      ;;
    *)
      fail "Architecture macOS non supportée: $arch"
      ;;
  esac
}

resolve_signing_identity() {
  if [ "$AD_HOC_SIGNING" -eq 1 ]; then
    printf '%s\n' "-"
    return 0
  fi

  if [ -n "$SIGNING_IDENTITY" ]; then
    printf '%s\n' "$SIGNING_IDENTITY"
    return 0
  fi

  local detected
  detected="$(
    security find-identity -v -p codesigning 2>/dev/null |
      sed -n 's/.*"\(Developer ID Application:.*\)"/\1/p' |
      head -n 1
  )"

  if [ -z "$detected" ]; then
    fail "Aucune identité 'Developer ID Application' trouvée dans le trousseau local"
  fi

  printf '%s\n' "$detected"
}

resolve_arch_metadata() {
  case "$1" in
    aarch64-apple-darwin)
      ARCH_SUFFIX="aarch64"
      PLATFORM_KEY="darwin-aarch64"
      PLATFORM_APP_KEY="darwin-aarch64-app"
      ;;
    x86_64-apple-darwin)
      ARCH_SUFFIX="x64"
      PLATFORM_KEY="darwin-x86_64"
      PLATFORM_APP_KEY="darwin-x86_64-app"
      ;;
    *)
      fail "Triple macOS non supporté pour la release: $1"
      ;;
  esac
}

read_app_version() {
  /usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$1/Contents/Info.plist"
}

CODESIGN_ARGS=()

set_base_codesign_args() {
  CODESIGN_ARGS=(--force --sign "$SIGNING_IDENTITY")
  if [ -n "$KEYCHAIN_PATH" ]; then
    CODESIGN_ARGS+=(--keychain "$KEYCHAIN_PATH")
  fi
  if [ "$SIGNING_IDENTITY" != "-" ]; then
    CODESIGN_ARGS+=(--timestamp)
  fi
}

ensure_updater_signer() {
  if cargo tauri signer --help >/dev/null 2>&1; then
    printf '%s\n' "cargo"
    return 0
  fi

  if command -v pnpm >/dev/null 2>&1; then
    printf '%s\n' "pnpm"
    return 0
  fi

  fail "Aucun signataire updater Tauri disponible (cargo tauri signer ou pnpm)"
}

resolve_updater_private_key_path() {
  if [ -n "${TAURI_SIGNING_PRIVATE_KEY_PATH:-}" ]; then
    printf '%s\n' "$TAURI_SIGNING_PRIVATE_KEY_PATH"
    return 0
  fi

  if [ -z "${TAURI_SIGNING_PRIVATE_KEY:-}" ]; then
    fail "TAURI_SIGNING_PRIVATE_KEY ou TAURI_SIGNING_PRIVATE_KEY_PATH requis pour signer l'archive updater"
  fi

  if [ -z "$WORK_DIR" ]; then
    fail "WORK_DIR non initialisé pour matérialiser la clé updater"
  fi

  UPDATER_PRIVATE_KEY_FILE="$WORK_DIR/tauri-updater.key"
  printf '%s' "$TAURI_SIGNING_PRIVATE_KEY" > "$UPDATER_PRIVATE_KEY_FILE"
  chmod 600 "$UPDATER_PRIVATE_KEY_FILE"
  printf '%s\n' "$UPDATER_PRIVATE_KEY_FILE"
}

sign_updater_archive() {
  local archive_path="$1"
  local signer_backend
  local private_key_path
  local -a password_args
  signer_backend="$(ensure_updater_signer)"
  private_key_path="$(resolve_updater_private_key_path)"
  password_args=()

  if [ -n "${TAURI_SIGNING_PRIVATE_KEY_PASSWORD:-}" ]; then
    password_args=(--password "$TAURI_SIGNING_PRIVATE_KEY_PASSWORD")
  fi

  log "Signature updater de $archive_path"

  case "$signer_backend" in
    cargo)
      cargo tauri signer sign "$archive_path" --private-key-path "$private_key_path" "${password_args[@]}"
      ;;
    pnpm)
      pnpm dlx "@tauri-apps/cli@${TAURI_CLI_NPM_VERSION}" signer sign "$archive_path" --private-key-path "$private_key_path" "${password_args[@]}"
      ;;
  esac
}

run_distribution_verifier() {
  local -a args
  args=(
    --app "$APP_PATH"
    --target "$TARGET_TRIPLE"
    --identity "$SIGNING_IDENTITY"
    --keychain "$KEYCHAIN_PATH"
    --skip-spctl
  )

  if [ "$AD_HOC_SIGNING" -eq 1 ]; then
    args=(--app "$APP_PATH" --target "$TARGET_TRIPLE" --ad-hoc --skip-spctl)
  fi

  if [ "$SKIP_NOTARIZE" -eq 0 ]; then
    args+=(--notarize)
  fi

  log "Finalisation du bundle .app"
  bash "$ROOT_DIR/scripts/dev/verify_macos_distribution.sh" "${args[@]}"
}

create_updater_archive() {
  APP_ARCHIVE_PATH="$OUTPUT_DIR/Niamoto_${ARCH_SUFFIX}.app.tar.gz"
  APP_SIG_PATH="${APP_ARCHIVE_PATH}.sig"

  rm -f "$APP_ARCHIVE_PATH" "$APP_SIG_PATH"

  log "Création de l'archive updater $(basename "$APP_ARCHIVE_PATH")"
  tar -C "$(dirname "$APP_PATH")" -czf "$APP_ARCHIVE_PATH" "$(basename "$APP_PATH")"
  sign_updater_archive "$APP_ARCHIVE_PATH"
}

create_release_dmg() {
  DMG_PATH="$OUTPUT_DIR/Niamoto_${VERSION}_${ARCH_SUFFIX}.dmg"
  rm -f "$DMG_PATH"

  local staging_dir
  staging_dir="$(mktemp -d "${TMPDIR:-/tmp}/niamoto-dmg-stage-XXXXXX")"
  cp -R "$APP_PATH" "$staging_dir/"

  log "Création du DMG $(basename "$DMG_PATH")"
  hdiutil create \
    -volname "Niamoto" \
    -srcfolder "$staging_dir" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

  rm -rf "$staging_dir"

  local -a dmg_codesign_args
  set_base_codesign_args
  dmg_codesign_args=("${CODESIGN_ARGS[@]}")
  codesign "${dmg_codesign_args[@]}" "$DMG_PATH"
  codesign --verify --verbose=2 "$DMG_PATH"

  if [ "$SKIP_NOTARIZE" -eq 0 ]; then
    [ -n "${APPLE_ID:-}" ] || fail "APPLE_ID requis pour notariser le DMG"
    [ -n "${APPLE_PASSWORD:-}" ] || fail "APPLE_PASSWORD requis pour notariser le DMG"
    [ -n "${APPLE_TEAM_ID:-}" ] || fail "APPLE_TEAM_ID requis pour notariser le DMG"

    log "Soumission du DMG à Apple notarization"
    xcrun notarytool submit "$DMG_PATH" \
      --apple-id "$APPLE_ID" \
      --password "$APPLE_PASSWORD" \
      --team-id "$APPLE_TEAM_ID" \
      --wait

    log "Stapling du ticket de notarisation du DMG"
    xcrun stapler staple "$DMG_PATH"
  fi
}

create_or_patch_latest_json() {
  [ -n "$RELEASE_TAG" ] || fail "--release-tag requis pour générer latest.json"

  local existing_dir
  existing_dir="$(mktemp -d "${TMPDIR:-/tmp}/niamoto-latest-json-XXXXXX")"
  if ! gh release download "$RELEASE_TAG" \
    --repo "$RELEASE_REPO" \
    --pattern latest.json \
    --dir "$existing_dir" >/dev/null 2>&1; then
    warn "latest.json absent de la release courante, création d'un manifeste initial"
  fi

  LATEST_JSON_PATH="$OUTPUT_DIR/latest.json"

  python3 - <<'PY' \
    "${existing_dir}/latest.json" \
    "$LATEST_JSON_PATH" \
    "$VERSION" \
    "$RELEASE_REPO" \
    "$RELEASE_TAG" \
    "$(basename "$APP_ARCHIVE_PATH")" \
    "$APP_SIG_PATH" \
    "$PLATFORM_KEY" \
    "$PLATFORM_APP_KEY"
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

source_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
version = sys.argv[3]
release_repo = sys.argv[4]
release_tag = sys.argv[5]
archive_name = sys.argv[6]
signature_path = Path(sys.argv[7])
platform_key = sys.argv[8]
platform_app_key = sys.argv[9]

if source_path.exists():
    payload = json.loads(source_path.read_text())
else:
    payload = {}

platforms = payload.setdefault("platforms", {})
signature = signature_path.read_text().strip()
url = f"https://github.com/{release_repo}/releases/download/{release_tag}/{archive_name}"

for key in (platform_key, platform_app_key):
    platforms[key] = {"signature": signature, "url": url}

payload["version"] = version
payload.setdefault("notes", "")
payload["pub_date"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

output_path.write_text(json.dumps(payload, indent=2) + "\n")
PY
}

upload_release_assets() {
  [ -n "$RELEASE_TAG" ] || fail "--release-tag requis pour uploader les artefacts"
  command -v gh >/dev/null 2>&1 || fail "GitHub CLI (gh) requis pour uploader les artefacts"

  log "Upload des artefacts macOS corrigés vers ${RELEASE_REPO}@${RELEASE_TAG}"
  gh release upload "$RELEASE_TAG" \
    "$APP_ARCHIVE_PATH" \
    "$APP_SIG_PATH" \
    "$DMG_PATH" \
    "$LATEST_JSON_PATH" \
    --repo "$RELEASE_REPO" \
    --clobber
}

cleanup() {
  if [ -n "$WORK_DIR" ] && [ -d "$WORK_DIR" ] && [ "${OUTPUT_DIR%/}" != "${WORK_DIR%/}" ]; then
    rm -rf "$WORK_DIR"
  fi
}

trap cleanup EXIT

while [ $# -gt 0 ]; do
  case "$1" in
    --app)
      APP_PATH="$2"
      shift
      ;;
    --target)
      TARGET_TRIPLE="$2"
      shift
      ;;
    --release-tag)
      RELEASE_TAG="$2"
      shift
      ;;
    --release-repo)
      RELEASE_REPO="$2"
      shift
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift
      ;;
    --identity)
      SIGNING_IDENTITY="$2"
      shift
      ;;
    --ad-hoc)
      AD_HOC_SIGNING=1
      ;;
    --keychain)
      KEYCHAIN_PATH="$2"
      shift
      ;;
    --skip-notarize)
      SKIP_NOTARIZE=1
      ;;
    --skip-upload)
      SKIP_UPLOAD=1
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      fail "Option inconnue: $1"
      ;;
  esac
  shift
done

if [[ "$OSTYPE" != darwin* ]]; then
  fail "Ce script ne fonctionne que sur macOS"
fi

if [ "$AD_HOC_SIGNING" -eq 1 ] && [ "$SKIP_NOTARIZE" -eq 0 ]; then
  fail "--ad-hoc et la notarisation Apple sont incompatibles"
fi

TARGET_TRIPLE="${TARGET_TRIPLE:-$(detect_target_triple)}"
APP_PATH="${APP_PATH:-$ROOT_DIR/src-tauri/target/release/bundle/macos/Niamoto.app}"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/niamoto-macos-release-XXXXXX")"
OUTPUT_DIR="${OUTPUT_DIR:-$WORK_DIR}"

[ -d "$APP_PATH" ] || fail "Bundle introuvable: $APP_PATH"
mkdir -p "$OUTPUT_DIR"

SIGNING_IDENTITY="$(resolve_signing_identity)"
if [ "$SIGNING_IDENTITY" = "-" ]; then
  success "Signature utilisée : ad hoc locale"
else
  success "Identité utilisée : $SIGNING_IDENTITY"
fi

VERSION="$(read_app_version "$APP_PATH")"
resolve_arch_metadata "$TARGET_TRIPLE"

run_distribution_verifier
create_updater_archive
create_release_dmg

if [ "$SKIP_UPLOAD" -eq 0 ]; then
  create_or_patch_latest_json
  upload_release_assets
else
  success "Artefacts macOS finalisés localement dans $OUTPUT_DIR"
fi
