from django.contrib import admin
from .models import Video, TranscriptSegment


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "duration_sec", "created_at")
    search_fields = ("title",)
    list_filter = ("status",)


@admin.register(TranscriptSegment)
class TranscriptSegmentAdmin(admin.ModelAdmin):
    list_display = ("id", "video", "start_sec", "end_sec")
    search_fields = ("text",)
    list_filter = ("video",)
