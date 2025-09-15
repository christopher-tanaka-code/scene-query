from __future__ import annotations
import os
from pathlib import Path
from faster_whisper import WhisperModel


_whisper_cache: WhisperModel | None = None


def get_whisper_model(model_size: str = "small") -> WhisperModel:
    global _whisper_cache
    if _whisper_cache is not None:
        return _whisper_cache

    # Controls
    local_model_path = os.getenv("WHISPER_MODEL_PATH")
    allow_downloads = os.getenv("ALLOW_MODEL_DOWNLOADS", "true").lower() != "false"
    cache_dir = os.getenv("WHISPER_CACHE_DIR") or os.getenv("MODEL_CACHE_DIR")
    if cache_dir:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)

    model_spec = local_model_path or model_size
    # Device/precision controls
    device = os.getenv("WHISPER_DEVICE", "cpu")  # cpu | cuda | auto
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "float32")  # e.g., float16, int8_float16, int8
    # Parallelism controls (CPU)
    # Do not pass None here; ctranslate2's underlying Whisper binding expects an int
    # 0 lets the runtime choose a default number of threads
    cpu_threads = int(os.getenv("WHISPER_CPU_THREADS", "0") or 0)
    num_workers = int(os.getenv("WHISPER_NUM_WORKERS", "1") or 1)

    try:
        _whisper_cache = WhisperModel(
            model_spec,
            device=device,
            compute_type=compute_type,
            download_root=cache_dir,  # None means default cache
            local_files_only=not allow_downloads,
            cpu_threads=cpu_threads,
            num_workers=num_workers,
        )
    except Exception as e:
        dl_note = "Downloads are disabled (set ALLOW_MODEL_DOWNLOADS=true)" if not allow_downloads else ""
        raise RuntimeError(
            "Failed to load Whisper model. "
            + ("Using local path. " if local_model_path else f"Using name '{model_size}'. ")
            + dl_note
            + f" Original error: {e}"
        )
    return _whisper_cache


def transcribe(path: str, model_size: str = "small"):
    """
    Returns list of segments: [{"start": float, "end": float, "text": str}]
    """
    model = get_whisper_model(model_size)
    # Transcription tuning via env
    vad_filter = os.getenv("WHISPER_VAD_FILTER", "true").lower() != "false"
    beam_size = int(os.getenv("WHISPER_BEAM_SIZE", "1"))  # 1 is fastest greedy
    best_of = int(os.getenv("WHISPER_BEST_OF", "1"))
    cond_prev = os.getenv("WHISPER_CONDITION_ON_PREV", "false").lower() == "true"
    language = os.getenv("WHISPER_LANGUAGE") or None  # set to 'en' to skip detection
    temperature = float(os.getenv("WHISPER_TEMPERATURE", "0"))

    segments, _ = model.transcribe(
        path,
        vad_filter=vad_filter,
        beam_size=beam_size,
        best_of=best_of,
        condition_on_previous_text=cond_prev,
        language=language,
        temperature=temperature,
    )
    out = []
    for seg in segments:
        out.append({
            "start": float(seg.start),
            "end": float(seg.end),
            "text": seg.text.strip(),
        })
    return out
