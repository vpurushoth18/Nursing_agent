#!/usr/bin/env bash
###############################################################################
# NurseAssist — one-shot installer
#
#   Usage:   bash install.sh
#
# Reproduces the full runtime on a fresh machine:
#   1. creates the `nurseassist` conda env (Python 3.10 + ffmpeg/libsndfile)
#   2. installs PyTorch (CUDA 12.6) + all pinned Python deps
#   3. asks for your Hugging Face token and writes src/.env
#   4. pre-downloads every model the app uses (~45 GB):
#        - src/models/ copies checked by the splash screen (Whisper-medium + Qwen2.5-7B)
#        - Hugging Face cache models used for grading (Qwen2.5-7B, faster-whisper-medium,
#          pyannote diarization) + the torchaudio wav2vec2 alignment model
#   5. writes run_app.sh + a double-click desktop launcher
#
# Prerequisites (must already exist on the machine):
#   - NVIDIA GPU + driver (CUDA 12.x capable)   -> `nvidia-smi` must work
#   - conda (Miniconda/Anaconda) on PATH
#   - ~60 GB free disk (conda env + models), internet access
#   - a Hugging Face token with access to:
#         pyannote/speaker-diarization-community-1
###############################################################################
set -euo pipefail

ENV_NAME="nurseassist"
HERE="$(cd "$(dirname "$0")" && pwd)"
REQ="$HERE/environment/requirements.txt"

echo "==> NurseAssist installer"
echo "    project: $HERE"

# ---------------------------------------------------------------- sanity checks
command -v conda >/dev/null 2>&1 || { echo "ERROR: conda not found on PATH. Install Miniconda first."; exit 1; }
if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "WARNING: nvidia-smi not found — the grading step needs an NVIDIA GPU."
    read -r -p "    Continue anyway? [y/N] " ok; [[ "${ok:-N}" =~ ^[Yy]$ ]] || exit 1
fi
[[ -f "$REQ" ]] || { echo "ERROR: $REQ not found."; exit 1; }

# conda env + models need ~60 GB; check both the project disk and the home disk (HF/torch caches)
NEED_GB=60
for d in "$HERE" "$HOME"; do
    free_gb=$(( $(df -Pk "$d" | awk 'NR==2 {print $4}') / 1024 / 1024 ))
    if (( free_gb < NEED_GB )); then
        echo "WARNING: only ${free_gb} GB free on the disk holding $d (need ~${NEED_GB} GB)."
        echo "         Disk quotas can also be lower than what df reports."
        read -r -p "    Continue anyway? [y/N] " ok; [[ "${ok:-N}" =~ ^[Yy]$ ]] || exit 1
    fi
done

# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"

# ---------------------------------------------------------------- 1. conda env
if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    echo "==> conda env '$ENV_NAME' already exists — reusing it."
else
    echo "==> creating conda env '$ENV_NAME' (python 3.10 + ffmpeg + libsndfile)..."
    # --override-channels: fresh Miniconda blocks the default Anaconda channels until their ToS is accepted
    conda create -y -n "$ENV_NAME" --override-channels -c conda-forge python=3.10 ffmpeg libsndfile
fi
conda activate "$ENV_NAME"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"

# ---------------------------------------------------------------- 2. python deps
echo "==> upgrading pip..."
python -m pip install --upgrade pip

echo "==> installing PyTorch (CUDA 12.6)..."
pip install --index-url https://download.pytorch.org/whl/cu126 \
    torch==2.8.0 torchaudio==2.8.0 torchvision==0.23.0

echo "==> installing remaining pinned dependencies..."
# everything from requirements.txt that came from pip, minus the torch trio
grep 'pypi_0' "$REQ" \
  | sed -E 's/=pypi_0//; s/=/==/' \
  | grep -vE '^(torch|torchaudio|torchvision)==' > /tmp/nurse_pip_reqs.txt
pip install -r /tmp/nurse_pip_reqs.txt

# ---------------------------------------------------------------- 3. HF token
ENV_FILE="$HERE/src/.env"
if [[ -f "$ENV_FILE" ]] && grep -q '^HF_TOKEN=' "$ENV_FILE"; then
    echo "==> src/.env already has an HF_TOKEN — keeping it."
else
    echo "==> A Hugging Face token is required for speaker diarization (pyannote)."
    read -r -p "    Paste your HF token (hf_...): " HF
    echo "HF_TOKEN=$HF" > "$ENV_FILE"
    echo "    wrote $ENV_FILE"
fi

# ---------------------------------------------------------------- 4. models
echo "==> pre-downloading models (~45 GB). This can take a while..."
# the splash screen requires the src/models/ copies at every launch
( cd "$HERE/src" && python -c "
from pipeline.splash_backend import verify_and_download
print(verify_and_download('whisper_small'))
print(verify_and_download('qwen_0_5b'))
" )
# the grading pipeline loads these from the Hugging Face / torch caches instead
HF_TOKEN="$(grep '^HF_TOKEN=' "$ENV_FILE" | cut -d= -f2-)" python -c "
import os
from huggingface_hub import snapshot_download
import torchaudio
for repo in ['Qwen/Qwen2.5-7B-Instruct', 'Systran/faster-whisper-medium']:
    snapshot_download(repo); print('cached', repo)
torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H.get_model(); print('cached WAV2VEC2_ASR_BASE_960H')
try:
    snapshot_download('pyannote/speaker-diarization-community-1', token=os.environ['HF_TOKEN'])
    print('cached pyannote/speaker-diarization-community-1')
except Exception as e:
    print('WARNING: could not download pyannote diarization model:', e)
    print('         Accept its terms at https://huggingface.co/pyannote/speaker-diarization-community-1')
    print('         and check the token in src/.env - it will download on first use.')
"

# ---------------------------------------------------------------- 5. launcher
echo "==> writing launcher (run_app.sh)..."
cat > "$HERE/run_app.sh" <<EOF
#!/usr/bin/env bash
# NurseAssist launcher
source "\$(conda info --base)/etc/profile.d/conda.sh"
conda activate $ENV_NAME
export LD_LIBRARY_PATH=\$CONDA_PREFIX/lib:\${LD_LIBRARY_PATH:-}
export DISPLAY=\${DISPLAY:-:0}
cd "\$(dirname "\$0")/src"
exec python -m app.main
EOF
chmod +x "$HERE/run_app.sh"

echo "==> writing desktop launcher (NurseAssist.desktop)..."
cat > "$HERE/NurseAssist.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=NurseAssist
Comment=Clinical assessment grading (WhisperX + Qwen)
Exec=$HERE/run_app.sh
Icon=$HERE/nurseassist.png
Terminal=false
Categories=Education;
EOF
chmod +x "$HERE/NurseAssist.desktop"
# make it show in the app menu too
mkdir -p "$HOME/.local/share/applications"
cp "$HERE/NurseAssist.desktop" "$HOME/.local/share/applications/"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo ""
echo "==================================================================="
echo " NurseAssist installed."
echo "   Start it with:  bash $HERE/run_app.sh"
echo "   or find 'NurseAssist' in your applications menu."
echo "==================================================================="
