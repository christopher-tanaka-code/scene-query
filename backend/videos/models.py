from __future__ import annotations
from django.db import models


class Video(models.Model):
    STATUS_CHOICES = (
        ("processing", "processing"),
        ("ready", "ready"),
        ("error", "error"),
    )

    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="videos/")
    duration_sec = models.FloatField(default=0.0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="processing")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Video({self.id}, {self.title})"


class TranscriptSegment(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="segments")
    text = models.TextField()
    start_sec = models.FloatField()
    end_sec = models.FloatField()
    embedding = models.JSONField()  # 384-dim list[float] for fallback; later swap to pgvector if available

    class Meta:
        indexes = [
            models.Index(fields=["video", "start_sec"]),
        ]

    def __str__(self) -> str:
        return f"Seg(v{self.video_id} {self.start_sec:.1f}-{self.end_sec:.1f}s)"
