import { create } from "zustand";
import type {
  WatchfaceDocument, WatchfaceElement, AssetImage, SimData as _SD,
} from "@shared/types.ts";
import { SCREEN_W, SCREEN_H } from "@shared/constants.ts";

const DEFAULT_SIM = {
  hour: 10, minute: 8, second: 0,
  steps: 6043, heartRate: 72, calories: 342,
  temperature: 22, battery: 80,
  dayOfMonth: 9, month: 8, weekday: 6, weather: 1,
};

interface EditorState {
  doc: WatchfaceDocument;
  selectedId: string | null;
  sim: typeof DEFAULT_SIM;
  zoom: number;
  showGrid: boolean;
  showMask: boolean;
  history: WatchfaceDocument[];
  historyIndex: number;
  projectId: string | null;

  setProjectId: (id: string) => void;
  loadDoc: (doc: WatchfaceDocument) => void;
  updateDoc: (updater: (doc: WatchfaceDocument) => WatchfaceDocument) => void;
  undo: () => void;
  redo: () => void;

  addElement: (el: WatchfaceElement) => void;
  removeElement: (id: string) => void;
  updateElement: (id: string, patch: Partial<WatchfaceElement>) => void;
  reorderElement: (id: string, dir: "up" | "down") => void;
  duplicateElement: (id: string) => void;

  selectElement: (id: string | null) => void;

  setSim: (patch: Partial<typeof DEFAULT_SIM>) => void;

  setZoom: (z: number) => void;
  toggleGrid: () => void;
  toggleMask: () => void;
}

const emptyDoc: WatchfaceDocument = {
  version: 1,
  elements: [],
  assets: [],
};

function pushHistory(state: EditorState): Partial<EditorState> {
  const newHistory = state.history.slice(0, state.historyIndex + 1);
  newHistory.push(state.doc);
  return {
    history: newHistory,
    historyIndex: newHistory.length - 1,
  };
}

export const useEditor = create<EditorState>((set, get) => ({
  doc: emptyDoc,
  selectedId: null,
  sim: DEFAULT_SIM,
  zoom: 1,
  showGrid: false,
  showMask: true,
  history: [emptyDoc],
  historyIndex: 0,
  projectId: null,

  setProjectId: (id) => set({ projectId: id }),

  loadDoc: (doc) => set({ doc, history: [doc], historyIndex: 0 }),

  updateDoc: (updater) => {
    const state = get();
    const newDoc = updater(state.doc);
    set({ doc: newDoc, ...pushHistory(state) });
  },

  undo: () => {
    const { history, historyIndex } = get();
    if (historyIndex > 0) {
      set({ doc: history[historyIndex - 1], historyIndex: historyIndex - 1 });
    }
  },

  redo: () => {
    const { history, historyIndex } = get();
    if (historyIndex < history.length - 1) {
      set({ doc: history[historyIndex + 1], historyIndex: historyIndex + 1 });
    }
  },

  addElement: (el) => {
    get().updateDoc((doc) => ({ ...doc, elements: [...doc.elements, el] }));
    set({ selectedId: el.id });
  },

  removeElement: (id) => {
    get().updateDoc((doc) => ({
      ...doc,
      elements: doc.elements.filter((e) => e.id !== id),
    }));
    if (get().selectedId === id) set({ selectedId: null });
  },

  updateElement: (id, patch) => {
    get().updateDoc((doc) => ({
      ...doc,
      elements: doc.elements.map((e) =>
        e.id === id ? ({ ...e, ...patch } as WatchfaceElement) : e
      ),
    }));
  },

  reorderElement: (id, dir) => {
    get().updateDoc((doc) => {
      const idx = doc.elements.findIndex((e) => e.id === id);
      if (idx < 0) return doc;
      const swap = dir === "up" ? idx + 1 : idx - 1;
      if (swap < 0 || swap >= doc.elements.length) return doc;
      const elements = [...doc.elements];
      [elements[idx], elements[swap]] = [elements[swap], elements[idx]];
      return { ...doc, elements };
    });
  },

  duplicateElement: (id) => {
    const { doc } = get();
    const el = doc.elements.find((e) => e.id === id);
    if (!el) return;
    const clone = { ...el, id: crypto.randomUUID() } as WatchfaceElement;
    get().addElement(clone);
  },

  selectElement: (id) => set({ selectedId: id }),

  setSim: (patch) => set((state) => ({ sim: { ...state.sim, ...patch } })),

  setZoom: (z) => set({ zoom: z }),
  toggleGrid: () => set((s) => ({ showGrid: !s.showGrid })),
  toggleMask: () => set((s) => ({ showMask: !s.showMask })),
}));
