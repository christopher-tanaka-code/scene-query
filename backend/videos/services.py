from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, List, Tuple

from django.conf import settings
from django.db import transaction

from .models import TranscriptSegment, Video
from .utils.chunking import chunk_segments
from .utils.embeddings import embed_text, embed_texts
from .utils.ffmpeg import generate_frame
from .utils.progress import send_progress
from .utils.search import cosine
from .utils.transcription import transcribe

def _hhmmss(seconds: float) -> str:
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"


def process_video(video_id: int, file_path: Path) -> None:
    """
    End-to-end processing pipeline for a video:
      - Transcribe audio to segments
      - Chunk segments into ~window blocks
      - Embed chunk texts
      - Store TranscriptSegment rows
      - Update Video.status and emit websocket progress
    """
    try:
        send_progress(video_id, "transcribe", 10, "Transcribing...")
        segments = transcribe(str(file_path), model_size=os.getenv("WHISPER_MODEL", "small"))

        send_progress(video_id, "chunk", 30, "Chunking transcript...")
        chunks = chunk_segments(segments, window_sec=15.0)

        send_progress(video_id, "embed", 60, "Embedding text...")
        vecs = embed_texts([c["text"] for c in chunks])

        video = Video.objects.get(id=video_id)
        send_progress(video_id, "index", 80, "Saving index...")
        with transaction.atomic():
            TranscriptSegment.objects.filter(video=video).delete()
            objs: List[TranscriptSegment] = []
            for c, v in zip(chunks, vecs):
                objs.append(TranscriptSegment(
                    video=video,
                    text=c["text"],
                    start_sec=float(c["start"]),
                    end_sec=float(c["end"]),
                    embedding=v,
                ))
            TranscriptSegment.objects.bulk_create(objs)

        video.status = "ready"
        video.save(update_fields=["status"])
        send_progress(video_id, "ready", 100, "Ready")
    except Exception as e:
        try:
            video = Video.objects.get(id=video_id)
            video.status = "error"
            video.save(update_fields=["status"])
        except Exception:
            pass
        send_progress(video_id, "error", 100, f"Error: {e}")
        # Re-raise so callers (e.g., upload view) can surface the error detail
        raise


def search_video(video: Video, query: str) -> Dict:
    """
    Compute best matching transcript segment for the query and generate a frame preview.
    Returns a dict with keys: best, alternatives.
    """
    qvec = embed_text(query)
    segs = list(TranscriptSegment.objects.filter(video_id=video.id).values(
        "id", "text", "start_sec", "end_sec", "embedding"
    ))
    if not segs:
        raise ValueError("no segments")

    scored: List[Tuple[float, Dict]] = []
    for s in segs:
        score = cosine(qvec, s["embedding"])  # safe even if normalized
        scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)

    best_score, best = scored[0]
    alt = scored[1:3]

    # Frame at best start + 0.5s
    ts = float(best["start_sec"]) + 0.5
    frames_dir = Path(settings.MEDIA_ROOT) / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_name = f"{video.id}_{int(ts*1000)}.jpg"
    frame_path = frames_dir / frame_name
    try:
        if not frame_path.exists():
            generate_frame(Path(settings.MEDIA_ROOT) / video.file.name, frame_path, ts)
    except Exception:
        pass

    return {
        "best": {
            "timestamp": float(best["start_sec"]),
            "hhmmss": _hhmmss(float(best["start_sec"])),
            "text": best["text"],
            "score": round(float(best_score), 4),
            "frameUrl": f"/media/frames/{frame_name}",
        },
        "alternatives": [
            {
                "timestamp": float(s["start_sec"]),
                "hhmmss": _hhmmss(float(s["start_sec"])),
                "text": s["text"],
                "score": round(float(sc), 4),
            }
            for sc, s in alt
        ],
    }
