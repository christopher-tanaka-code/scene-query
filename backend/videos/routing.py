from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"^ws/videos/(?P<video_id>\d+)/progress/$", consumers.VideoProgressConsumer.as_asgi()),
    re_path(r"^ws/videos/(?P<video_id>\d+)/chat/$", consumers.VideoChatConsumer.as_asgi()),
]
