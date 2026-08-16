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

export function bytesField(field: number, value: Uint8Array | number[]): Uint8Array {
  return msg(field, new Uint8Array(value));
}
