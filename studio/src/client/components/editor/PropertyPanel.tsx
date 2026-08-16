import { useState } from "react";
import { useEditor } from "../../lib/store/editor.ts";
import { NUMERIC_SOURCES, PICTURE_SET_TYPES, ROTATION_SOURCES } from "@shared/sources.ts";
import type { WatchfaceElement } from "@shared/types.ts";

export function PropertyPanel() {
  const { doc, selectedId, updateElement } = useEditor();
  const el = doc.elements.find((e) => e.id === selectedId);

  if (!el) {
    return (
      <div className="flex h-full items-center justify-center p-4 text-sm text-zinc-600">
        Select an element to edit properties
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="mb-4">
        <label className="mb-1 block text-xs text-zinc-500">Name</label>
        <input
          type="text"
          value={el.name}
          onChange={(e) => updateElement(el.id, { name: e.target.value } as any)}
          className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-2.5 py-1.5 text-sm text-white outline-none focus:border-indigo-500"
        />
      </div>

      <ElementProperties el={el} update={(patch) => updateElement(el.id, patch)} />
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <label className="mb-1 block text-xs text-zinc-500">{label}</label>
      {children}
    </div>
  );
}

function NumInput({
  value, onChange, step = 1,
}: { value: number; onChange: (v: number) => void; step?: number }) {
  return (
    <input
      type="number"
      value={value}
      step={step}
      onChange={(e) => onChange(parseInt(e.target.value) || 0)}
      className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-2.5 py-1.5 text-sm text-white outline-none focus:border-indigo-500"
    />
  );
}

function Select({
  value, options, onChange,
}: {
  value: number;
  options: { value: number; label: string }[];
  onChange: (v: number) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(parseInt(e.target.value))}
      className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-2.5 py-1.5 text-sm text-white outline-none focus:border-indigo-500"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}

function ColourInput({
  colour, onChange,
}: { colour: { r: number; g: number; b: number }; onChange: (c: { r: number; g: number; b: number }) => void }) {
  const hex = `#${[colour.r, colour.g, colour.b].map((v) => v.toString(16).padStart(2, "0")).join("")}`;
  return (
    <div className="flex gap-2">
      <input
        type="color"
        value={hex}
        onChange={(e) => {
          const h = e.target.value;
          onChange({
            r: parseInt(h.slice(1, 3), 16),
            g: parseInt(h.slice(3, 5), 16),
            b: parseInt(h.slice(5, 7), 16),
          });
        }}
        className="h-8 w-12 rounded border border-zinc-700 bg-zinc-800"
      />
      <span className="flex items-center text-xs text-zinc-500">{hex}</span>
    </div>
  );
}

function ElementProperties({
  el, update,
}: { el: WatchfaceElement; update: (patch: any) => void }) {
  switch (el.kind) {
    case "background":
      return <div className="text-xs text-zinc-600">Full-screen background image.</div>;

    case "image":
      return (
        <>
          <Field label="X"><NumInput value={el.x} onChange={(v) => update({ x: v })} /></Field>
          <Field label="Y"><NumInput value={el.y} onChange={(v) => update({ y: v })} /></Field>
        </>
      );

    case "digits":
      return (
        <>
          <Field label="Data Source">
            <Select
              value={el.source}
              options={NUMERIC_SOURCES.map((s) => ({ value: s.id, label: s.label }))}
              onChange={(v) => update({ source: v })}
            />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="X"><NumInput value={el.x} onChange={(v) => update({ x: v })} /></Field>
            <Field label="Y"><NumInput value={el.y} onChange={(v) => update({ y: v })} /></Field>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Cell Width"><NumInput value={el.w} onChange={(v) => update({ w: v })} /></Field>
            <Field label="Cell Height"><NumInput value={el.h} onChange={(v) => update({ h: v })} /></Field>
          </div>
          <Field label="Alignment">
            <div className="flex gap-1">
              {([0, 1, 2] as const).map((a) => (
                <button
                  key={a}
                  onClick={() => update({ align: a })}
                  className={`flex-1 rounded py-1.5 text-xs ${
                    el.align === a ? "bg-indigo-600 text-white" : "bg-zinc-800 text-zinc-400"
                  }`}
                >
                  {a === 0 ? "Left" : a === 1 ? "Center" : "Right"}
                </button>
              ))}
            </div>
          </Field>
        </>
      );

    case "pictureSet":
      return (
        <>
          <Field label="Type">
            <Select
              value={el.type}
              options={PICTURE_SET_TYPES.map((t) => ({ value: t.id, label: `${t.label} (${t.states} states)` }))}
              onChange={(v) => update({ type: v })}
            />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="X"><NumInput value={el.x} onChange={(v) => update({ x: v })} /></Field>
            <Field label="Y"><NumInput value={el.y} onChange={(v) => update({ y: v })} /></Field>
          </div>
          <div className="text-xs text-zinc-600">{el.assetIds.length} state images assigned.</div>
        </>
      );

    case "animation":
      return (
        <>
          <div className="grid grid-cols-2 gap-2">
            <Field label="X"><NumInput value={el.x} onChange={(v) => update({ x: v })} /></Field>
            <Field label="Y"><NumInput value={el.y} onChange={(v) => update({ y: v })} /></Field>
          </div>
          <Field label="Frame Period (ms)">
            <NumInput value={el.periodMs} onChange={(v) => update({ periodMs: v })} step={50} />
          </Field>
          <div className="text-xs text-zinc-600">{el.assetIds.length} frames assigned.</div>
        </>
      );

    case "vectorHand":
      return (
        <>
          <Field label="Rotation Source">
            <Select
              value={el.source}
              options={ROTATION_SOURCES.map((s) => ({ value: s.id, label: s.label }))}
              onChange={(v) => update({ source: v })}
            />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Canvas X"><NumInput value={el.canvas.x} onChange={(v) => update({ canvas: { ...el.canvas, x: v } })} /></Field>
            <Field label="Canvas Y"><NumInput value={el.canvas.y} onChange={(v) => update({ canvas: { ...el.canvas, y: v } })} /></Field>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Canvas W"><NumInput value={el.canvas.w} onChange={(v) => update({ canvas: { ...el.canvas, w: v } })} /></Field>
            <Field label="Canvas H"><NumInput value={el.canvas.h} onChange={(v) => update({ canvas: { ...el.canvas, h: v } })} /></Field>
          </div>
          <Field label="Fill Colour (Polygon)"><ColourInput colour={el.fillColor} onChange={(c) => update({ fillColor: c })} /></Field>
          <Field label="Arc Colour (Circles)"><ColourInput colour={el.arcColor} onChange={(c) => update({ arcColor: c })} /></Field>
          <Field label="Range"><NumInput value={el.range} onChange={(v) => update({ range: v })} /></Field>
          <div className="text-xs text-zinc-600">
            {el.points.length} points, {el.circles.length} circles
          </div>
        </>
      );

    case "bitmapHand":
      return (
        <>
          <Field label="Rotation Source">
            <Select
              value={el.source}
              options={ROTATION_SOURCES.map((s) => ({ value: s.id, label: s.label }))}
              onChange={(v) => update({ source: v })}
            />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Pivot X"><NumInput value={el.pivot.x} onChange={(v) => update({ pivot: { ...el.pivot, x: v } })} /></Field>
            <Field label="Pivot Y"><NumInput value={el.pivot.y} onChange={(v) => update({ pivot: { ...el.pivot, y: v } })} /></Field>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Box X"><NumInput value={el.box.x} onChange={(v) => update({ box: { ...el.box, x: v } })} /></Field>
            <Field label="Box Y"><NumInput value={el.box.y} onChange={(v) => update({ box: { ...el.box, y: v } })} /></Field>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Box W"><NumInput value={el.box.w} onChange={(v) => update({ box: { ...el.box, w: v } })} /></Field>
            <Field label="Box H"><NumInput value={el.box.h} onChange={(v) => update({ box: { ...el.box, h: v } })} /></Field>
          </div>
        </>
      );
  }
}
