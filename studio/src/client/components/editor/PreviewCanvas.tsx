import { useEffect, useRef, useCallback } from "react";
import { useEditor } from "../../lib/store/editor.ts";
import { renderWatchface, preloadAsset } from "../../lib/render/render.ts";
import { SCREEN_W, SCREEN_H, SCREEN_R } from "@shared/constants.ts";
import type { SimData } from "@shared/sources.ts";

export function PreviewCanvas({ sim }: { sim: SimData }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { doc, selectedId, zoom, showMask, showGrid } = useEditor();

  useEffect(() => {
    Promise.all(doc.assets.filter((a) => a.sourceUrl).map((a) => preloadAsset(a.sourceUrl!)))
      .then(() => render());
  }, [doc, sim, selectedId, zoom, showMask, showGrid]);

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, SCREEN_W * zoom, SCREEN_H * zoom);
    ctx.save();
    ctx.scale(zoom, zoom);

    if (showMask) {
      ctx.save();
      ctx.beginPath();
      roundRectPath(ctx, 0, 0, SCREEN_W, SCREEN_H, SCREEN_R);
      ctx.clip();
    }

    renderWatchface(ctx, doc, sim, selectedId);

    if (showMask) ctx.restore();

    if (showGrid) {
      ctx.strokeStyle = "rgba(99, 102, 241, 0.1)";
      ctx.lineWidth = 0.5;
      for (let x = 0; x <= SCREEN_W; x += 20) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, SCREEN_H);
        ctx.stroke();
      }
      for (let y = 0; y <= SCREEN_H; y += 20) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(SCREEN_W, y);
        ctx.stroke();
      }
    }

    ctx.restore();
  }, [doc, sim, selectedId, zoom, showMask, showGrid]);

  return (
    <canvas
      ref={canvasRef}
      width={SCREEN_W * zoom}
      height={SCREEN_H * zoom}
      className="rounded-2xl border border-zinc-800 bg-black shadow-2xl"
      style={{ imageRendering: zoom > 1 ? "pixelated" : "auto" }}
    />
  );
}

function roundRectPath(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, r: number,
) {
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
