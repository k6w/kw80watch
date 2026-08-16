import { useEditor } from "../../lib/store/editor.ts";
import type { WatchfaceElement } from "@shared/types.ts";

const KIND_ICONS: Record<string, string> = {
  background: "BG",
  image: "IMG",
  digits: "123",
  pictureSet: "PS",
  animation: "ANI",
  vectorHand: "VH",
  bitmapHand: "BH",
};

const KIND_COLORS: Record<string, string> = {
  background: "text-blue-400",
  image: "text-green-400",
  digits: "text-yellow-400",
  pictureSet: "text-purple-400",
  animation: "text-orange-400",
  vectorHand: "text-cyan-400",
  bitmapHand: "text-pink-400",
};

export function LayerPanel() {
  const { doc, selectedId, selectElement, removeElement, reorderElement, duplicateElement } = useEditor();

  const layers = [...doc.elements].reverse();

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-zinc-800 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
        Layers
      </div>
      <div className="flex-1 overflow-y-auto">
        {layers.length === 0 ? (
          <div className="p-4 text-sm text-zinc-600">No layers yet. Use + to add elements.</div>
        ) : (
          layers.map((el) => (
            <div
              key={el.id}
              onClick={() => selectElement(el.id)}
              className={`group flex cursor-pointer items-center gap-2 border-l-2 px-3 py-2 text-sm transition ${
                selectedId === el.id
                  ? "border-indigo-500 bg-zinc-800/50"
                  : "border-transparent hover:bg-zinc-800/30"
              }`}
            >
              <span className={`w-7 text-center text-xs font-bold ${KIND_COLORS[el.kind]}`}>
                {KIND_ICONS[el.kind]}
              </span>
              <span className="flex-1 truncate text-zinc-300">{el.name}</span>
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100">
                <button
                  onClick={(e) => { e.stopPropagation(); reorderElement(el.id, "up"); }}
                  className="rounded p-0.5 text-zinc-500 hover:text-white"
                  title="Move forward"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 15l-6-6-6 6"/></svg>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); reorderElement(el.id, "down"); }}
                  className="rounded p-0.5 text-zinc-500 hover:text-white"
                  title="Move backward"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 9l6 6 6-6"/></svg>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); duplicateElement(el.id); }}
                  className="rounded p-0.5 text-zinc-500 hover:text-white"
                  title="Duplicate"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); removeElement(el.id); }}
                  className="rounded p-0.5 text-red-500/70 hover:text-red-400"
                  title="Delete"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
