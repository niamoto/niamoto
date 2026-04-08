#!/bin/bash
# Build two local desktop versions and exercise the real Tauri auto-update flow on macOS.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

FROM_VERSION=""
TO_VERSION=""
PORT=""
REF="HEAD"
KEEP_TEMP=0
WORK_ROOT=""

TEMP_ROOT=""
FROM_WORKSPACE=""
TO_WORKSPACE=""
RUN_APP_PATH=""
SERVER_DIR=""
LOG_DIR=""
SERVER_PID=""

usage() {
  cat <<'EOF'
Usage: scripts/dev/test_desktop_update.sh [options]

Builds a source and target macOS desktop app locally, serves a local Tauri updater
endpoint, launches the source app, and lets you validate a real auto-update flow.

Options:
  --from-version VERSION   Source app version. Defaults to src-tauri/tauri.conf.json version.
  --to-version VERSION     Target app version. Defaults to next patch with "-local" suffix.
  --port PORT              Local HTTP port for updater server. Defaults to an ephemeral free port.
  --ref GIT_REF            Git ref to checkout in temp workspaces. Defaults to HEAD.
  --work-root PATH         Reuse a specific temporary root directory instead of mktemp.
  --keep-temp              Keep temp workspaces/logs after completion.
  -h, --help               Show this help message.

Notes:
  - macOS only.
  - Requires cargo, pnpm, python3, git, curl and open.
  - Uses a temporary Tauri signing keypair generated for this harness run.
  - The install click remains manual in the first version of the harness.
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

current_tauri_target() {
  case "$(uname -s):$(uname -m)" in
    Darwin:arm64) echo "aarch64-apple-darwin" ;;
    Darwin:x86_64) echo "x86_64-apple-darwin" ;;
    *)
      echo "Unsupported local target: $(uname -s) $(uname -m)" >&2
      exit 1
      ;;
  esac
}

current_repo_version() {
  python3 - <<'PY' "$REPO_ROOT"
import json
import sys
from pathlib import Path

repo_root = Path(sys.argv[1])
conf = json.loads((repo_root / "src-tauri" / "tauri.conf.json").read_text())
print(conf["version"])
PY
}

default_target_version() {
  python3 - <<'PY' "$1"
import re
import sys

version = sys.argv[1]
match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
if not match:
    raise SystemExit(f"Unsupported version format: {version}")
major, minor, patch = map(int, match.groups())
print(f"{major}.{minor}.{patch + 1}-local")
PY
}

version_gt() {
  python3 - <<'PY' "$1" "$2"
import re
import sys

def parse(version: str):
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$", version)
    if not match:
        raise SystemExit(f"Unsupported version format: {version}")
    major, minor, patch = map(int, match.groups()[:3])
    prerelease = match.group(4)
    prerelease_rank = (0, "") if prerelease is None else (-1, prerelease)
    return (major, minor, patch, prerelease_rank)

left = parse(sys.argv[1])
right = parse(sys.argv[2])
raise SystemExit(0 if right > left else 1)
PY
}

pick_free_port() {
  python3 - <<'PY'
import socket

sock = socket.socket()
sock.bind(("127.0.0.1", 0))
port = sock.getsockname()[1]
sock.close()
print(port)
PY
}

read_app_version() {
  local app_path="$1"
  /usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$app_path/Contents/Info.plist"
}

patch_workspace() {
  local workspace="$1"
  local version="$2"
  local endpoint="$3"
  local pubkey="$4"

  python3 - <<'PY' "$workspace" "$version" "$endpoint" "$pubkey"
import json
import re
import sys
from pathlib import Path

workspace = Path(sys.argv[1])
version = sys.argv[2]
endpoint = sys.argv[3]
pubkey = sys.argv[4]

tauri_conf_path = workspace / "src-tauri" / "tauri.conf.json"
tauri_conf = json.loads(tauri_conf_path.read_text())
tauri_conf["version"] = version
tauri_conf.setdefault("plugins", {}).setdefault("updater", {})["pubkey"] = pubkey
tauri_conf["plugins"]["updater"]["endpoints"] = [endpoint]
tauri_conf["plugins"]["updater"]["dangerousInsecureTransportProtocol"] = endpoint.startswith("http://")
tauri_conf_path.write_text(json.dumps(tauri_conf, indent=2) + "\n")

cargo_toml_path = workspace / "src-tauri" / "Cargo.toml"
cargo_toml = cargo_toml_path.read_text()
cargo_toml, count = re.subn(
    r'(?ms)(^\[package\]\s+.*?^version\s*=\s*")([^"]+)(")',
    rf'\g<1>{version}\3',
    cargo_toml,
    count=1,
)
if count != 1:
    raise SystemExit("Failed to patch src-tauri/Cargo.toml package version")
cargo_toml_path.write_text(cargo_toml)

pyproject_path = workspace / "pyproject.toml"
pyproject = pyproject_path.read_text()
pyproject, count = re.subn(
    r'(?m)^(version\s*=\s*")([^"]+)(")$',
    rf'\g<1>{version}\3',
    pyproject,
    count=1,
)
if count != 1:
    raise SystemExit("Failed to patch pyproject.toml version")
pyproject_path.write_text(pyproject)
PY
}

ensure_frontend_dependencies() {
  local workspace="$1"
  local repo_node_modules="$REPO_ROOT/src/niamoto/gui/ui/node_modules"
  local workspace_node_modules="$workspace/src/niamoto/gui/ui/node_modules"

  if [[ -e "$workspace_node_modules" ]]; then
    return
  fi

  if [[ -d "$repo_node_modules" ]]; then
    ln -s "$repo_node_modules" "$workspace_node_modules"
  else
    pnpm --dir "$workspace/src/niamoto/gui/ui" install --frozen-lockfile
  fi
}

sync_sidecar_resources() {
  local workspace="$1"
  local target="$2"
  local source_root="$REPO_ROOT/src-tauri/resources/sidecar"
  local target_root="$workspace/src-tauri/resources/sidecar"
  local source_bundle="$source_root/$target/niamoto"

  if [[ ! -f "$source_bundle/niamoto" ]]; then
    echo "Local sidecar resources are missing for $target." >&2
    echo "Expected: $source_bundle/niamoto" >&2
    echo "Build or restore the local sidecar bundle before running the update harness." >&2
    exit 1
  fi

  rm -rf "$target_root"
  mkdir -p "$target_root"
  cp -R "$source_root/." "$target_root/"
}

build_workspace() {
  local workspace="$1"
  local label="$2"
  local private_key_path="$3"
  local log_file="$LOG_DIR/${label}-build.log"
  local tauri_target="$4"

  ensure_frontend_dependencies "$workspace"
  sync_sidecar_resources "$workspace" "$tauri_target"

  {
    echo "==> Building frontend for $label"
    pnpm --dir "$workspace/src/niamoto/gui/ui" build
    echo "==> Building Tauri app for $label"
    (
      cd "$workspace/src-tauri"
      TAURI_SIGNING_PRIVATE_KEY="$private_key_path" \
      TAURI_SIGNING_PRIVATE_KEY_PASSWORD="" \
      cargo tauri build --ci --bundles app
    )
  } >"$log_file" 2>&1
}

find_source_app() {
  find "$1/src-tauri/target/release/bundle" -type d -name '*.app' | sort | head -n 1
}

find_target_archive_and_sig() {
  local bundle_root="$1/src-tauri/target/release/bundle"
  local sig_path
  sig_path="$(find "$bundle_root" -type f -name '*.sig' | sort | grep -E '\.app\.tar\.gz\.sig$' | head -n 1 || true)"
  if [[ -z "$sig_path" ]]; then
    sig_path="$(find "$bundle_root" -type f -name '*.sig' | sort | head -n 1 || true)"
  fi
  if [[ -z "$sig_path" ]]; then
    return 1
  fi
  printf '%s\n%s\n' "${sig_path%.sig}" "$sig_path"
}

create_manifest() {
  local version="$1"
  local base_url="$2"
  local archive_name="$3"
  local signature_file="$4"

  python3 - <<'PY' "$version" "$base_url" "$archive_name" "$signature_file" "$SERVER_DIR/latest.json"
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

version = sys.argv[1]
base_url = sys.argv[2].rstrip("/")
archive_name = sys.argv[3]
signature_file = Path(sys.argv[4])
output_path = Path(sys.argv[5])

signature = signature_file.read_text().strip()

manifest = {
    "version": version,
    "notes": "Local updater harness build",
    "pub_date": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "platforms": {
        "darwin-aarch64": {
            "url": f"{base_url}/{archive_name}",
            "signature": signature,
        }
    },
}

output_path.write_text(json.dumps(manifest, indent=2) + "\n")
PY
}

cleanup() {
  local exit_code=$?

  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
  fi

  if [[ "$KEEP_TEMP" -eq 0 && "$exit_code" -eq 0 && -n "$TEMP_ROOT" ]]; then
    if [[ -n "$FROM_WORKSPACE" && -e "$FROM_WORKSPACE/.git" ]]; then
      git -C "$REPO_ROOT" worktree remove --force "$FROM_WORKSPACE" >/dev/null 2>&1 || true
    fi
    if [[ -n "$TO_WORKSPACE" && -e "$TO_WORKSPACE/.git" ]]; then
      git -C "$REPO_ROOT" worktree remove --force "$TO_WORKSPACE" >/dev/null 2>&1 || true
    fi
    rm -rf "$TEMP_ROOT"
  fi

  exit "$exit_code"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from-version)
      FROM_VERSION="$2"
      shift 2
      ;;
    --to-version)
      TO_VERSION="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --ref)
      REF="$2"
      shift 2
      ;;
    --work-root)
      WORK_ROOT="$2"
      shift 2
      ;;
    --keep-temp)
      KEEP_TEMP=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This harness is currently macOS-only." >&2
  exit 1
fi

require_cmd git
require_cmd cargo
require_cmd pnpm
require_cmd python3
require_cmd curl
require_cmd open

cd "$REPO_ROOT"

if ! git rev-parse --verify "$REF" >/dev/null 2>&1; then
  echo "Unknown git ref: $REF" >&2
  exit 1
fi

CURRENT_VERSION="$(current_repo_version)"
FROM_VERSION="${FROM_VERSION:-$CURRENT_VERSION}"
TO_VERSION="${TO_VERSION:-$(default_target_version "$FROM_VERSION")}"
PORT="${PORT:-$(pick_free_port)}"

if ! version_gt "$FROM_VERSION" "$TO_VERSION"; then
  echo "--to-version must be strictly greater than --from-version" >&2
  echo "from=$FROM_VERSION to=$TO_VERSION" >&2
  exit 1
fi

TEMP_ROOT="${WORK_ROOT:-$(mktemp -d "/tmp/niamoto-update-harness-XXXXXX")}"
mkdir -p "$TEMP_ROOT"
LOG_DIR="$TEMP_ROOT/logs"
SERVER_DIR="$TEMP_ROOT/update-server"
FROM_WORKSPACE="$TEMP_ROOT/from-workspace"
TO_WORKSPACE="$TEMP_ROOT/to-workspace"
RUN_APP_PATH="$TEMP_ROOT/Niamoto.app"
mkdir -p "$LOG_DIR" "$SERVER_DIR"

trap cleanup EXIT INT TERM

echo "==> Harness root: $TEMP_ROOT"
echo "==> Source version: $FROM_VERSION"
echo "==> Target version: $TO_VERSION"
echo "==> Updater endpoint: http://127.0.0.1:$PORT/latest.json"

TAURI_TARGET="$(current_tauri_target)"
echo "==> Local Tauri target: $TAURI_TARGET"

echo "==> Creating temporary signing keypair"
KEY_PATH="$TEMP_ROOT/tauri-update.key"
cargo tauri signer generate --ci --force --write-keys "$KEY_PATH" >"$LOG_DIR/keygen.log" 2>&1
PUBKEY_PATH="${KEY_PATH}.pub"
PUBKEY="$(<"$PUBKEY_PATH")"
UPDATER_ENDPOINT="http://127.0.0.1:$PORT/latest.json"

echo "==> Creating isolated workspaces from $REF"
git worktree add --detach "$FROM_WORKSPACE" "$REF" >"$LOG_DIR/from-worktree.log" 2>&1
git worktree add --detach "$TO_WORKSPACE" "$REF" >"$LOG_DIR/to-worktree.log" 2>&1

echo "==> Patching workspaces"
patch_workspace "$FROM_WORKSPACE" "$FROM_VERSION" "$UPDATER_ENDPOINT" "$PUBKEY"
patch_workspace "$TO_WORKSPACE" "$TO_VERSION" "$UPDATER_ENDPOINT" "$PUBKEY"

echo "==> Building source app"
build_workspace "$FROM_WORKSPACE" "from" "$KEY_PATH" "$TAURI_TARGET"

echo "==> Building target app"
build_workspace "$TO_WORKSPACE" "to" "$KEY_PATH" "$TAURI_TARGET"

SOURCE_APP="$(find_source_app "$FROM_WORKSPACE")"
if [[ -z "$SOURCE_APP" ]]; then
  echo "Unable to find source .app bundle. See $LOG_DIR/from-build.log" >&2
  exit 1
fi

TARGET_ARCHIVE=""
TARGET_SIG=""
while IFS= read -r line; do
  if [[ -z "$TARGET_ARCHIVE" ]]; then
    TARGET_ARCHIVE="$line"
  elif [[ -z "$TARGET_SIG" ]]; then
    TARGET_SIG="$line"
  fi
done < <(find_target_archive_and_sig "$TO_WORKSPACE" || true)

if [[ -z "$TARGET_ARCHIVE" || -z "$TARGET_SIG" ]]; then
  echo "Unable to find target updater archive/signature. See $LOG_DIR/to-build.log" >&2
  exit 1
fi

echo "==> Preparing local updater server payload"
cp "$TARGET_ARCHIVE" "$SERVER_DIR/"
cp "$TARGET_SIG" "$SERVER_DIR/"
TARGET_ARCHIVE_NAME="$(basename "$TARGET_ARCHIVE")"
create_manifest "$TO_VERSION" "http://127.0.0.1:$PORT" "$TARGET_ARCHIVE_NAME" "$TARGET_SIG"

echo "==> Preparing runnable source app copy"
rm -rf "$RUN_APP_PATH"
cp -R "$SOURCE_APP" "$RUN_APP_PATH"

SOURCE_APP_VERSION="$(read_app_version "$RUN_APP_PATH")"
echo "==> Source app bundle version: $SOURCE_APP_VERSION"

echo "==> Starting local updater server"
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$SERVER_DIR" >"$LOG_DIR/server.log" 2>&1 &
SERVER_PID=$!

for _ in {1..20}; do
  if curl -fsS "http://127.0.0.1:$PORT/latest.json" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

if ! curl -fsS "http://127.0.0.1:$PORT/latest.json" >/dev/null 2>&1; then
  echo "Local updater server did not start. See $LOG_DIR/server.log" >&2
  exit 1
fi

echo
echo "Harness is ready."
echo "- Local manifest: http://127.0.0.1:$PORT/latest.json"
echo "- Source app:     $RUN_APP_PATH"
echo "- Logs:           $LOG_DIR"
echo
echo "The app will open now."
echo "1. Wait for the update prompt."
echo "2. Click 'Installer'."
echo "3. Wait for the app to relaunch."
echo "4. Return here and press Enter."
echo

open -n "$RUN_APP_PATH"
read -r -p "Press Enter after the app has completed the update flow..."

FINAL_VERSION="$(read_app_version "$RUN_APP_PATH")"

echo
echo "==> Update harness summary"
echo "Source version expected: $FROM_VERSION"
echo "Target version expected: $TO_VERSION"
echo "Final bundle version:    $FINAL_VERSION"
echo "Updater manifest:        $SERVER_DIR/latest.json"
echo "Artifact served:         $SERVER_DIR/$TARGET_ARCHIVE_NAME"
echo "Logs directory:          $LOG_DIR"

if [[ "$FINAL_VERSION" == "$TO_VERSION" ]]; then
  echo
  echo "PASS: app bundle version matches the target version."
else
  echo
  echo "FAIL: app bundle version did not reach the target version." >&2
  echo "Inspect:" >&2
  echo "- $LOG_DIR/from-build.log" >&2
  echo "- $LOG_DIR/to-build.log" >&2
  echo "- $LOG_DIR/server.log" >&2
  exit 1
fi
