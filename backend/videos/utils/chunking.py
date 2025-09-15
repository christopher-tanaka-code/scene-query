from __future__ import annotations
from typing import List, Dict


def chunk_segments(segments: List[Dict], window_sec: float = 15.0):
    """
    Coalesce transcription segments into ~window_sec windows keeping start/end.
    """
    chunks = []
    if not segments:
        return chunks
    cur = None
    for s in segments:
        start = s["start"]
        end = s["end"]
        text = s["text"]
        if cur is None:
            cur = {"start": start, "end": end, "text": text}
            continue
        if (s["end"] - cur["start"]) <= window_sec:
            cur["end"] = end
            if cur["text"]:
                cur["text"] += " "
            cur["text"] += text
        else:
            chunks.append(cur)
            cur = {"start": start, "end": end, "text": text}
    if cur is not None:
        chunks.append(cur)
    return chunks
