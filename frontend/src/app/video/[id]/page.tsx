"use client";

import { API_BASE, searchVideo } from "@/lib/api";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

type VideoInfo = {
  id: number;
  title: string;
  file: string;
  duration_sec: number;
  status: "processing" | "ready" | "error";
};

export default function VideoPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [info, setInfo] = useState<VideoInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [q, setQ] = useState("");
  const [searching, setSearching] = useState(false);
  const [best, setBest] = useState<any | null>(null);
  const [alts, setAlts] = useState<any[]>([]);

  const videoRef = useRef<HTMLVideoElement | null>(null);

  type ChatMessage = { role: "system" | "user" | "assistant" | "error"; content: string };
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatConnecting, setChatConnecting] = useState(false);
  const [chatConnected, setChatConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const pendingToSendRef = useRef<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const chatScrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function fetchInfo() {
      try {
        const res = await fetch(`${API_BASE}/api/videos/${id}/`);
        if (!res.ok) {
          throw new Error(`Failed to load video: ${res.status}`);
        }
        const data = await res.json();
        if (!cancelled) {
          setInfo(data);
        }
      } catch (e: any) {
        if (!cancelled) setError(e?.message || "Failed to load video");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchInfo();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const onSearch = async () => {
    if (!q.trim()) return;
    setSearching(true);
    setError(null);
    try {
      const data = await searchVideo(id, q.trim());
      setBest(data.best);
      setAlts(data.alternatives || []);
      if (videoRef.current) {
        videoRef.current.currentTime = data.best.timestamp;
        videoRef.current.play().catch(() => {});
      }
    } catch (e: any) {
      setError(e?.message || "Search failed");
    } finally {
      setSearching(false);
    }
  };

  function toWsOrigin(httpBase: string): string {
    try {
      const u = new URL(httpBase);
      const proto = u.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${u.host}`;
    } catch {
      return httpBase.replace(/^http/, "ws");
    }
  }

  useEffect(() => {
    if (!id || Number.isNaN(id)) return;
    const wsUrl = `${toWsOrigin(API_BASE)}/ws/videos/${id}/chat/`;

    const connect = () => {
      if (
        wsRef.current &&
        (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)
      ) {
        return;
      }
      setChatConnecting(true);
      setChatConnected(false);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setChatConnecting(false);
        setChatConnected(true);
        reconnectAttemptsRef.current = 0;
        if (messages.length === 0) {
          setMessages([]);
        }
        const pending = pendingToSendRef.current;
        if (pending) {
          ws.send(JSON.stringify({ type: "user_message", text: pending }));
          pendingToSendRef.current = null;
        }
      };

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          const t = data?.type;
          if (t === "chat_info") {
            setMessages((prev) => [...prev, { role: "system", content: data.message || "" }]);
            if (data.message === "Processing your question...") setIsStreaming(true);
          } else if (t === "chat_error") {
            setMessages((prev) => [...prev, { role: "error", content: data.error || "Unknown error" }]);
            setIsStreaming(false);
          } else if (t === "chat_token") {
            const token: string = data.token || "";
            setMessages((prev) => {
              const next = [...prev];
              if (next.length === 0 || next[next.length - 1].role !== "assistant") {
                next.push({ role: "assistant", content: token });
              } else {
                next[next.length - 1] = {
                  ...next[next.length - 1],
                  content: next[next.length - 1].content + token,
                };
              }
              return next;
            });
            setIsStreaming(true);
          } else if (t === "chat_done") {
            setIsStreaming(false);
          }
        } catch {}
      };

      ws.onerror = () => {
        setMessages((prev) => [...prev, { role: "error", content: "WebSocket error" }]);
        setIsStreaming(false);
      };

      ws.onclose = () => {
        wsRef.current = null;
        setChatConnected(false);
        setChatConnecting(true);
        setIsStreaming(false);
        const attempt = Math.min(reconnectAttemptsRef.current + 1, 5);
        reconnectAttemptsRef.current = attempt;
        const delay = Math.min(500 * Math.pow(2, attempt - 1), 5000);
        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      try { wsRef.current?.close(); } catch {}
      wsRef.current = null;
    };
  }, [id]);

  const sendChat = () => {
    const text = chatInput.trim();
    if (!text) return;
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      pendingToSendRef.current = text;
      setMessages((prev) => [...prev, { role: "system", content: "Queued your question. Sending when connected..." }]);
      return;
    }
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    ws.send(JSON.stringify({ type: "user_message", text }));
    setChatInput("");
    setIsStreaming(true);
  };

  const cancelChat = () => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "cancel" }));
    }
    setIsStreaming(false);
  };

  useEffect(() => {
    const el = chatScrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  function renderMessageContent(content: string) {
    const parts: React.ReactNode[] = [];
    const regex = /\[(\d{2}):(\d{2})\]/g;
    let lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = regex.exec(content)) !== null) {
      const before = content.slice(lastIndex, m.index);
      if (before) parts.push(<span key={parts.length}>{before}</span>);
      const mm = parseInt(m[1], 10);
      const ss = parseInt(m[2], 10);
      const seconds = mm * 60 + ss;
      parts.push(
        <button
          key={parts.length}
          className="underline text-blue-600"
          onClick={() => {
            if (videoRef.current) {
              videoRef.current.currentTime = seconds;
              videoRef.current.play().catch(() => {});
            }
          }}
          title="Jump to timestamp"
        >
          [{m[1]}:{m[2]}]
        </button>
      );
      lastIndex = m.index + m[0].length;
    }
    const tail = content.slice(lastIndex);
    if (tail) parts.push(<span key={parts.length}>{tail}</span>);
    return parts;
  }

  if (loading) return <div className="p-8">Loading...</div>;
  if (error) return <div className="p-8 text-red-600">{error}</div>;
  if (!info) return <div className="p-8">Not found</div>;

  const videoUrl = `${API_BASE}${info.file}`;

  return (
    <div className="max-w-4xl mx-auto w-full py-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold">{info.title}</h1>
        <a href="/upload" className="text-sm text-blue-600 underline">Upload another</a>
      </div>

      <video ref={videoRef} src={videoUrl} controls className="w-full rounded border max-h-[70vh]" />

      <div className="mt-6 flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ask a question about this video (e.g., pricing, features)"
          className="flex-1 border rounded px-3 py-2"
        />
        <button
          onClick={onSearch}
          disabled={searching || !q.trim()}
          className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
        >
          {searching ? "Searching..." : "Search"}
        </button>
      </div>

      {best && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-[200px_1fr] gap-4 items-start">
          <div className="border rounded overflow-hidden">
            {best.frameUrl ? (
              <img src={`${API_BASE}${best.frameUrl}`} alt="Preview" className="w-full h-auto" />
            ) : (
              <div className="p-4 text-sm text-gray-500">No preview</div>
            )}
          </div>
          <div>
            <div className="text-sm text-gray-600">Best match at {best.hhmmss} (score {best.score})</div>
            <div className="mt-2 whitespace-pre-wrap">{best.text}</div>
            <button
              className="mt-3 text-sm text-blue-600 underline"
              onClick={() => {
                if (videoRef.current) {
                  videoRef.current.currentTime = best.timestamp;
                  videoRef.current.play().catch(() => {});
                }
              }}
            >Jump to timestamp</button>
          </div>
        </div>
      )}

      {alts.length > 0 && (
        <div className="mt-6">
          <div className="font-medium mb-2">Alternatives</div>
          <div className="space-y-3">
            {alts.map((a, idx) => (
              <div key={idx} className="p-3 border rounded">
                <div className="text-sm text-gray-600">
                  {a.hhmmss} (score {a.score})
                </div>
                <div className="mt-1 text-sm">{a.text}</div>
                <button
                  className="mt-2 text-xs text-blue-600 underline"
                  onClick={() => {
                    if (videoRef.current) {
                      videoRef.current.currentTime = a.timestamp;
                      videoRef.current.play().catch(() => {});
                    }
                  }}
                >Jump</button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-8">
        <div className="flex items-center justify-between mb-2">
          <div className="font-medium">Chat with this video</div>
          <div className="text-xs text-gray-500">{chatConnected ? "Connected" : chatConnecting ? "Connecting..." : "Disconnected"}</div>
        </div>
        <div ref={chatScrollRef} className="border rounded p-3 max-h-72 overflow-y-auto bg-white/60">
          {messages.length === 0 ? (
            <div className="text-sm text-gray-500">No messages yet. Ask a question below.</div>
          ) : (
            <div className="space-y-2">
              {messages.map((m, i) => (
                <div key={i} className={
                  m.role === "user" ? "text-right" : m.role === "error" ? "text-red-600" : ""
                }>
                  <div className={
                    "inline-block px-3 py-2 rounded " +
                    (m.role === "user" ? "bg-black text-white" : m.role === "assistant" ? "bg-gray-100" : "bg-yellow-50")
                  }>
                    <span className="whitespace-pre-wrap text-sm">{renderMessageContent(m.content)}</span>
                  </div>
                </div>
              ))}
              {isStreaming && (
                <div className="text-gray-500 text-xs">Assistant is typing…</div>
              )}
            </div>
          )}
        </div>
        <div className="mt-3 flex gap-2">
          <input
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="Ask the assistant about this video (answers cite timestamps)"
            className="flex-1 border rounded px-3 py-2"
            onKeyDown={(e) => { if (e.key === "Enter") sendChat(); }}
          />
          {isStreaming ? (
            <button
              onClick={cancelChat}
              className="px-4 py-2 rounded bg-gray-200 text-black"
            >Cancel</button>
          ) : (
            <button
              onClick={sendChat}
              disabled={!chatInput.trim() || !chatConnected}
              className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
            >Send</button>
          )}
        </div>
        <div className="mt-1 text-xs text-gray-500">Responses are generated via an LLM using transcript excerpts; include timestamps like [mm:ss].</div>
      </div>
    </div>
  );
}
