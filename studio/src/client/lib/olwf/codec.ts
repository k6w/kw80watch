export function varint(v: number): Uint8Array {
  if (v < 0) throw new Error(`varint cannot be negative: ${v}`);
  const bytes: number[] = [];
  let n = v;
  while (n >= 0x80) {
    bytes.push((n & 0x7f) | 0x80);
    n >>>= 7;
  }
  bytes.push(n);
  return new Uint8Array(bytes);
}

export function tag(field: number, wireType: number): Uint8Array {
  return varint((field << 3) | wireType);
}

export function msg(field: number, payload: Uint8Array): Uint8Array {
  return new Uint8Array([...tag(field, 2), ...varint(payload.length), ...payload]);
}

export function u(field: number, value: number): Uint8Array {
  return new Uint8Array([...tag(field, 0), ...varint(value)]);
}

export function bytesField(field: number, value: number[] | Uint8Array): Uint8Array {
  return msg(field, value instanceof Uint8Array ? value : new Uint8Array(value));
}

export function lvglHeader(w: number, h: number, cf: number = 4): Uint8Array {
  const header = ((w << 10) | (h << 21)) + cf;
  return new Uint8Array([
    header & 0xff,
    (header >> 8) & 0xff,
    (header >> 16) & 0xff,
    (header >> 24) & 0xff,
  ]);
}

const DITHER_R = new Uint8Array([
  1, 7, 3, 5, 0, 8, 2, 6, 7, 1, 5, 3, 8, 0, 6, 2,
  3, 5, 0, 8, 2, 6, 1, 7, 5, 3, 8, 0, 6, 2, 7, 1,
  0, 8, 2, 6, 1, 7, 3, 5, 8, 0, 6, 2, 7, 1, 5, 3,
  2, 6, 1, 7, 3, 5, 0, 8, 6, 2, 7, 1, 5, 3, 8, 0,
]);
const DITHER_G = new Uint8Array([
  1, 3, 2, 2, 3, 1, 2, 2, 2, 2, 0, 4, 2, 2, 4, 0,
  3, 1, 2, 2, 1, 3, 2, 2, 2, 2, 4, 0, 2, 2, 0, 4,
  1, 3, 2, 2, 3, 1, 2, 2, 2, 2, 0, 4, 2, 2, 4, 0,
  3, 1, 2, 2, 1, 3, 2, 2, 2, 2, 4, 0, 2, 2, 0, 4,
]);
const DITHER_B = new Uint8Array([
  5, 3, 8, 0, 6, 2, 7, 1, 3, 5, 0, 8, 2, 6, 1, 7,
  8, 0, 6, 2, 7, 1, 5, 3, 0, 8, 2, 6, 1, 7, 3, 5,
  6, 2, 7, 1, 5, 3, 8, 0, 2, 6, 1, 7, 3, 5, 0, 8,
  7, 1, 5, 3, 8, 0, 6, 2, 1, 7, 3, 5, 0, 8, 2, 6,
]);

const clamp = (v: number) => (v < 0 ? 0 : v > 255 ? 255 : v);

export function encodePixelsRGB(rgba: Uint8Array, w: number, h: number): Uint8Array {
  const out = new Uint8Array(w * h * 2);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const di = ((y & 7) << 3) + (x & 7);
      const si = (y * w + x) * 4;
      const red = clamp(rgba[si] + DITHER_R[di]);
      const green = clamp(rgba[si + 1] + DITHER_G[di]);
      const blue = clamp(rgba[si + 2] + DITHER_B[di]);
      const v =
        ((blue >> 3) & 0x1f) |
        (((green >> 2) & 0x3f) << 5) |
        (((red >> 3) & 0x1f) << 11);
      const oi = (y * w + x) * 2;
      out[oi] = (v >> 8) & 0xff;
      out[oi + 1] = v & 0xff;
    }
  }
  return out;
}

export function encodePixelsRGBA(rgba: Uint8Array, w: number, h: number): Uint8Array {
  const out = new Uint8Array(w * h * 3);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const di = ((y & 7) << 3) + (x & 7);
      const si = (y * w + x) * 4;
      const red = clamp(rgba[si] + DITHER_R[di]);
      const green = clamp(rgba[si + 1] + DITHER_G[di]);
      const blue = clamp(rgba[si + 2] + DITHER_B[di]);
      const v =
        ((blue >> 3) & 0x1f) |
        (((green >> 2) & 0x3f) << 5) |
        (((red >> 3) & 0x1f) << 11);
      const oi = (y * w + x) * 3;
      out[oi] = (v >> 8) & 0xff;
      out[oi + 1] = v & 0xff;
      out[oi + 2] = rgba[si + 3];
    }
  }
  return out;
}
