import type { WatchfaceDocument, WatchfaceElement, AssetImage } from "@shared/types.ts";
import type { SimData } from "@shared/sources.ts";
import { SCREEN_W, SCREEN_H, SCREEN_R } from "@shared/constants.ts";
import {
  ROTATION_SOURCES, NUMERIC_SOURCES,
} from "@shared/sources.ts";

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, r: number,
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function drawRoundedMask(ctx: CanvasRenderingContext2D) {
  ctx.save();
  ctx.beginPath();
  roundRect(ctx, 0, 0, SCREEN_W, SCREEN_H, SCREEN_R);
  ctx.clip();
}

function drawAsset(
  ctx: CanvasRenderingContext2D,
  asset: AssetImage | undefined,
  x: number, y: number,
) {
  if (!asset || !asset.sourceUrl) return;
  // assets are drawn from their cached image URLs
  const img = getCachedImage(asset.sourceUrl);
  if (img) {
    ctx.drawImage(img, x, y, asset.width, asset.height);
  }
}

const imageCache = new Map<string, HTMLImageElement>();

function getCachedImage(url: string): HTMLImageElement | null {
  if (imageCache.has(url)) return imageCache.get(url)!;
  return null;
}

export function preloadAsset(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    if (imageCache.has(url)) {
      resolve(imageCache.get(url)!);
      return;
    }
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      imageCache.set(url, img);
      resolve(img);
    };
    img.onerror = reject;
    img.src = url;
  });
}

function getAsset(doc: WatchfaceDocument, id: string): AssetImage | undefined {
  return doc.assets.find((a) => a.id === id);
}

function formatNumber(value: number, source: number): string {
  switch (source) {
    case 12: return String(value % 12 || 12).padStart(2, "0");
    case 13: case 14: return String(value).padStart(2, "0");
    case 0: return String(value);
    case 17: return String(value).padStart(2, "0");
    default: return String(value);
  }
}

function getNumericValue(source: number, sim: SimData): number {
  switch (source) {
    case 0: return sim.steps;
    case 1: return sim.calories;
    case 2: return sim.heartRate;
    case 4: return sim.temperature;
    case 9: return sim.battery;
    case 12: return sim.hour;
    case 13: return sim.minute;
    case 14: return sim.second;
    case 17: return sim.dayOfMonth;
    case 51: return sim.month;
    default: return 0;
  }
}

function getPictureSetState(type: number, sim: SimData): number {
  switch (type) {
    case 50: return sim.hour < 12 ? 0 : 1;
    case 51: return sim.month - 1;
    case 52: return sim.weekday;
    case 54: return Math.min(10, Math.floor(sim.battery / 10));
    case 59: return Math.floor((sim.hour % 12) / 10);
    case 60: return (sim.hour % 12) % 10;
    case 61: return Math.floor(sim.minute / 10);
    case 62: return sim.minute % 10;
    case 70: return Math.floor(sim.dayOfMonth / 10);
    case 71: return sim.dayOfMonth % 10;
    case 181: return 1;
    case 248: return sim.weather;
    default: return 0;
  }
}

function getRotationAngle(sourceId: number, sim: SimData): number {
  const src = ROTATION_SOURCES.find((s) => s.id === sourceId);
  if (!src) return 0;
  return src.toAngle(sim);
}

function drawElement(
  ctx: CanvasRenderingContext2D,
  el: WatchfaceElement,
  doc: WatchfaceDocument,
  sim: SimData,
  selected: boolean,
) {
  switch (el.kind) {
    case "background": {
      const asset = getAsset(doc, el.assetId);
      if (asset) drawAsset(ctx, asset, 0, 0);
      break;
    }
    case "image": {
      const asset = getAsset(doc, el.assetId);
      if (asset) drawAsset(ctx, asset, el.x, el.y);
      break;
    }
    case "digits": {
      const value = getNumericValue(el.source, sim);
      const str = formatNumber(value, el.source);
      for (let i = 0; i < str.length; i++) {
        const digitIdx = parseInt(str[i]);
        const asset = getAsset(doc, el.assetIds[digitIdx]);
        if (!asset) continue;
        const x = el.x + i * el.w;
        drawAsset(ctx, asset, x, el.y);
      }
      if (el.suffixAssetId) {
        const suffix = getAsset(doc, el.suffixAssetId);
        if (suffix) {
          drawAsset(ctx, suffix, el.x + str.length * el.w, el.y);
        }
      }
      break;
    }
    case "pictureSet": {
      const stateIdx = getPictureSetState(el.type, sim);
      const assetId = el.assetIds[stateIdx];
      if (assetId) {
        const asset = getAsset(doc, assetId);
        if (asset) drawAsset(ctx, asset, el.x, el.y);
      }
      break;
    }
    case "animation": {
      // cycle through frames based on time
      const frameIdx = Math.floor(Date.now() / el.periodMs) % el.assetIds.length;
      const asset = getAsset(doc, el.assetIds[frameIdx]);
      if (asset) drawAsset(ctx, asset, el.x, el.y);
      break;
    }
    case "vectorHand": {
      const angle = getRotationAngle(el.source, sim) - 90;
      const cx = el.canvas.x + el.canvas.w / 2;
      const cy = el.canvas.y + el.canvas.h / 2;
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate((angle * Math.PI) / 180);

      // polygon
      if (el.points.length > 0) {
        ctx.fillStyle = `rgb(${el.fillColor.r}, ${el.fillColor.g}, ${el.fillColor.b})`;
        ctx.beginPath();
        for (let i = 0; i < el.points.length; i++) {
          const px = el.points[i].x - el.canvas.w / 2;
          const py = el.points[i].y - el.canvas.h / 2;
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.fill();
      }

      // circles (filled pie sectors)
      ctx.fillStyle = `rgb(${el.arcColor.r}, ${el.arcColor.g}, ${el.arcColor.b})`;
      for (const c of el.circles) {
        ctx.beginPath();
        if (c.start !== 0 || c.end < 360) {
          ctx.moveTo(c.cx - el.canvas.w / 2, c.cy - el.canvas.h / 2);
          ctx.arc(
            c.cx - el.canvas.w / 2,
            c.cy - el.canvas.h / 2,
            c.r,
            (c.start * Math.PI) / 180,
            (c.end * Math.PI) / 180,
          );
          ctx.closePath();
        } else {
          ctx.arc(
            c.cx - el.canvas.w / 2,
            c.cy - el.canvas.h / 2,
            c.r, 0, Math.PI * 2,
          );
        }
        ctx.fill();
      }
      ctx.restore();
      break;
    }
    case "bitmapHand": {
      const asset = getAsset(doc, el.assetId);
      if (!asset) break;
      const angle = getRotationAngle(el.source, sim) - 90;
      const ccx = el.box.x + el.box.w / 2;
      const ccy = el.box.y + el.box.h / 2;
      ctx.save();
      ctx.translate(ccx, ccy);
      ctx.rotate((angle * Math.PI) / 180);
      ctx.drawImage(
        getCachedImage(asset.sourceUrl!)!,
        -el.pivot.x, -el.pivot.y,
        asset.width, asset.height,
      );
      ctx.restore();
      break;
    }
  }

  if (selected) {
    drawSelectionBox(ctx, el);
  }
}

function drawSelectionBox(ctx: CanvasRenderingContext2D, el: WatchfaceElement) {
  ctx.save();
  ctx.strokeStyle = "#6366f1";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);

  let x = 0, y = 0, w = SCREEN_W, h = SCREEN_H;
  switch (el.kind) {
    case "image": x = el.x; y = el.y; break;
    case "digits": x = el.x; y = el.y; w = el.w * 2; h = el.h; break;
    case "pictureSet": case "animation": x = el.x; y = el.y; w = 52; h = 52; break;
    case "vectorHand": case "bitmapHand":
      x = (el as any).canvas?.x ?? (el as any).box?.x ?? 0;
      y = (el as any).canvas?.y ?? (el as any).box?.y ?? 0;
      w = (el as any).canvas?.w ?? (el as any).box?.w ?? SCREEN_W;
      h = (el as any).canvas?.h ?? (el as any).box?.h ?? SCREEN_H;
      break;
  }
  ctx.strokeRect(x - 1, y - 1, w + 2, h + 2);
  ctx.restore();
}

export function renderWatchface(
  ctx: CanvasRenderingContext2D,
  doc: WatchfaceDocument,
  sim: SimData,
  selectedId: string | null,
) {
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, SCREEN_W, SCREEN_H);

  for (const el of doc.elements) {
    drawElement(ctx, el, doc, sim, el.id === selectedId);
  }
}
