from django.apps import AppConfig
import os


class VideosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "videos"

    def ready(self):
        # Warm up models at startup so first request doesn't pay the download/load cost
        if os.getenv("DISABLE_MODEL_WARMUP", "false").lower() == "true":
            return
        try:
            from .utils.transcription import get_whisper_model
            from .utils.embeddings import get_model as get_embed_model

            model_size = os.getenv("WHISPER_MODEL", "small")

            # These calls will download (if allowed) and cache the models
            get_whisper_model(model_size)
            get_embed_model()

            print("[videos] Model warm-up completed.")
        except Exception as e:
            # Do not crash the app; the upload endpoint will surface detailed errors
            print(f"[videos] Model warm-up skipped due to error: {e}")
