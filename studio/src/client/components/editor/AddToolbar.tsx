import { useState } from "react";
import { useEditor } from "../../lib/store/editor.ts";
import type { WatchfaceElement } from "@shared/types.ts";

const TEMPLATES: { kind: string; label: string; icon: string; create: () => WatchfaceElement }[] = [
  {
    kind: "background",
    label: "Background",
    icon: "BG",
    create: () => ({
      kind: "background", id: crypto.randomUUID(), name: "Background", assetId: "",
    }),
  },
  {
    kind: "image",
    label: "Image",
    icon: "IMG",
    create: () => ({
      kind: "image", id: crypto.randomUUID(), name: "Image", assetId: "", x: 50, y: 50,
    }),
  },
  {
    kind: "digits",
    label: "Digits",
    icon: "123",
    create: () => ({
      kind: "digits", id: crypto.randomUUID(), name: "Digits",
      assetIds: [], source: 12, x: 100, y: 100, align: 1, w: 52, h: 82, cf: 5,
    }),
  },
  {
    kind: "pictureSet",
    label: "Picture Set",
    icon: "PS",
    create: () => ({
      kind: "pictureSet", id: crypto.randomUUID(), name: "Picture Set",
      assetIds: [], type: 52, x: 150, y: 150,
    }),
  },
  {
    kind: "animation",
    label: "Animation",
    icon: "ANI",
    create: () => ({
      kind: "animation", id: crypto.randomUUID(), name: "Animation",
      assetIds: [], x: 50, y: 50, periodMs: 200,
    }),
  },
  {
    kind: "vectorHand",
    label: "Vector Hand",
    icon: "VH",
    create: () => ({
      kind: "vectorHand", id: crypto.randomUUID(), name: "Vector Hand",
      canvas: { x: 0, y: 0, w: 368, h: 448 },
      points: [
        { x: 180, y: 180 }, { x: 190, y: 220 }, { x: 180, y: 240 }, { x: 170, y: 220 },
      ],
      circles: [{ cx: 180, cy: 224, r: 20, start: 0, end: 360 }],
      source: 150, range: 360,
      fillColor: { r: 255, g: 255, b: 255 },
      arcColor: { r: 255, g: 255, b: 255 },
    }),
  },
  {
    kind: "bitmapHand",
    label: "Bitmap Hand",
    icon: "BH",
    create: () => ({
      kind: "bitmapHand", id: crypto.randomUUID(), name: "Bitmap Hand",
      assetId: "",
      box: { x: 84, y: 64, w: 200, h: 320 },
      pivot: { x: 100, y: 160 },
      source: 150, range: 360,
    }),
  },
];

export function AddToolbar() {
  const { addElement } = useEditor();
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-center gap-2 rounded-md bg-indigo-600 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14"/></svg>
        Add Element
      </button>
      {open && (
        <div className="absolute bottom-full left-0 z-10 mb-1 w-56 rounded-lg border border-zinc-700 bg-zinc-900 p-1 shadow-xl">
          {TEMPLATES.map((t) => (
            <button
              key={t.kind}
              onClick={() => {
                addElement(t.create());
                setOpen(false);
              }}
              className="flex w-full items-center gap-3 rounded px-3 py-2 text-left text-sm text-zinc-300 hover:bg-zinc-800"
            >
              <span className="w-8 text-center text-xs font-bold text-indigo-400">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
