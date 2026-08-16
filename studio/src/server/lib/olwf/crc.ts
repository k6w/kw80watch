export function huawoCrc(data: Uint8Array): number {
  let i = 0xffff;
  for (let n = 0; n < data.length; n++) {
    const b = data[n] & 0xff;
    let i2 = (((i << 8) | ((i >> 8) & 0xff)) & 0xffff) ^ b;
    let i3 = i2 ^ (((i2 & 0xff) >> 4) & 0xffff);
    let i4 = i3 ^ ((i3 << 12) & 0xffff);
    i = i4 ^ (((i4 & 0xff) << 5) & 0xffff);
  }
  return i;
}

export function crc16(data: Uint8Array): number {
  return huawoCrc(data);
}

export function crc16Bytes(data: Uint8Array): Uint8Array {
  const c = huawoCrc(data);
  return new Uint8Array([c & 0xff, (c >> 8) & 0xff]);
}
