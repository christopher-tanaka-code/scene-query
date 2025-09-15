from django.urls import path
from . import views

urlpatterns = [
    path("api/videos/", views.VideoUploadView.as_view(), name="video-upload"),
    path("api/videos/<int:video_id>/", views.VideoDetailView.as_view(), name="video-detail"),
    path("api/videos/<int:video_id>/search", views.VideoSearchView.as_view(), name="video-search"),
    path("api/chat", views.ChatView.as_view(), name="chat"),
]
