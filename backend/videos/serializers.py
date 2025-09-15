from rest_framework import serializers
from .models import Video, TranscriptSegment


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ["id", "title", "file", "duration_sec", "status", "created_at"]


class TranscriptSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptSegment
        fields = ["id", "video", "text", "start_sec", "end_sec", "embedding"]
