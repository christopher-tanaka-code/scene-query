from __future__ import annotations
import json
import os
import shutil
import subprocess
from pathlib import Path

# Allow overriding via environment variables (useful on Windows where PATH may not include ffmpeg)
FFPROBE = os.getenv("FFPROBE_PATH") or shutil.which("ffprobe") or "ffprobe"
FFMPEG = os.getenv("FFMPEG_PATH") or shutil.which("ffmpeg") or "ffmpeg"


def get_duration_seconds(file_path: str | Path) -> float:
    cmd = [
        FFPROBE,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        str(file_path),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise RuntimeError(f"ffprobe not found. Set FFPROBE_PATH in .env or add ffprobe to PATH. Original error: {e}")
    if res.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {res.stderr}")
    data = json.loads(res.stdout)
    duration = float(data["format"].get("duration", 0.0))
    return duration


def generate_frame(file_path: str | Path, out_path: str | Path, ts_seconds: float) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    # -ss before -i for faster seek
    cmd = [
        FFMPEG,
        "-y",
        "-ss", str(max(0.0, ts_seconds)),
        "-i", str(file_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(out),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise RuntimeError(f"ffmpeg not found. Set FFMPEG_PATH in .env or add ffmpeg to PATH. Original error: {e}")
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed: {res.stderr}")
