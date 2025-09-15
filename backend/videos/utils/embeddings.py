from __future__ import annotations
import os
from pathlib import Path
from typing import List
from sentence_transformers import SentenceTransformer

_model_cache = None


def get_model():
    global _model_cache
    if _model_cache is not None:
        return _model_cache

    # Controls
    local_path = os.getenv("EMBED_MODEL_PATH")
    model_name = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    allow_downloads = os.getenv("ALLOW_MODEL_DOWNLOADS", "true").lower() != "false"
    cache_dir = os.getenv("EMBED_CACHE_DIR") or os.getenv("MODEL_CACHE_DIR")
    device = os.getenv("EMBED_DEVICE")  # e.g., "cuda" or "cpu"; None = auto
    if cache_dir:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)

    try:
        if local_path and os.path.isdir(local_path):
            _model_cache = SentenceTransformer(local_path, cache_folder=cache_dir, device=device)
        else:
            if not allow_downloads:
                raise RuntimeError(
                    "Embedding model not available locally and downloads are disabled. "
                    "Set EMBED_MODEL_PATH or set ALLOW_MODEL_DOWNLOADS=true."
                )
            _model_cache = SentenceTransformer(model_name, cache_folder=cache_dir, device=device)
    except Exception as e:
        raise RuntimeError(
            "Failed to load embedding model. "
            + ("Using local path. " if local_path else f"Using name '{model_name}'. ")
            + ("Downloads are disabled. " if not allow_downloads else "")
            + f"Original error: {e}"
        )
    return _model_cache


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = get_model()
    batch_size = int(os.getenv("EMBED_BATCH_SIZE", "32"))
    vecs = model.encode(texts, normalize_embeddings=True, batch_size=batch_size, show_progress_bar=False)
    return [v.tolist() for v in vecs]


def embed_text(text: str) -> List[float]:
    return embed_texts([text])[0]
