from __future__ import annotations
import os
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from .models import Video
from .serializers import VideoSerializer
from .services import process_video, search_video
from .utils.ffmpeg import get_duration_seconds


class VideoUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return JsonResponse({"detail": "file is required"}, status=400)
        if not f.name.lower().endswith((".mp4", ".mov", ".webm")):
            return JsonResponse({"detail": "unsupported media type"}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

        # Ensure media root exists
        try:
            Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return JsonResponse({"detail": f"Failed to prepare media directory: {e}"}, status=500)

        # Save file first to determine duration
        try:
            video = Video.objects.create(title=os.path.splitext(f.name)[0], file=f, status="processing")
        except Exception as e:
            return JsonResponse({"detail": f"Failed to save uploaded file: {e}"}, status=500)

        file_path = Path(settings.MEDIA_ROOT) / video.file.name
        try:
            duration = get_duration_seconds(file_path)
        except Exception as e:
            video.status = "error"
            video.save(update_fields=["status"])
            return JsonResponse({"detail": f"ffprobe failed: {e}"}, status=500)

        if duration > 180.0:
            video.delete()
            return JsonResponse({"detail": "> 3 minutes"}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        video.duration_sec = duration
        video.save(update_fields=["duration_sec"]) 

        # Synchronous processing: process the video before responding
        try:
            process_video(video.id, file_path)
        except Exception as e:
            # process_video internally marks status=error on failure
            video.refresh_from_db()
            return JsonResponse({"detail": f"processing failed: {e}"}, status=500)

        # Refresh and return the final state
        video.refresh_from_db()
        if video.status != "ready":
            return JsonResponse({"detail": f"processing ended with status {video.status}"}, status=500)

        ser = VideoSerializer(video)
        return JsonResponse(ser.data, status=201)


class VideoDetailView(APIView):
    def get(self, request, video_id: int):
        try:
            video = Video.objects.get(id=video_id)
        except Video.DoesNotExist:
            return JsonResponse({"detail": "not found"}, status=404)
        ser = VideoSerializer(video)
        return JsonResponse(ser.data)


class VideoSearchView(APIView):
    def get(self, request, video_id: int):
        q = request.GET.get("q", "").strip()
        if not q:
            return JsonResponse({"detail": "q required"}, status=400)
        try:
            video = Video.objects.get(id=video_id)
        except Video.DoesNotExist:
            return JsonResponse({"detail": "not found"}, status=404)
        if video.status != "ready":
            return JsonResponse({"detail": f"video status is {video.status}"}, status=400)

        try:
            data = search_video(video, q)
        except ValueError as ve:
            return JsonResponse({"detail": str(ve)}, status=400)
        except Exception as e:
            return JsonResponse({"detail": f"search failed: {e}"}, status=500)
        return JsonResponse(data)


class ChatView(APIView):
    def post(self, request):
        # Placeholder for future RAG chat logic
        return JsonResponse({"answer": "Not implemented yet", "citations": []}, status=501)
