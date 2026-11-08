# NurseAssist — Install & Run on Another Computer

NurseAssist transcribes a clinical assessment recording, identifies the Nurse vs
Patient, and grades it against a rubric using Whisper (ASR) + Qwen2.5-7B (LLM).

## What the target computer needs (prerequisites)

| Requirement | Why | Check |
|---|---|---|
| **64-bit Linux** (x86_64, glibc ≥ 2.28) | PyTorch/CUDA wheels are Linux builds | `uname -m`, `ldd --version` |
| **Two NVIDIA GPUs, 24 GB each** *(required)* | `scoring.py` splits Qwen-7B across GPU 0 + 1 (22 GiB each) | `nvidia-smi` |
| **NVIDIA driver ≥ 560** (CUDA 12.6 capable) | PyTorch is built for CUDA 12.6 | `nvidia-smi` shows "CUDA Version: 12.6+" |
| **32 GB+ system RAM** *(recommended)* | loading the 7B model in float16 | `free -g` |
| **conda** (Miniconda/Anaconda) | builds the Python environment | `conda --version` |
| **~60 GB free disk** | models (~45 GB) + libraries (~8 GB); disk quotas count too | `df -h . ~` |
| **Internet access** | downloads models + packages | — |
| **Hugging Face token** | pyannote speaker diarization | see step 2 |
| **A display** (monitor, or VNC/X) | it's a GUI app | `echo $DISPLAY` |

> **Hugging Face access:** log in at huggingface.co, create a token
> (Settings → Access Tokens), and on the model page
> **pyannote/speaker-diarization-community-1** click **"Agree and access"**.
> Without this the diarization step returns HTTP 403.

## Install (one file)

1. Download `NurseAssist-installer.run` to the new machine.
2. In a terminal:

   ```bash
   bash NurseAssist-installer.run
   ```

   It will: unpack the app into `~/NurseAssist` (use `--dir DIR` for another
   location), install Miniconda if it is missing, ask for **your own** HF token and
   check it works, create the `nurseassist` conda env, install PyTorch (CUDA 12.6)
   and all pinned dependencies, download the models, and add NurseAssist to the
   applications menu.

To uninstall: `bash ~/NurseAssist/uninstall.sh`

**Building the installer** (developers, from the project root):
`bash packaging/build_installer.sh` → `dist/NurseAssist-installer.run`.
The build never includes `src/.env`, models, or generated outputs.

## Run

- **From a terminal:** `bash run_app.sh`
- **By icon:** open your applications menu → **NurseAssist**, or double-click
  `NurseAssist.desktop` in the folder. (In some file managers you must first
  right-click → Properties → *Allow this file to run as a program*.)

Then in the app:
1. **Input** tab → select an audio file (`.mp3/.wav/.m4a`) and a rubric `.docx`.
2. **Begin Grading**.
3. **Rubric Output** tab → download the graded `.docx`.
4. **Forensics** tab → audit log + reproducibility re-run.

## Notes / gotchas

- **PyQt6 + harfbuzz:** the launcher exports
  `LD_LIBRARY_PATH=$CONDA_PREFIX/lib` so Qt uses conda's freetype/harfbuzz.
  Running `python -m app.main` **without** this can fail with
  `libharfbuzz.so.0: undefined symbol: FT_Get_Colorline_Stops`.
- **Two 24 GB GPUs are required:** the installer stops if it finds fewer.
  Tested on 2 × NVIDIA A30 (24 GB), driver 565.57.01, AlmaLinux 9.5.
- **torchcodec warning** at startup is harmless — audio is decoded via ffmpeg and
  pyannote uses an in-memory waveform.
- **First grading run** is slower (it caches the runtime models); later runs are fast.
- **`DISPLAY`:** the generated `run_app.sh` defaults to `:0`. Over VNC set the
  matching display, e.g. `DISPLAY=:1.0 bash run_app.sh`.
