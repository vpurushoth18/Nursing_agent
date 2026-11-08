#!/usr/bin/env bash
# NurseAssist launcher (double-click friendly)
source /nfs/cc-filer/home/pvelayuthan/miniconda3/etc/profile.d/conda.sh
conda activate nurseassist
# Force conda's C++/audio/font libs first (fixes PyQt6 harfbuzz/freetype clash)
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
export DISPLAY=${DISPLAY:-:1.0}
cd "$(dirname "$0")/src"
exec python -m app.main
