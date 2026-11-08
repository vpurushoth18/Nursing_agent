#!/usr/bin/env bash
# Builds dist/NurseAssist-installer.run: installer_header.sh + a tar.gz of the app.
# Secrets (src/.env), downloaded models, generated outputs, the exam recording
# and thesis experiments are never packaged.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/dist/NurseAssist-installer.run"
mkdir -p "$ROOT/dist"

PAYLOAD="$(mktemp)"
trap 'rm -f "$PAYLOAD"' EXIT
tar -czf "$PAYLOAD" -C "$ROOT" \
    --exclude='__pycache__' --exclude='*.pyc' \
    --anchored --no-wildcards-match-slash \
    --exclude='src/.env' --exclude='src/models' \
    --exclude='src/*.docx' --exclude='src/*.json' \
    LICENSE README.md INSTALL.md install.sh nurseassist.png environment src

cat "$ROOT/packaging/installer_header.sh" "$PAYLOAD" > "$OUT"
chmod +x "$OUT"

# refuse to ship a build that contains a token
if tar -tzf "$PAYLOAD" | grep -qE '(^|/)\.env$'; then
    rm -f "$OUT"; echo "ERROR: .env ended up in the payload — build aborted."; exit 1
fi
echo "built $OUT ($(du -h "$OUT" | cut -f1))"
