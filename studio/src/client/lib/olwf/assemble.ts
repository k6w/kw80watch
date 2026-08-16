import {
  varint, tag, msg, u as uField, bytesField,
  lvglHeader, encodePixelsRGB, encodePixelsRGBA,
} from "./codec.ts";
import type { WatchfaceDocument, WatchfaceElement, Colour, Point, Circle, Rect } from "@shared/types.ts";
import { SCREEN_W, SCREEN_H, THUMB_W, THUMB_H, TRAILER, MAX_IMAGE_COUNT, MAX_LAYOUT_BYTES } from "@shared/constants.ts";

function pos(x: number, y: number): Uint8Array {
  return msg(1, new Uint8Array([...uField(1, x), ...uField(2, y)]));
}

function rectMsg(r: Rect): Uint8Array {
  let payload = new Uint8Array();
  if (r.x) payload = new Uint8Array([...payload, ...uField(1, r.x)]);
  if (r.y) payload = new Uint8Array([...payload, ...uField(2, r.y)]);
  payload = new Uint8Array([...payload, ...uField(3, r.w), ...uField(4, r.h)]);
  return msg(1, payload);
}

function positionMsg(p: Point): Uint8Array {
  return msg(2, new Uint8Array([...uField(1, p.x), ...uField(2, p.y)]));
}

function colourMsg(field: number, c: Colour): Uint8Array {
  return msg(field, new Uint8Array([...uField(1, c.r), ...uField(2, c.g), ...uField(3, c.b)]));
}

function circleToMsg(c: Circle): Uint8Array {
  let p = positionMsg({ x: c.cx, y: c.cy });
  p = new Uint8Array([...p, ...uField(2, c.r)]);
  if (c.start) p = new Uint8Array([...p, ...uField(3, c.start)]);
  if (c.end < 360) p = new Uint8Array([...p, ...uField(4, c.end)]);
  return p;
}

function assetIndex(doc: WatchfaceDocument, assetId: string): number {
  const idx = doc.assets.findIndex((a) => a.id === assetId);
  if (idx < 0) throw new Error(`asset not found: ${assetId}`);
  return idx + 1;
}

function elementToProto(el: WatchfaceElement, doc: WatchfaceDocument): Uint8Array {
  switch (el.kind) {
    case "background": {
      return msg(1, msg(4, new Uint8Array([...uField(1, assetIndex(doc, el.assetId)), ...msg(2, new Uint8Array())])));
    }
    case "image": {
      return msg(1, msg(4, new Uint8Array([...uField(1, assetIndex(doc, el.assetId)), ...pos(el.x, el.y)])));
    }
    case "digits": {
      const glyphs = el.assetIds.map((id) => assetIndex(doc, id));
      let inner = new Uint8Array([...bytesField(1, glyphs), ...msg(3, pos(el.x, el.y))]);
      if (el.align) inner = new Uint8Array([...inner, ...uField(4, el.align)]);
      inner = new Uint8Array([...inner, ...uField(5, el.source)]);
      if (el.suffixAssetId) inner = new Uint8Array([...inner, ...uField(6, assetIndex(doc, el.suffixAssetId))]);
      inner = new Uint8Array([...inner, ...uField(21, el.w), ...uField(22, el.h), ...uField(23, el.cf)]);
      return msg(1, msg(6, inner));
    }
    case "pictureSet": {
      const indices = el.assetIds.map((id) => assetIndex(doc, id));
      return msg(1, msg(5, new Uint8Array([
        ...bytesField(1, indices),
        ...msg(2, pos(el.x, el.y)),
        ...uField(3, el.type),
      ])));
    }
    case "animation": {
      const frames = el.assetIds.map((id) => assetIndex(doc, id));
      return msg(1, msg(20, new Uint8Array([
        ...bytesField(1, frames),
        ...msg(2, pos(el.x, el.y)),
        ...uField(3, el.periodMs),
        ...uField(5, 1),
      ])));
    }
    case "vectorHand": {
      let inner = rectMsg(el.canvas);
      for (const p of el.points) inner = new Uint8Array([...inner, ...positionMsg(p)]);
      for (const c of el.circles) inner = new Uint8Array([...inner, ...msg(3, circleToMsg(c))]);
      inner = new Uint8Array([...inner, ...uField(5, el.range), ...uField(6, el.source)]);
      inner = new Uint8Array([...inner, ...colourMsg(7, el.fillColor), ...colourMsg(8, el.arcColor)]);
      return msg(1, msg(23, inner));
    }
    case "bitmapHand": {
      const idx = assetIndex(doc, el.assetId);
      let inner = new Uint8Array([
        ...uField(1, idx), ...msg(2, rectMsg(el.box)),
        ...msg(3, pos(el.pivot.x, el.pivot.y)),
      ]);
      inner = new Uint8Array([...inner, ...uField(5, el.range), ...uField(6, el.source)]);
      return msg(1, msg(8, inner));
    }
  }
}

function buildLayout(doc: WatchfaceDocument): Uint8Array {
  let layout = new Uint8Array();
  for (const el of doc.elements) {
    layout = new Uint8Array([...layout, ...elementToProto(el, doc)]);
  }
  return new Uint8Array([...layout, ...uField(5, 1)]);
}

function u32(v: number): Uint8Array {
  return new Uint8Array([v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff, (v >>> 24) & 0xff]);
}

export interface AssembleOptions {
  thumbnailRGBA?: Uint8Array;
}

export function assembleBin(doc: WatchfaceDocument, thumbnailRGBA: Uint8Array): Uint8Array {
  const thumbPixels = encodePixelsRGB(thumbnailRGBA, THUMB_W, THUMB_H);
  const thumbBlob = new Uint8Array([...lvglHeader(THUMB_W, THUMB_H, 4), ...thumbPixels]);

  const assetBlobs: Uint8Array[] = doc.assets.map((a) =>
    new Uint8Array([...lvglHeader(a.width, a.height, a.cf), ...a.pixels]),
  );

  const blobs = [thumbBlob, ...assetBlobs];
  const imageCount = blobs.length;
  const cnt = imageCount * 4;

  if (imageCount > MAX_IMAGE_COUNT) {
    throw new Error(`Too many images: ${imageCount} > ${MAX_IMAGE_COUNT}`);
  }

  const layout = buildLayout(doc);
  if (layout.length > MAX_LAYOUT_BYTES) {
    throw new Error(`Layout too large: ${layout.length} > ${MAX_LAYOUT_BYTES}`);
  }

  const tableEntries: number[] = [];
  let cur = cnt * 4;
  for (const blob of blobs) {
    tableEntries.push(cur);
    cur += blob.length;
  }

  const table = new Uint8Array(tableEntries.length * 4);
  tableEntries.forEach((offset, i) => {
    table[i * 4] = offset & 0xff;
    table[i * 4 + 1] = (offset >> 8) & 0xff;
    table[i * 4 + 2] = (offset >> 16) & 0xff;
    table[i * 4 + 3] = (offset >> 24) & 0xff;
  });

  const body = new Uint8Array(blobs.reduce((s, b) => s + b.length, 0));
  let off = 0;
  for (const blob of blobs) { body.set(blob, off); off += blob.length; }

  const off1 = 20;
  const off2 = off1 + thumbBlob.length;
  const off3 = off2 + table.length + body.length;

  const header = new Uint8Array([...u32(off1), ...u32(off2), ...u32(cnt), ...u32(off3), ...u32(layout.length)]);

  return new Uint8Array([...header, ...thumbBlob, ...table, ...body, ...layout, ...TRAILER]);
}
