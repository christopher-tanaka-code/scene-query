import { create } from "zustand";

export interface MatchItem {
  timestamp: number;
  hhmmss: string;
  text: string;
  score: number;
  frameUrl?: string;
}

interface SearchState {
  query: string;
  loading: boolean;
  best?: MatchItem;
  alternatives: MatchItem[];
  error?: string;
  setQuery: (q: string) => void;
  setLoading: (b: boolean) => void;
  setResults: (best: MatchItem, alternatives: MatchItem[]) => void;
  setError: (e?: string) => void;
  reset: () => void;
}

export const useSearchStore = create<SearchState>((set) => ({
  query: "",
  loading: false,
  alternatives: [],
  setQuery: (q) => set({ query: q }),
  setLoading: (b) => set({ loading: b }),
  setResults: (best, alternatives) => set({ best, alternatives, loading: false, error: undefined }),
  setError: (e) => set({ error: e, loading: false }),
  reset: () => set({ query: "", loading: false, best: undefined, alternatives: [], error: undefined }),
}));
