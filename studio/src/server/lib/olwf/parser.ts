import { parseHeader } from "./header.ts";
import { decodePixelsRGB, decodePixelsRGBA } from "./rgb565.ts";
import { SCREEN_W, SCREEN_H, TRAILER } from "@shared/constants.ts";

function u32(buf: Uint8Array, off: number): number {
  return buf[off] | (buf[off + 1] << 8) | (buf[off + 2] << 16) | (buf[off + 3] >>> 0);
}

interface ParsedImage {
  index: number;     // 1-based
  cf: number;
  w: number;
  h: number;
  offset: number;    // relative to table base
  dataLength: number;
}

export interface ParsedBin {
  off1: number;
  off2: number;
  cnt: number;
  off3: number;
  len3: number;
  imageCount: number;
  thumbnail: { w: number; h: number; cf: number; rgba: Uint8Array };
  images: ParsedImage[];
  layout: Uint8Array;
}

export function parseBin(bin: Uint8Array): ParsedBin {
  const off1 = u32(bin, 0);
  const off2 = u32(bin, 4);
  const cnt = u32(bin, 8);
  const off3 = u32(bin, 12);
  const len3 = u32(bin, 16);

  const imageCount = cnt / 4;

  // Parse thumbnail
  const thumbHeader = parseHeader(bin.subarray(off1));
  const thumbPixels = bin.subarray(
    off1 + 4,
    off1 + 4 + thumbHeader.w * thumbHeader.h * (thumbHeader.cf === 5 ? 3 : 2),
  );
  const thumbRgba = thumbHeader.cf === 5
    ? decodePixelsRGBA(thumbPixels, thumbHeader.w, thumbHeader.h)
    : decodePixelsRGB(thumbPixels, thumbHeader.w, thumbHeader.h);

  // Parse image table
  const images: ParsedImage[] = [];
  for (let i = 0; i < imageCount; i++) {
    const tableEntryOff = off2 + i * 4;
    const imgOffset = u32(bin, tableEntryOff);

    const headerOff = off2 + imgOffset;
    const header = parseHeader(bin.subarray(headerOff));
    const pixelLen = header.w * header.h * (header.cf === 5 ? 3 : 2);

    images.push({
      index: i + 1,
      cf: header.cf,
      w: header.w,
      h: header.h,
      offset: imgOffset,
      dataLength: 4 + pixelLen,
    });
  }

  const layout = bin.subarray(off3, off3 + len3);

  return {
    off1, off2, cnt, off3, len3,
    imageCount,
    thumbnail: {
      w: thumbHeader.w, h: thumbHeader.h, cf: thumbHeader.cf,
      rgba: thumbRgba,
    },
    images,
    layout,
  };
}

export function extractImageRGBA(bin: Uint8Array, parsed: ParsedBin, index: number): {
  w: number; h: number; cf: number; rgba: Uint8Array;
} {
  const img = parsed.images.find((i) => i.index === index);
  if (!img) throw new Error(`image index ${index} not found`);

  const headerOff = parsed.off2 + img.offset;
  const pixelOff = headerOff + 4;
  const pixels = bin.subarray(pixelOff, pixelOff + img.dataLength - 4);

  const rgba = img.cf === 5
    ? decodePixelsRGBA(pixels, img.w, img.h)
    : decodePixelsRGB(pixels, img.w, img.h);

  return { w: img.w, h: img.h, cf: img.cf, rgba };
}

interface RawField {
  field: number;
  wireType: number;
  value: number | Uint8Array;
}

function parseProtobufFields(buf: Uint8Array): RawField[] {
  const fields: RawField[] = [];
  let i = 0;
  while (i < buf.length) {
    let tag = 0;
    let shift = 0;
    let byte: number;
    do {
      byte = buf[i++];
      tag |= (byte & 0x7f) << shift;
      shift += 7;
    } while (byte & 0x80);

    const field = tag >> 3;
    const wireType = tag & 7;

    if (wireType === 0) {
      let value = 0;
      shift = 0;
      do {
        byte = buf[i++];
        value |= (byte & 0x7f) << shift;
        shift += 7;
      } while (byte & 0x80);
      fields.push({ field, wireType, value });
    } else if (wireType === 2) {
      let len = 0;
      shift = 0;
      do {
        byte = buf[i++];
        len |= (byte & 0x7f) << shift;
        shift += 7;
      } while (byte & 0x80);
      fields.push({ field, wireType, value: buf.subarray(i, i + len) });
      i += len;
    } else {
      break;
    }
  }
  return fields;
}

export function parseLayout(layout: Uint8Array): RawField[][] {
  const elements: RawField[][] = [];
  const fields = parseProtobufFields(layout);
  for (const f of fields) {
    if (f.field === 1 && f.wireType === 2 && f.value instanceof Uint8Array) {
      elements.push(parseProtobufFields(f.value));
    }
  }
  return elements;
}
