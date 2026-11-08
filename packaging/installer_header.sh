#!/usr/bin/env bash
###############################################################################
# NurseAssist installer for Linux (self-extracting)
#
#   Usage:  bash NurseAssist-installer.run [--dir DIR] [--extract-only]
#
# Installs NurseAssist into ~/NurseAssist (or --dir), installs Miniconda if
# needed, asks the user for THEIR OWN Hugging Face token, then runs install.sh
# to build the environment, download the models and add the app-menu launcher.
###############################################################################
set -euo pipefail

INSTALL_DIR="$HOME/NurseAssist"
EXTRACT_ONLY=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir) INSTALL_DIR="$2"; shift 2 ;;
        --extract-only) EXTRACT_ONLY=1; shift ;;
        -h|--help) sed -n 3,9p "$0"; exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done
INSTALL_DIR="$(mkdir -p "$INSTALL_DIR" && cd "$INSTALL_DIR" && pwd)"

# prompts read from the terminal so the installer also works when piped
ask() { local reply; read -r -p "$1" reply </dev/tty; printf '%s' "$reply"; }

echo "==================================================================="
echo " NurseAssist installer"
echo "   install location: $INSTALL_DIR"
echo "==================================================================="

# ---------------------------------------------------------------- extract app
PAYLOAD_LINE=$(awk '/^__PAYLOAD_BELOW__$/ {print NR + 1; exit 0}' "$0")
echo "==> extracting application files..."
tail -n +"$PAYLOAD_LINE" "$0" | tar -xz -C "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/install.sh"
if (( EXTRACT_ONLY )); then
    echo "==> extracted to $INSTALL_DIR (--extract-only, nothing installed)"
    exit 0
fi

# ---------------------------------------------------------------- platform
[[ "$(uname -s)" == "Linux" && "$(uname -m)" == "x86_64" ]] || {
    echo "ERROR: NurseAssist requires 64-bit Linux (x86_64)."; exit 1; }

# grading splits Qwen2.5-7B across two GPUs (src/pipeline/scoring.py), so require 2 × 24 GB NVIDIA GPUs
command -v nvidia-smi >/dev/null 2>&1 || {
    echo "ERROR: nvidia-smi not found. Install the NVIDIA driver first (2 NVIDIA GPUs with 24 GB each required)."; exit 1; }
mapfile -t GPU_MEM < <(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits)
BIG_GPUS=0
for m in "${GPU_MEM[@]}"; do (( ${m// /} >= 23000 )) && BIG_GPUS=$((BIG_GPUS + 1)); done
echo "==> GPUs found:"; nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader | sed 's/^/    /'
if (( BIG_GPUS < 2 )); then
    echo "ERROR: NurseAssist needs 2 NVIDIA GPUs with 24 GB memory each; found $BIG_GPUS."
    exit 1
fi

# ---------------------------------------------------------------- conda
find_conda() {
    command -v conda 2>/dev/null && return 0
    for c in "$HOME/miniconda3/bin/conda" "$HOME/anaconda3/bin/conda" \
             "/opt/miniconda3/bin/conda" "/opt/anaconda3/bin/conda"; do
        [[ -x "$c" ]] && { echo "$c"; return 0; }
    done
    return 1
}
if CONDA_BIN="$(find_conda)"; then
    echo "==> using conda: $CONDA_BIN"
else
    echo "==> conda was not found. NurseAssist needs Miniconda (free, ~1 GB)."
    ok="$(ask "    Download and install Miniconda into $HOME/miniconda3? [Y/n] ")"
    [[ "${ok:-Y}" =~ ^[Yy]$ ]] || { echo "Install Miniconda, then run this installer again."; exit 1; }
    MC="$(mktemp -d)/miniconda.sh"
    curl -fL -o "$MC" https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    bash "$MC" -b -p "$HOME/miniconda3"
    rm -f "$MC"
    CONDA_BIN="$HOME/miniconda3/bin/conda"
fi
export PATH="$(dirname "$CONDA_BIN"):$PATH"

# ---------------------------------------------------------------- HF token
# Every user supplies their own token; it is only ever stored on this computer.
ENV_FILE="$INSTALL_DIR/src/.env"
check_token() {
    local t="$1" code
    code=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $t" \
        https://huggingface.co/api/whoami-v2) || true
    [[ "$code" == "200" ]] || { echo "    ✗ Token was rejected by Hugging Face (HTTP $code)."; return 1; }
    code=$(curl -s -o /dev/null -w '%{http_code}' -I -L -H "Authorization: Bearer $t" \
        https://huggingface.co/pyannote/speaker-diarization-community-1/resolve/main/config.yaml) || true
    [[ "$code" == "200" ]] || {
        echo "    ✗ Token works, but this account has not accepted the pyannote model terms (HTTP $code)."
        echo "      Open https://huggingface.co/pyannote/speaker-diarization-community-1"
        echo "      and click \"Agree and access repository\", then try again."
        return 1; }
    echo "    ✓ Token verified."
}

if [[ -f "$ENV_FILE" ]] && grep -q '^HF_TOKEN=hf_' "$ENV_FILE"; then
    keep="$(ask "==> A token from a previous NurseAssist install exists here. Keep it? [Y/n] ")"
    [[ "${keep:-Y}" =~ ^[Yy]$ ]] || rm -f "$ENV_FILE"
fi
if [[ ! -f "$ENV_FILE" ]]; then
    cat <<'EOF'

==> NurseAssist needs YOUR OWN free Hugging Face token (for speaker detection).
    1. Create an account at     https://huggingface.co/join
    2. Create a "Read" token at https://huggingface.co/settings/tokens
    3. Accept the model terms:  https://huggingface.co/pyannote/speaker-diarization-community-1
EOF
    for attempt in 1 2 3; do
        HF="$(ask "    Paste your token (hf_...): ")"
        HF="${HF//[[:space:]]/}"
        if check_token "$HF"; then break; fi
        if (( attempt == 3 )); then
            skip="$(ask "    Save this token anyway and fix it later in $ENV_FILE? [y/N] ")"
            [[ "${skip:-N}" =~ ^[Yy]$ ]] || exit 1
        fi
    done
    echo "HF_TOKEN=$HF" > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
fi

# ---------------------------------------------------------------- uninstaller
cat > "$INSTALL_DIR/uninstall.sh" <<EOF
#!/usr/bin/env bash
# Removes NurseAssist: its conda env, app-menu entry and this folder.
read -r -p "Remove NurseAssist from $INSTALL_DIR? [y/N] " ok
[[ "\${ok:-N}" =~ ^[Yy]$ ]] || exit 0
"$CONDA_BIN" env remove -y -n nurseassist
rm -f "\$HOME/.local/share/applications/NurseAssist.desktop"
rm -rf "$INSTALL_DIR"
echo "NurseAssist removed. Downloaded models remain in ~/.cache/huggingface and ~/.cache/torch."
EOF
chmod +x "$INSTALL_DIR/uninstall.sh"

# ---------------------------------------------------------------- install
echo "==> starting environment + model setup (this takes a while)..."
bash "$INSTALL_DIR/install.sh" </dev/tty
echo "   To uninstall later:  bash $INSTALL_DIR/uninstall.sh"
exit 0
__PAYLOAD_BELOW__
