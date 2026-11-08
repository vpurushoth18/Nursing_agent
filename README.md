# thesis

## System requirements

NurseAssist needs a GPU workstation or server — a typical office PC or laptop will not work.

**The computer must have**

| | Requirement |
|---|---|
| Operating system | 64-bit **Linux** (Ubuntu 20.04+, Debian 11+, Rocky/AlmaLinux 8+). Windows and macOS are not supported. |
| Graphics cards | **2 NVIDIA GPUs with 24 GB memory each** (e.g. 2 × A30, RTX 3090/4090, A5000) — required |
| GPU driver | NVIDIA driver **560 or newer**; `nvidia-smi` must list both GPUs |
| RAM | 32 GB or more |
| Disk space | ~60 GB free |
| Display | A monitor, or remote desktop (VNC) — it is a window-based app |

**Needed during installation**

- **Internet connection** — about 50 GB is downloaded.
- **Your own free Hugging Face token:**
  1. Sign up at https://huggingface.co/join
  2. Create a *Read* token at https://huggingface.co/settings/tokens
  3. Open https://huggingface.co/pyannote/speaker-diarization-community-1 and click **Agree and access**

**Installed automatically** — Miniconda, Python, PyTorch, WhisperX, the AI models and the app-menu shortcut.

Tested on 2 × NVIDIA A30 (24 GB), driver 565.57.01, AlmaLinux 9.5.

## Install

```bash
bash NurseAssist-installer.run
```

See [INSTALL.md](INSTALL.md) for details and troubleshooting.

## Developer setup

# 1. Pull requirements.txt and setup a conda environment

# 2. Force the system to use Conda's fixed C++ and audio libraries first
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH

# 3. Launch the app (from /src/
python -m app.main
