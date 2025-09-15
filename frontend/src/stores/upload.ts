import { create } from "zustand";

export type UploadStatus = "idle" | "uploading" | "processing" | "ready" | "error";

type ProgressEvent = {
  type: "progress";
  stage: "transcribe" | "chunk" | "embed" | "index" | "ready" | "error";
  pct: number;
  message: string;
};

interface UploadState {
  status: UploadStatus;
  progressPct: number;
  progressStage?: ProgressEvent["stage"];
  progressMessage?: string;
  videoId?: number;
  title?: string;
  error?: string;
  setStatus: (s: UploadStatus) => void;
  setProgress: (evt: ProgressEvent) => void;
  setResult: (videoId: number, title: string) => void;
  setError: (msg: string) => void;
  reset: () => void;
}

export const useUploadStore = create<UploadState>((set) => ({
  status: "idle",
  progressPct: 0,
  setStatus: (s) => set({ status: s }),
  setProgress: (evt) => set({
    status: evt.stage === "ready" ? "ready" : evt.stage === "error" ? "error" : "processing",
    progressPct: evt.pct,
    progressStage: evt.stage,
    progressMessage: evt.message,
  }),
  setResult: (videoId, title) => set({ videoId, title, status: "ready", progressPct: 100 }),
  setError: (msg) => set({ status: "error", error: msg }),
  reset: () => set({ status: "idle", progressPct: 0, progressStage: undefined, progressMessage: undefined, videoId: undefined, title: undefined, error: undefined }),
}));
