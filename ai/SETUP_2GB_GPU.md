# Setup For 2GB GPU

## What is prepared

- `install_windows_gpu.bat`: creates `.venv` and installs dependencies.
- `check_runtime.py`: verifies Python, Torch, CUDA, weights, videos, and output directory.
- `run_single_video.bat`: runs one input video.
- `run_batch_2gb.bat`: runs the batch script with safe defaults for a 2GB GPU.
- `batch_video_plate.py`: stops each video job after the same plate is detected `3` times and writes a Markdown report.

## Recommended environment

- Windows
- Python `3.10`, `3.11`, or `3.12`
- NVIDIA GPU with about `2GB` VRAM

## Install

From the project folder, run:

```powershell
.\install_windows_gpu.bat
```

This script installs PyTorch CUDA wheels from the official PyTorch index for Windows pip CUDA builds:
- PyTorch local install page: https://pytorch.org/get-started/locally/

## Verify

Run:

```powershell
.\.venv\Scripts\python check_runtime.py
```

Expected important lines:

- `CUDA available: True`
- `Detector weights: OK`
- `Recognizer weights: OK`

If your GPU has around `2GB` VRAM, the safe batch setting is:

```text
Recommended batch max_concurrent: 1
```

## Run one video

Default sample:

```powershell
.\run_single_video.bat
```

Specific video:

```powershell
.\run_single_video.bat "D:\path\to\your_video.mp4"
```

Output:

- `io/output/single_result.mp4`

## Run batch on 2GB GPU

Prepared safe run:

```powershell
.\run_batch_2gb.bat
```

This uses:

- `--max-concurrent 1`
- `--launch-interval 1`
- `--success-count 3`

Outputs:

- Result videos in `io/output/batch_videos`
- Final report in `io/output/batch_report_2gb.md`

## If you want to run your own list

Edit:

- `video_jobs_10.txt`

Then run:

```powershell
.\run_batch_2gb.bat
```

Each line in `video_jobs_10.txt` must be a full video path.

## Notes for 2GB GPU

- Use `max_concurrent=1` as the default safe value.
- Do not start `10` GPU processes at the same time.
- If Windows is using VRAM for display, usable VRAM for inference will be lower than the card total.
- The script now warns if `max_concurrent` is above the recommended value for the detected GPU memory.
