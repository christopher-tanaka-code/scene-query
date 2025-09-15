from __future__ import annotations
import asyncio
from channels.layers import get_channel_layer


async def _send_progress_async(video_id: int, stage: str, pct: int, message: str):
    layer = get_channel_layer()
    if not layer:
        return
    await layer.group_send(
        f"video_{video_id}",
        {"type": "progress", "stage": stage, "pct": pct, "message": message},
    )


def send_progress(video_id: int, stage: str, pct: int, message: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        asyncio.create_task(_send_progress_async(video_id, stage, pct, message))
    else:
        asyncio.run(_send_progress_async(video_id, stage, pct, message))
