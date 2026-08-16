import { lvglHeader } from "./header.ts";
import { encodePixelsRGB, encodePixelsRGBA } from "./rgb565.ts";
import { msg, u } from "./protobuf.ts";
import { TRAILER, MAX_IMAGE_COUNT, MAX_LAYOUT_BYTES } from "@shared/constants.ts";
import {
  imageElement, pictureSetElement, digitsElement,
  animationElement, vectorHandElement, bitmapHandElement,
} from "./elements.ts";
import type { WatchfaceDocument, WatchfaceElement, AssetImage } from "@shared/types.ts";

export interface EncodedImage {
  cf: number;
  w: number;
  h: number;
  data: Uint8Array;   // pixels only (no header)
}

export function encodeImage(asset: AssetImage): EncodedImage {
  if (asset.cf === 5) {
    return {
      cf: 5, w: asset.width, h: asset.height,
      data: asset.pixels,
    };
  }
  return {
    cf: 4, w: asset.width, h: asset.height,
    data: asset.pixels,
  };
}

export function encodeFromRGBA(
  rgba: Uint8Array, w: number, h: number, alpha: boolean,
): EncodedImage {
  return {
    cf: alpha ? 5 : 4, w, h,
    data: alpha ? encodePixelsRGBA(rgba, w, h) : encodePixelsRGB(rgba, w, h),
  };
}

function buildImageBlob(img: EncodedImage): Uint8Array {
  const header = lvglHeader(img.w, img.h, img.cf);
  return new Uint8Array([...header, ...img.data]);
}

function elementToProtobuf(el: WatchfaceElement, doc: WatchfaceDocument): Uint8Array {
  switch (el.kind) {
    case "background": {
      const idx = assetIndex(doc, el.assetId);
      return imageElement(idx);
    }
    case "image": {
      const idx = assetIndex(doc, el.assetId);
      return imageElement(idx, el.x, el.y);
    }
    case "digits": {
      const glyphs = el.assetIds.map((id) => assetIndex(doc, id));
      const suffix = el.suffixAssetId ? assetIndex(doc, el.suffixAssetId) : undefined;
      return digitsElement(
        glyphs, el.x, el.y, el.source, el.w, el.h,
        el.cf, el.align, suffix,
      );
    }
    case "pictureSet": {
      const indices = el.assetIds.map((id) => assetIndex(doc, id));
      return pictureSetElement(indices, el.x, el.y, el.type);
    }
    case "animation": {
      const frames = el.assetIds.map((id) => assetIndex(doc, id));
      return animationElement(frames, el.x, el.y, el.periodMs);
    }
    case "vectorHand": {
      return vectorHandElement(
        el.canvas, el.points, el.circles,
        el.source, el.range, el.fillColor, el.arcColor,
      );
    }
    case "bitmapHand": {
      const idx = assetIndex(doc, el.assetId);
      return bitmapHandElement(idx, el.box, el.pivot, el.source, el.range);
    }
  }
}

function assetIndex(doc: WatchfaceDocument, assetId: string): number {
  const idx = doc.assets.findIndex((a) => a.id === assetId);
  if (idx < 0) throw new Error(`asset not found: ${assetId}`);
  return idx + 1;  // 1-based
}

function buildLayout(doc: WatchfaceDocument): Uint8Array {
  let layout = new Uint8Array();
  for (const el of doc.elements) {
    layout = new Uint8Array([...layout, ...elementToProtobuf(el, doc)]);
  }
  layout = new Uint8Array([...layout, ...u(5, 1)]);  // version = 1
  return layout;
}

export interface AssembleResult {
  bin: Uint8Array;
  imageCount: number;
  layoutBytes: number;
  warnings: string[];
}

export function assemble(
  doc: WatchfaceDocument,
  thumbnail: EncodedImage,
): AssembleResult {
  const warnings: string[] = [];

  const blobs: EncodedImage[] = [];
  const assetBlobs: EncodedImage[] = [];

  for (const asset of doc.assets) {
    assetBlobs.push(encodeImage(asset));
  }

  blobs.push(thumbnail);
  blobs.push(...assetBlobs);

  const imageCount = blobs.length;
  const cnt = imageCount * 4;

  if (imageCount > MAX_IMAGE_COUNT) {
    warnings.push(`Image count ${imageCount} exceeds firmware limit ${MAX_IMAGE_COUNT}`);
  }

  const layout = buildLayout(doc);
  if (layout.length > MAX_LAYOUT_BYTES) {
    warnings.push(`Layout ${layout.length} bytes exceeds firmware limit ${MAX_LAYOUT_BYTES}`);
  }

  const tableEntries: number[] = [];
  const bodyChunks: Uint8Array[] = [];
  let cur = cnt * 4;

  for (const blob of blobs) {
    tableEntries.push(cur);
    const fullBlob = buildImageBlob(blob);
    bodyChunks.push(fullBlob);
    cur += fullBlob.length;
  }

  const table = new Uint8Array(tableEntries.length * 4);
  tableEntries.forEach((offset, i) => {
    table[i * 4] = offset & 0xff;
    table[i * 4 + 1] = (offset >> 8) & 0xff;
    table[i * 4 + 2] = (offset >> 16) & 0xff;
    table[i * 4 + 3] = (offset >> 24) & 0xff;
  });

  const body = new Uint8Array(bodyChunks.reduce((sum, c) => sum + c.length, 0));
  let offset = 0;
  for (const chunk of bodyChunks) {
    body.set(chunk, offset);
    offset += chunk.length;
  }

  const off1 = 20;
  const off2 = off1 + buildImageBlob(thumbnail).length;
  const off3 = off2 + table.length + body.length;

  const header = new Uint8Array(20);
  const setU32 = (i: number, val: number) => {
    header[i * 4] = val & 0xff;
    header[i * 4 + 1] = (val >> 8) & 0xff;
    header[i * 4 + 2] = (val >> 16) & 0xff;
    header[i * 4 + 3] = (val >> 24) & 0xff;
  };
  setU32(0, off1);
  setU32(1, off2);
  setU32(2, cnt);
  setU32(3, off3);
  setU32(4, layout.length);

  const thumbBlob = buildImageBlob(thumbnail);

  const bin = new Uint8Array([
    ...header,
    ...thumbBlob,
    ...table,
    ...body,
    ...layout,
    ...TRAILER,
  ]);

  return { bin, imageCount, layoutBytes: layout.length, warnings };
}
