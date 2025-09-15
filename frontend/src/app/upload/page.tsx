"use client";

import { uploadVideo } from "@/lib/api";
import { useUploadStore } from "@/stores/upload";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

export default function UploadPage() {
  const router = useRouter();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const { status, setStatus, setResult, setError: setStoreError } = useUploadStore();

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    setError(null);
    setDuration(null);
    setFile(f);
    if (f) {
      const url = URL.createObjectURL(f);
      setPreviewUrl(url);
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.load();
        }
      }, 0);
    } else {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
  };

  const onLoadedMetadata = () => {
    if (videoRef.current) {
      const d = videoRef.current.duration;
      if (!Number.isNaN(d) && Number.isFinite(d)) {
        setDuration(d);
      }
    }
  };

  const onUpload = async () => {
    setError(null);
    if (!file) {
      setError("Please choose a file");
      return;
    }
    if (duration && duration > 180) {
      setError("Video is longer than 3 minutes (client-side check)");
      return;
    }
    try {
      setStatus("uploading");
      const res = await uploadVideo(file);
      setStatus("processing");
      if (res?.status === "ready") {
        setResult(res.id, res.title);
        router.push(`/video/${res.id}`);
        return;
      }
      setStoreError("Processing did not complete successfully");
      setError("Processing did not complete successfully");
      setStatus("error");
    } catch (e: any) {
      const msg = e?.message || "Upload failed";
      setStoreError(msg);
      setError(msg);
      setStatus("error");
    }
  };

  const renderProgress = () => {
    if (status !== "processing" && status !== "uploading") return null;
    const label = status === "uploading" ? "Uploading..." : "Processing...";
    return (
      <div className="rounded border p-4 bg-white/60">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm text-gray-700">{label}</div>
          <div className="text-xs text-gray-500">{status.toUpperCase()}</div>
        </div>
        <div className="w-full h-2 bg-gray-200 rounded">
          <div className="h-2 bg-black rounded" style={{ width: `100%`, opacity: 0.2 }} />
        </div>
      </div>
    );
  };

  const [isDragging, setIsDragging] = useState(false);
  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) {
      const dt = new DataTransfer();
      dt.items.add(f);
      const fake = { target: { files: dt.files } } as unknown as React.ChangeEvent<HTMLInputElement>;
      onFileChange(fake);
    }
  };

  const primaryLabel = !file ? "Choose or drop a video" : status === "uploading" ? "Uploading..." : status === "processing" ? "Processing..." : "Upload & process";

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50">
      <div className="max-w-2xl mx-auto w-full py-10 px-4">
        <div className="mb-6">
          <h1 className="text-3xl font-semibold">Upload a video</h1>
          <p className="text-gray-600 mt-2">MP4, WebM, or MOV. Max length 3 minutes.</p>
        </div>

        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          className={`rounded-xl border bg-white p-5 shadow-sm transition ${isDragging ? "border-black ring-2 ring-black/10" : "border-gray-200"}`}
        >
          <div className="space-y-4">
            <label className="block">
              <span className="sr-only">Choose video</span>
              <input
                type="file"
                accept="video/mp4,video/webm,video/quicktime"
                onChange={onFileChange}
                className="hidden"
                id="video-input"
              />
              <button
                onClick={() => document.getElementById("video-input")?.click()}
                type="button"
                className="w-full border border-gray-300 rounded-md px-4 py-3 text-sm hover:bg-gray-50 transition"
                disabled={status === "uploading" || status === "processing"}
              >
                {file ? `Selected: ${file.name}` : "Click to select a file or drag & drop here"}
              </button>
            </label>

            {previewUrl && (
              <div className="rounded border overflow-hidden">
                <video
                  ref={videoRef}
                  src={previewUrl}
                  onLoadedMetadata={onLoadedMetadata}
                  controls
                  className="w-full max-h-80"
                />
                <div className="text-xs text-gray-500 px-2 py-1">Client duration: {duration ? duration.toFixed(1) : "?"}s</div>
              </div>
            )}

            {error && <div className="text-red-600 text-sm">{error}</div>}

            <div className="flex items-center gap-3">
              <button
                onClick={onUpload}
                className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
                disabled={!file || status === "uploading" || status === "processing"}
              >
                {primaryLabel}
              </button>
              {file && status === "idle" && (
                <span className="text-xs text-gray-500">Ready to upload</span>
              )}
            </div>

            {renderProgress()}

            <div className="text-xs text-gray-500">Tip: Keep your video concise and clear narration for best results.</div>
          </div>
        </div>
      </div>
    </div>
  );
}
