from __future__ import annotations
import asyncio
import os
from typing import Dict, List

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.db.models import QuerySet

from .models import TranscriptSegment, Video
from .utils.embeddings import embed_text
from .utils.search import cosine

try:
    from openai import AsyncOpenAI as _OpenAIClient  # type: ignore
except Exception:  # pragma: no cover
    _OpenAIClient = None  # type: ignore


class VideoProgressConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.video_id = self.scope["url_route"]["kwargs"]["video_id"]
        self.group_name = f"video_{self.video_id}"
        try:
            print(f"[ws] connect video_id={self.video_id} channel={self.channel_name}")
        except Exception:
            pass
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        try:
            print(f"[ws] disconnect video_id={self.video_id} channel={self.channel_name} code={close_code}")
        except Exception:
            pass
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def progress(self, event):
        try:
            print(f"[ws] progress -> video_id={self.video_id} stage={event.get('stage')} pct={event.get('pct')}")
        except Exception:
            pass
        await self.send_json({
            "type": "progress",
            "stage": event.get("stage"),
            "pct": event.get("pct", 0),
            "message": event.get("message", ""),
        })


class VideoChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.video_id = int(self.scope["url_route"]["kwargs"]["video_id"])
        self._chat_task: asyncio.Task | None = None
        try:
            print(f"[ws-chat] connect video_id={self.video_id} channel={self.channel_name}")
        except Exception:
            pass
        await self.accept()
        await self.send_json({
            "type": "chat_info",
            "message": "Connected. Ask a question about this video.",
        })

    async def disconnect(self, close_code):
        try:
            print(f"[ws-chat] disconnect video_id={self.video_id} channel={self.channel_name} code={close_code}")
        except Exception:
            pass
        if self._chat_task and not self._chat_task.done():
            self._chat_task.cancel()
            try:
                await self._chat_task
            except Exception:
                pass

    async def receive_json(self, content, **kwargs):
        msg_type = content.get("type")
        if msg_type == "user_message":
            question = (content.get("text") or "").strip()
            if not question:
                await self.send_json({"type": "chat_error", "error": "Empty question"})
                return
            if self._chat_task and not self._chat_task.done():
                self._chat_task.cancel()
                try:
                    await self._chat_task
                except Exception:
                    pass
                await self.send_json({"type": "chat_info", "message": "Canceled previous response."})
            try:
                print(f"[ws-chat] receive user_message video_id={self.video_id} len={len(question)}")
            except Exception:
                pass
            await self.send_json({"type": "chat_info", "message": "Processing your question..."})
            self._chat_task = asyncio.create_task(self._handle_chat(question))
        elif msg_type == "cancel":
            if self._chat_task and not self._chat_task.done():
                self._chat_task.cancel()
                try:
                    await self._chat_task
                except Exception:
                    pass
                await self.send_json({"type": "chat_info", "message": "Canceled."})
        else:
            await self.send_json({"type": "chat_error", "error": f"Unknown message type: {msg_type}"})

    async def _handle_chat(self, question: str):
        try:
            ctx = await self._retrieve_context(self.video_id, question, top_k=5)
        except Exception as e:
            await self.send_json({"type": "chat_error", "error": f"Retrieval failed: {e}"})
            return

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            await self.send_json({"type": "chat_error", "error": "OPENAI_API_KEY not configured on server."})
            return

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        system_prompt = (
            "You are a helpful assistant answering questions about a single video. "
            "Use the provided transcript excerpts with timestamps as the source of truth. "
            "Cite timestamps inline like [mm:ss] where relevant. If unsure, say you don't know."
        )
        user_prompt = (
            f"Question: {question}\n\n"
            "Relevant excerpts (with timestamps):\n" + ctx + "\n\n"
            "Answer succinctly and include timestamps like [mm:ss] where applicable."
        )

        if _OpenAIClient is None:
            await self.send_json({"type": "chat_error", "error": "OpenAI async client not available on server."})
            return

        client = _OpenAIClient(api_key=api_key)
        try:
            stream = await client.chat.completions.create(
                model=model,
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            async for event in stream:
                try:
                    delta = event.choices[0].delta  # type: ignore[attr-defined]
                except Exception:
                    delta = None
                if not delta:
                    continue
                token = getattr(delta, "content", None)
                if token:
                    await self.send_json({"type": "chat_token", "token": token})
            await self.send_json({"type": "chat_done"})
        except asyncio.CancelledError:
            await self.send_json({"type": "chat_info", "message": "Generation canceled."})
        except Exception as e:
            try:
                print(f"[ws-chat] error video_id={self.video_id}: {e}")
            except Exception:
                pass
            await self.send_json({"type": "chat_error", "error": str(e)})
        finally:
            if getattr(self, "_chat_task", None) and self._chat_task.done():
                self._chat_task = None

    async def _retrieve_context(self, video_id: int, question: str, top_k: int = 5) -> str:
        qvec = await asyncio.get_event_loop().run_in_executor(None, embed_text, question)

        @database_sync_to_async
        def _fetch_segments() -> List[Dict]:
            return list(
                TranscriptSegment.objects.filter(video_id=video_id).values(
                    "start_sec", "end_sec", "text", "embedding"
                )
            )

        segs: List[Dict] = await _fetch_segments()
        if not segs:
            return "(No transcript segments available)"

        scored: List[tuple[float, Dict]] = []
        for s in segs:
            try:
                score = cosine(qvec, s["embedding"])  # type: ignore[arg-type]
            except Exception:
                score = 0.0
            scored.append((score, s))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:max(1, top_k)]

        def _hhmmss(seconds: float) -> str:
            s = int(seconds)
            m = (s % 3600) // 60
            sec = s % 60
            return f"{m:02d}:{sec:02d}"

        lines: List[str] = []
        for sc, s in top:
            ts = _hhmmss(float(s["start_sec"]))
            lines.append(f"[{ts}] {s['text']}")
        return "\n".join(lines)
