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
SIDECAR_DIR=""
SIGNING_IDENTITY="${APPLE_SIGNING_IDENTITY:-}"
KEYCHAIN_PATH="${NIAMOTO_SIGNING_KEYCHAIN:-}"
RUN_BUILD=0
RUN_NOTARIZE=0
SKIP_SPCTL=0
AD_HOC_SIGNING=0

usage() {
  cat <<'EOF'
Usage: scripts/dev/verify_macos_distribution.sh [options]

Prépare, signe et vérifie localement le bundle macOS desktop Niamoto.

Options:
  --build                 Rebuild l'application desktop avant la vérification
  --app PATH              Chemin vers Niamoto.app
  --sidecar-dir PATH      Chemin vers le dossier sidecar à signer
  --target TRIPLE         Triple cible Tauri/PyInstaller (défaut: détection auto)
  --identity STRING       Identité Developer ID Application à utiliser
  --ad-hoc                Utilise une signature ad hoc locale au lieu d'un certificat Apple
  --keychain PATH         Trousseau à utiliser pour codesign
  --notarize              Soumet aussi l'application à Apple avec notarytool
  --skip-spctl            N'exécute pas la vérification Gatekeeper locale
  --help                  Affiche cette aide

Variables d'environnement utiles:
  APPLE_SIGNING_IDENTITY  Identité codesign par défaut
  NIAMOTO_SIGNING_KEYCHAIN Trousseau codesign facultatif
  APPLE_ID                Requis avec --notarize
  APPLE_PASSWORD          Requis avec --notarize
  APPLE_TEAM_ID           Requis avec --notarize
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

find_versioned_python_path() {
  local python_path
  python_path="$(find "$1/_internal/Python.framework/Versions" -type f -name Python | head -n 1)"
  if [ -z "$python_path" ]; then
    fail "Impossible de trouver le binaire Python versionné dans $1/_internal/Python.framework"
  fi
  printf '%s\n' "$python_path"
}

active_python_framework_version() {
  local framework_path="$1/_internal/Python.framework"
  local version
  version="$(readlink "$framework_path/Versions/Current" || true)"
  if [ -z "$version" ]; then
    version="$(basename "$(dirname "$(find_versioned_python_path "$1")")")"
  fi
  if [ -z "$version" ]; then
    fail "Impossible de déterminer la version active de Python.framework"
  fi
  printf '%s\n' "$version"
}

rebuild_python_framework_layout() {
  local sidecar_dir="$1"
  local framework_path="$sidecar_dir/_internal/Python.framework"
  local framework_version
  framework_version="$(active_python_framework_version "$sidecar_dir")"

  log "Réparation du layout Python.framework dans $sidecar_dir"

  rm -f "$framework_path/Versions/Current"
  ln -s "$framework_version" "$framework_path/Versions/Current"

  rm -f "$framework_path/Python"
  ln -s "Versions/Current/Python" "$framework_path/Python"

  if [ -d "$framework_path/Versions/$framework_version/Resources" ]; then
    rm -rf "$framework_path/Resources"
    ln -s "Versions/Current/Resources" "$framework_path/Resources"
  fi

  rm -f "$sidecar_dir/_internal/Python"
  ln -s "Python.framework/Versions/$framework_version/Python" "$sidecar_dir/_internal/Python"

  local versioned_python
  versioned_python="$(find_versioned_python_path "$sidecar_dir")"
  ls -l \
    "$sidecar_dir/_internal/Python" \
    "$framework_path/Python" \
    "$framework_path/Versions/Current" \
    "$versioned_python"
}

sign_macho_file() {
  local path="$1"
  local file_description
  file_description="$(file -b "$path")"
  if [[ "$file_description" != *"Mach-O"* ]]; then
    return 0
  fi

  local -a args
  set_base_codesign_args
  args=("${CODESIGN_ARGS[@]}")

  if [[ "$file_description" == *"executable"* ]]; then
    args+=(--options runtime)
  fi

  codesign "${args[@]}" "$path"
}

sign_sidecar() {
  local sidecar_dir="$1"
  log "Signature du sidecar dans $sidecar_dir"

  while IFS= read -r -d '' path; do
    case "$path" in
      */_internal/Python.framework/Python)
        echo "Skipping top-level framework Python entrypoint in favor of bundle signing: $path"
        continue
        ;;
      */_internal/Python.framework/Versions/*/Python)
        echo "Skipping framework-version Python binary in favor of bundle signing: $path"
        continue
        ;;
    esac
    sign_macho_file "$path"
  done < <(find "$sidecar_dir" -type f -print0)

  while IFS= read -r -d '' framework_path; do
    local -a args
    set_base_codesign_args
    args=("${CODESIGN_ARGS[@]}")

    case "$framework_path" in
      */_internal/Python.framework)
        args+=(--bundle-version "$(active_python_framework_version "$sidecar_dir")")
        ;;
    esac

    codesign "${args[@]}" "$framework_path"
  done < <(find "$sidecar_dir" -type d -name '*.framework' -print0)
}

verify_sidecar() {
  local sidecar_dir="$1"
  log "Vérification du sidecar"

  codesign --verify --verbose=4 "$sidecar_dir/_internal/Python"
  codesign -dvvv "$sidecar_dir/_internal/Python" 2>&1 |
    grep -E '^(Executable|Identifier|Format|Authority|TeamIdentifier|Timestamp)=' || true

  codesign --verify --deep --strict --verbose=2 \
    --bundle-version "$(active_python_framework_version "$sidecar_dir")" \
    "$sidecar_dir/_internal/Python.framework"
}

app_executable_path() {
  local app_path="$1"
  local executable
  executable="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$app_path/Contents/Info.plist")"
  if [ -z "$executable" ]; then
    fail "Impossible de lire CFBundleExecutable depuis $app_path/Contents/Info.plist"
  fi
  printf '%s\n' "$app_path/Contents/MacOS/$executable"
}

restore_executable_permissions() {
  local app_path="$1"
  local sidecar_dir="$2"
  local path
  local file_description

  log "Restauration des permissions exécutables"

  while IFS= read -r -d '' path; do
    file_description="$(file -b "$path")"
    if [[ "$file_description" == *"Mach-O"* ]]; then
      chmod 755 "$path"
    fi
  done < <(find "$app_path/Contents/MacOS" "$sidecar_dir" -type f -print0)
}

assert_executable_file() {
  local path="$1"
  [ -f "$path" ] || fail "Fichier exécutable introuvable: $path"
  [ -x "$path" ] || fail "Permission exécutable absente: $path"
}

verify_executable_permissions() {
  local app_path="$1"
  local sidecar_dir="$2"
  local app_binary
  local sidecar_binary
  local python_binary

  app_binary="$(app_executable_path "$app_path")"
  sidecar_binary="$sidecar_dir/niamoto"
  python_binary="$(find_versioned_python_path "$sidecar_dir")"

  assert_executable_file "$app_binary"
  assert_executable_file "$sidecar_binary"
  assert_executable_file "$python_binary"

  ls -l "$app_binary" "$sidecar_binary" "$python_binary"
}

resign_app_bundle() {
  local app_path="$1"
  local executable_path
  executable_path="$(app_executable_path "$app_path")"

  log "Ressignature du binaire principal"
  local -a args
  set_base_codesign_args
  args=("${CODESIGN_ARGS[@]}")
  args+=(--options runtime)

  codesign "${args[@]}" "$executable_path"

  log "Ressignature du bundle .app"
  local -a bundle_args
  set_base_codesign_args
  bundle_args=("${CODESIGN_ARGS[@]}")
  bundle_args+=(--options runtime)
  codesign "${bundle_args[@]}" "$app_path"
}

verify_app_bundle() {
  local app_path="$1"
  log "Vérification du bundle $app_path"
  codesign --verify --deep --strict --verbose=2 "$app_path"
  codesign -dvvv "$app_path" 2>&1 |
    grep -E '^(Executable|Identifier|Format|Authority|TeamIdentifier|Timestamp)=' || true

  if [ "$SKIP_SPCTL" -eq 0 ]; then
    spctl -a -vv "$app_path"
  else
    warn "Vérification Gatekeeper ignorée (--skip-spctl)"
  fi
}

notarize_app_bundle() {
  local app_path="$1"
  [ -n "${APPLE_ID:-}" ] || fail "APPLE_ID requis avec --notarize"
  [ -n "${APPLE_PASSWORD:-}" ] || fail "APPLE_PASSWORD requis avec --notarize"
  [ -n "${APPLE_TEAM_ID:-}" ] || fail "APPLE_TEAM_ID requis avec --notarize"

  local zip_path
  zip_path="$(mktemp -t niamoto-notary-XXXXXX.zip)"

  log "Création de l'archive pour notarytool"
  ditto -c -k --keepParent --sequesterRsrc "$app_path" "$zip_path"

  log "Soumission à Apple notarization"
  xcrun notarytool submit "$zip_path" \
    --apple-id "$APPLE_ID" \
    --password "$APPLE_PASSWORD" \
    --team-id "$APPLE_TEAM_ID" \
    --wait

  log "Stapling du ticket de notarisation"
  xcrun stapler staple "$app_path"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --build)
      RUN_BUILD=1
      ;;
    --app)
      APP_PATH="$2"
      shift
      ;;
    --sidecar-dir)
      SIDECAR_DIR="$2"
      shift
      ;;
    --target)
      TARGET_TRIPLE="$2"
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
    --notarize)
      RUN_NOTARIZE=1
      ;;
    --skip-spctl)
      SKIP_SPCTL=1
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

if [ "$AD_HOC_SIGNING" -eq 1 ] && [ "$RUN_NOTARIZE" -eq 1 ]; then
  fail "--ad-hoc et --notarize sont incompatibles"
fi

TARGET_TRIPLE="${TARGET_TRIPLE:-$(detect_target_triple)}"
APP_PATH="${APP_PATH:-$ROOT_DIR/src-tauri/target/release/bundle/macos/Niamoto.app}"
SIDECAR_DIR="${SIDECAR_DIR:-$APP_PATH/Contents/Resources/sidecar/$TARGET_TRIPLE/niamoto}"

SIGNING_IDENTITY="$(resolve_signing_identity)"
if [ "$SIGNING_IDENTITY" = "-" ]; then
  success "Signature utilisée : ad hoc locale"
else
  success "Identité utilisée : $SIGNING_IDENTITY"
fi

if [ "$RUN_BUILD" -eq 1 ]; then
  log "Build desktop local"
  bash "$ROOT_DIR/build_scripts/build_desktop.sh"
fi

[ -d "$APP_PATH" ] || fail "Bundle introuvable: $APP_PATH"
[ -d "$SIDECAR_DIR" ] || fail "Sidecar introuvable: $SIDECAR_DIR"

rebuild_python_framework_layout "$SIDECAR_DIR"
restore_executable_permissions "$APP_PATH" "$SIDECAR_DIR"
verify_executable_permissions "$APP_PATH" "$SIDECAR_DIR"
sign_sidecar "$SIDECAR_DIR"
verify_sidecar "$SIDECAR_DIR"
resign_app_bundle "$APP_PATH"
verify_app_bundle "$APP_PATH"

if [ "$RUN_NOTARIZE" -eq 1 ]; then
  notarize_app_bundle "$APP_PATH"
fi

success "Vérification locale macOS terminée"
