export function lvglHeader(w: number, h: number, cf: number = 4): Uint8Array {
  const header = ((w << 10) | (h << 21)) + cf;
  return new Uint8Array([
    header & 0xff,
    (header >> 8) & 0xff,
    (header >> 16) & 0xff,
    (header >> 24) & 0xff,
  ]);
}

export function parseHeader(buf: Uint8Array): { w: number; h: number; cf: number } {
  const raw = buf[0] | (buf[1] << 8) | (buf[2] << 16) | (buf[3] << 24);
  return {
    cf: raw & 0x1f,
    w: (raw >> 10) & 0x7ff,
    h: (raw >> 21) & 0x7ff,
  };
}
