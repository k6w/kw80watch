export const DITHER_R = new Uint8Array([
  1, 7, 3, 5, 0, 8, 2, 6, 7, 1, 5, 3, 8, 0, 6, 2,
  3, 5, 0, 8, 2, 6, 1, 7, 5, 3, 8, 0, 6, 2, 7, 1,
  0, 8, 2, 6, 1, 7, 3, 5, 8, 0, 6, 2, 7, 1, 5, 3,
  2, 6, 1, 7, 3, 5, 0, 8, 6, 2, 7, 1, 5, 3, 8, 0,
]);

export const DITHER_G = new Uint8Array([
  1, 3, 2, 2, 3, 1, 2, 2, 2, 2, 0, 4, 2, 2, 4, 0,
  3, 1, 2, 2, 1, 3, 2, 2, 2, 2, 4, 0, 2, 2, 0, 4,
  1, 3, 2, 2, 3, 1, 2, 2, 2, 2, 0, 4, 2, 2, 4, 0,
  3, 1, 2, 2, 1, 3, 2, 2, 2, 2, 4, 0, 2, 2, 0, 4,
]);

export const DITHER_B = new Uint8Array([
  5, 3, 8, 0, 6, 2, 7, 1, 3, 5, 0, 8, 2, 6, 1, 7,
  8, 0, 6, 2, 7, 1, 5, 3, 0, 8, 2, 6, 1, 7, 3, 5,
  6, 2, 7, 1, 5, 3, 8, 0, 2, 6, 1, 7, 3, 5, 0, 8,
  7, 1, 5, 3, 8, 0, 6, 2, 1, 7, 3, 5, 0, 8, 2, 6,
]);

const clamp = (v: number) => (v < 0 ? 0 : v > 255 ? 255 : v);

export interface RGBA {
  r: number; g: number; b: number; a: number;
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
      out[oi] = (v >> 8) & 0xff;       // big-endian high byte
      out[oi + 1] = v & 0xff;          // big-endian low byte
      out[oi + 2] = rgba[si + 3];      // alpha (raw)
    }
  }
  return out;
}

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

export function decodeRGB565(hi: number, lo: number): { r: number; g: number; b: number } {
  const r = ((hi >> 3) & 0x1f) << 3;
  const g = (((hi & 0x07) << 3) | ((lo >> 5) & 0x07)) << 2;
  const b = (lo & 0x1f) << 3;
  return { r: r | (r >> 5), g: g | (g >> 6), b: b | (b >> 5) };
}

export function decodePixelsRGB(pixels: Uint8Array, w: number, h: number): Uint8Array {
  const out = new Uint8Array(w * h * 4);
  for (let i = 0; i < w * h; i++) {
    const hi = pixels[i * 2];
    const lo = pixels[i * 2 + 1];
    const { r, g, b } = decodeRGB565(hi, lo);
    out[i * 4] = r;
    out[i * 4 + 1] = g;
    out[i * 4 + 2] = b;
    out[i * 4 + 3] = 255;
  }
  return out;
}

export function decodePixelsRGBA(pixels: Uint8Array, w: number, h: number): Uint8Array {
  const out = new Uint8Array(w * h * 4);
  for (let i = 0; i < w * h; i++) {
    const hi = pixels[i * 3];
    const lo = pixels[i * 3 + 1];
    const { r, g, b } = decodeRGB565(hi, lo);
    out[i * 4] = r;
    out[i * 4 + 1] = g;
    out[i * 4 + 2] = b;
    out[i * 4 + 3] = pixels[i * 3 + 2];
  }
  return out;
}
