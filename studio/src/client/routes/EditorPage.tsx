import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useEditor } from "../lib/store/editor.ts";
import { PreviewCanvas } from "../components/editor/PreviewCanvas.tsx";
import { LayerPanel } from "../components/editor/LayerPanel.tsx";
import { PropertyPanel } from "../components/editor/PropertyPanel.tsx";
import { AddToolbar } from "../components/editor/AddToolbar.tsx";
import { DataSimulator } from "../components/editor/DataSimulator.tsx";
import { ConstraintBadge } from "../components/editor/ConstraintBadge.tsx";
import { assembleBin } from "../lib/olwf/assemble.ts";
import { uploadWatchface, isWebBluetoothSupported, type UploadProgress } from "../lib/ble/ota.ts";
import { SCREEN_W, SCREEN_H } from "@shared/constants.ts";

export function EditorPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const editor = useEditor();
  const [saving, setSaving] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [showExport, setShowExport] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    editor.setProjectId(projectId);
    fetch(`/api/projects/${projectId}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.project) {
          editor.loadDoc(JSON.parse(data.project.document || '{"version":1,"elements":[],"assets":[]}'));
        }
      });
  }, [projectId]);

  const save = useCallback(async () => {
    if (!projectId) return;
    setSaving(true);
    await fetch(`/api/projects/${projectId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "Untitled",
        document: JSON.stringify(editor.doc),
      }),
    });
    setSaving(false);
  }, [projectId, editor.doc]);

  const exportBin = useCallback(async () => {
    const canvas = document.createElement("canvas");
    canvas.width = SCREEN_W;
    canvas.height = SCREEN_H;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, SCREEN_W, SCREEN_H);

    const { renderWatchface } = await import("../lib/render/render.ts");
    renderWatchface(ctx, editor.doc, editor.sim, null);

    const thumbCanvas = document.createElement("canvas");
    thumbCanvas.width = 180;
    thumbCanvas.height = 219;
    const thumbCtx = thumbCanvas.getContext("2d")!;
    thumbCtx.drawImage(canvas, 0, 0, 180, 219);
    const thumbData = thumbCtx.getImageData(0, 0, 180, 219);

    const bin = assembleBin(editor.doc, new Uint8Array(thumbData.data.buffer));

    const blob = new Blob([bin], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "watchface.bin";
    a.click();
    URL.revokeObjectURL(url);
  }, [editor.doc, editor.sim]);

  const uploadToWatch = useCallback(async () => {
    if (!isWebBluetoothSupported()) {
      alert("Web Bluetooth is not supported in this browser. Use Chrome or Edge.");
      return;
    }
    try {
      const canvas = document.createElement("canvas");
      canvas.width = SCREEN_W;
      canvas.height = SCREEN_H;
      const ctx = canvas.getContext("2d")!;
      ctx.fillStyle = "#000";
      ctx.fillRect(0, 0, SCREEN_W, SCREEN_H);

      const { renderWatchface } = await import("../lib/render/render.ts");
      renderWatchface(ctx, editor.doc, editor.sim, null);

      const thumbCanvas = document.createElement("canvas");
      thumbCanvas.width = 180;
      thumbCanvas.height = 219;
      const thumbCtx = thumbCanvas.getContext("2d")!;
      thumbCtx.drawImage(canvas, 0, 0, 180, 219);
      const thumbData = thumbCtx.getImageData(0, 0, 180, 219);

      const bin = assembleBin(editor.doc, new Uint8Array(thumbData.data.buffer));
      await uploadWatchface(bin, setUploadProgress);
    } catch (e) {
      console.error(e);
      alert(`Upload failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setTimeout(() => setUploadProgress(null), 2000);
    }
  }, [editor.doc, editor.sim]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        editor.undo();
      } else if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.key === "z" && e.shiftKey))) {
        e.preventDefault();
        editor.redo();
      } else if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        save();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [editor, save]);

  return (
    <div className="flex h-screen flex-col bg-zinc-950">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-2">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate("/dashboard")}
            className="flex items-center gap-1 text-sm text-zinc-400 hover:text-white"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            Back
          </button>
          <span className="text-sm font-medium text-white">Untitled Watchface</span>
          {saving && <span className="text-xs text-zinc-500">Saving...</span>}
        </div>

        <ConstraintBadge />

        <div className="flex items-center gap-2">
          <button
            onClick={() => editor.setZoom(Math.max(0.5, editor.zoom - 0.25))}
            className="rounded p-1.5 text-zinc-400 hover:bg-zinc-800"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="M8 11h6M21 21l-4.35-4.35"/></svg>
          </button>
          <span className="w-10 text-center text-xs text-zinc-400">{Math.round(editor.zoom * 100)}%</span>
          <button
            onClick={() => editor.setZoom(Math.min(4, editor.zoom + 0.25))}
            className="rounded p-1.5 text-zinc-400 hover:bg-zinc-800"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="M11 8v6M8 11h6M21 21l-4.35-4.35"/></svg>
          </button>

          <div className="mx-1 h-5 w-px bg-zinc-800" />

          <button
            onClick={editor.toggleGrid}
            className={`rounded px-2 py-1 text-xs ${editor.showGrid ? "bg-indigo-600 text-white" : "bg-zinc-800 text-zinc-400"}`}
          >
            Grid
          </button>
          <button
            onClick={editor.toggleMask}
            className={`rounded px-2 py-1 text-xs ${editor.showMask ? "bg-indigo-600 text-white" : "bg-zinc-800 text-zinc-400"}`}
          >
            Mask
          </button>

          <div className="mx-1 h-5 w-px bg-zinc-800" />

          <button onClick={save} className="rounded-md bg-zinc-800 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-700">
            Save
          </button>
          <button onClick={exportBin} className="rounded-md bg-zinc-800 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-700">
            Export .bin
          </button>
          <button
            onClick={uploadToWatch}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500"
          >
            {uploadProgress ? `${uploadProgress.phase}...` : "Send to Watch"}
          </button>
        </div>
      </div>

      {/* Main editor area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar — Layers */}
        <div className="flex w-56 flex-col border-r border-zinc-800 bg-zinc-900/50">
          <LayerPanel />
          <div className="border-t border-zinc-800 p-3">
            <AddToolbar />
          </div>
        </div>

        {/* Centre — Canvas */}
        <div className="flex flex-1 items-center justify-center overflow-auto p-8">
          <div className="relative">
            <PreviewCanvas sim={editor.sim} />
            {uploadProgress && (
              <div className="absolute inset-0 flex items-center justify-center rounded-2xl bg-black/70">
                <div className="text-center">
                  <div className="mb-2 text-sm text-indigo-400">{uploadProgress.phase}</div>
                  <div className="h-2 w-48 overflow-hidden rounded-full bg-zinc-800">
                    <div
                      className="h-full rounded-full bg-indigo-500 transition-all"
                      style={{ width: `${uploadProgress.percent}%` }}
                    />
                  </div>
                  <div className="mt-2 text-xs text-zinc-500">
                    Piece {uploadProgress.piece} / {uploadProgress.totalPieces}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right sidebar — Properties + Sim */}
        <div className="flex w-72 flex-col border-l border-zinc-800 bg-zinc-900/50">
          <div className="border-b border-zinc-800 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Properties
          </div>
          <div className="flex-1 overflow-y-auto">
            <PropertyPanel />
          </div>
          <div className="border-t border-zinc-800 p-3">
            <DataSimulator />
          </div>
        </div>
      </div>
    </div>
  );
}
