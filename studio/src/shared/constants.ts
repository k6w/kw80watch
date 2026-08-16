export const SCREEN_W = 368;
export const SCREEN_H = 448;
export const SCREEN_R = 55;
export const THUMB_W = 180;
export const THUMB_H = 219;
export const THUMB_R = 26;

export const MAX_IMAGE_COUNT = 254;   // cnt ≤ 0x3F8 → 254 images
export const MAX_LAYOUT_BYTES = 2048;  // len3 ≤ 0x800

export const CF = {
  TRUE_COLOR: 4,
  TRUE_COLOR_ALPHA: 5,
  USER_ENCODED_0: 24,
  USER_ENCODED_1: 25,
} as const;

export const TRAILER = new Uint8Array([0x55, 0x43, 0x50, 0x44, 0x4f, 0x4c, 0x57, 0x46]); // UCPDOLWF

export const OTA = {
  DATA_SERVICE: 0x6006,
  DATA_WRITE: 0x8001,
  DATA_READ: 0x8002,
  DATA2_WRITE: 0x8003,
  DATA2_READ: 0x8004,
  OTA_SERVICE: 0x1530,
  OTA_CTRL: 0x1531,
  OTA_DATA: 0x1532,
  TYPE_PICTURE: 4,
  MTU: 128,
  PIECE: 2048,
  BATCH: 20,
} as const;
