import { msg, u, bytesField } from "./protobuf.ts";
import type {
  Colour, Point, Circle, Rect,
} from "@shared/types.ts";

function pos(x: number, y: number): Uint8Array {
  return msg(1, new Uint8Array([...u(1, x), ...u(2, y)]));
}

function rect(r: Rect): Uint8Array {
  let payload = new Uint8Array();
  if (r.x !== undefined) payload = new Uint8Array([...payload, ...u(1, r.x)]);
  if (r.y !== undefined) payload = new Uint8Array([...payload, ...u(2, r.y)]);
  payload = new Uint8Array([...payload, ...u(3, r.w), ...u(4, r.h)]);
  return msg(1, payload);
}

function position(p: Point): Uint8Array {
  return msg(2, new Uint8Array([...u(1, p.x), ...u(2, p.y)]));
}

function colourMsg(field: number, c: Colour): Uint8Array {
  return msg(field, new Uint8Array([...u(1, c.r), ...u(2, c.g), ...u(3, c.b)]));
}

function circleMsg(c: Circle): Uint8Array {
  let payload = position({ x: c.cx, y: c.cy });
  payload = new Uint8Array([...payload, ...u(2, c.r)]);
  if (c.start !== undefined) payload = new Uint8Array([...payload, ...u(3, c.start)]);
  if (c.end !== undefined) payload = new Uint8Array([...payload, ...u(4, c.end)]);
  return payload;
}

// f4 — Image
export function imageElement(index: number, x?: number, y?: number): Uint8Array {
  let inner = u(1, index);
  if (x !== undefined && y !== undefined) {
    inner = new Uint8Array([...inner, ...pos(x, y)]);
  } else {
    // empty position message = full screen (0,0) — matches Python wfbuild.background()
    inner = new Uint8Array([...inner, ...msg(2, new Uint8Array())]);
  }
  return msg(1, msg(4, inner));
}

// f5 — PictureSet
export function pictureSetElement(
  indices: number[],
  x: number,
  y: number,
  type: number,
): Uint8Array {
  const inner = new Uint8Array([
    ...bytesField(1, indices),
    ...msg(2, new Uint8Array([...u(1, x), ...u(2, y)])),
    ...u(3, type),
  ]);
  return msg(1, msg(5, inner));
}

// f6 — Digits
export function digitsElement(
  glyphs: number[],
  x: number,
  y: number,
  source: number,
  w: number,
  h: number,
  cf: number = 5,
  align?: number,
  suffix?: number,
): Uint8Array {
  let inner = new Uint8Array([
    ...bytesField(1, glyphs),
    ...msg(3, new Uint8Array([...u(1, x), ...u(2, y)])),
  ]);
  if (align !== undefined) inner = new Uint8Array([...inner, ...u(4, align)]);
  inner = new Uint8Array([...inner, ...u(5, source)]);
  if (suffix !== undefined) inner = new Uint8Array([...inner, ...u(6, suffix)]);
  inner = new Uint8Array([...inner, ...u(21, w), ...u(22, h), ...u(23, cf)]);
  return msg(1, msg(6, inner));
}

// f8 — BitmapHand
export function bitmapHandElement(
  index: number,
  box: Rect,
  pivot: Point,
  source: number,
  range: number = 360,
): Uint8Array {
  let inner = new Uint8Array([
    ...u(1, index),
    ...msg(2, rect(box)),
    ...msg(3, new Uint8Array([...u(1, pivot.x), ...u(2, pivot.y)])),
  ]);
  if (range !== undefined) inner = new Uint8Array([...inner, ...u(5, range)]);
  inner = new Uint8Array([...inner, ...u(6, source)]);
  return msg(1, msg(8, inner));
}

// f20 — Animation
export function animationElement(
  frames: number[],
  x: number,
  y: number,
  periodMs: number,
): Uint8Array {
  let inner = new Uint8Array([
    ...bytesField(1, frames),
    ...msg(2, new Uint8Array([...u(1, x), ...u(2, y)])),
    ...u(3, periodMs),
    ...u(5, 1),
  ]);
  return msg(1, msg(20, inner));
}

// f23 — VectorHand
export function vectorHandElement(
  canvas: Rect,
  points: Point[],
  circles: Circle[],
  source: number,
  range: number,
  fillColor: Colour,
  arcColor: Colour,
): Uint8Array {
  let inner = rect(canvas);
  for (const p of points) {
    inner = new Uint8Array([...inner, ...position(p)]);
  }
  for (const c of circles) {
    inner = new Uint8Array([...inner, ...msg(3, circleMsg(c))]);
  }
  if (range !== undefined) inner = new Uint8Array([...inner, ...u(5, range)]);
  inner = new Uint8Array([...inner, ...u(6, source)]);
  inner = new Uint8Array([...inner, ...colourMsg(7, fillColor)]);
  inner = new Uint8Array([...inner, ...colourMsg(8, arcColor)]);
  return msg(1, msg(23, inner));
}
