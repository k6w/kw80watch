export type Colour = { r: number; g: number; b: number };
export type Point = { x: number; y: number };
export type Rect = { x: number; y: number; w: number; h: number };
export type Circle = { cx: number; cy: number; r: number; start: number; end: number };

export type Align = 0 | 1 | 2;  // left | centre | right

export interface AssetImage {
  id: string;
  name: string;
  width: number;
  height: number;
  cf: 4 | 5;
  pixels: Uint8Array;      // raw encoded (RGB565 BE for cf=4, +alpha for cf=5)
  sourceUrl?: string;      // for uploaded originals (preview)
}

export type ElementKind = "background" | "image" | "digits" | "pictureSet" | "animation" | "vectorHand" | "bitmapHand";

export interface BackgroundElement {
  kind: "background";
  id: string;
  name: string;
  assetId: string;
}

export interface ImageElement {
  kind: "image";
  id: string;
  name: string;
  assetId: string;
  x: number;
  y: number;
}

export interface DigitsElement {
  kind: "digits";
  id: string;
  name: string;
  assetIds: string[];      // 10 glyph images (0-9)
  source: number;          // numeric source ID
  x: number;
  y: number;
  align: Align;
  w: number;
  h: number;
  suffixAssetId?: string;  // optional 11th glyph (°, %)
  cf: number;              // LVGL cf of glyph images (5)
}

export interface PictureSetElement {
  kind: "pictureSet";
  id: string;
  name: string;
  assetIds: string[];      // one per state
  type: number;            // PictureSet type ID
  x: number;
  y: number;
}

export interface AnimationElement {
  kind: "animation";
  id: string;
  name: string;
  assetIds: string[];      // frame images
  x: number;
  y: number;
  periodMs: number;
}

export interface VectorHandElement {
  kind: "vectorHand";
  id: string;
  name: string;
  canvas: Rect;
  points: Point[];
  circles: Circle[];
  source: number;          // rotation source ID
  range: number;
  fillColor: Colour;
  arcColor: Colour;
}

export interface BitmapHandElement {
  kind: "bitmapHand";
  id: string;
  name: string;
  assetId: string;
  box: Rect;
  pivot: Point;
  source: number;
  range: number;
}

export type WatchfaceElement =
  | BackgroundElement
  | ImageElement
  | DigitsElement
  | PictureSetElement
  | AnimationElement
  | VectorHandElement
  | BitmapHandElement;

export interface WatchfaceDocument {
  version: number;
  elements: WatchfaceElement[];
  assets: AssetImage[];
}

export interface ProjectMeta {
  id: string;
  name: string;
  authorId: string;
  authorName: string;
  createdAt: number;
  updatedAt: number;
}

export interface PublishedWatchface {
  id: string;
  projectId: string;
  authorId: string;
  authorName: string;
  name: string;
  description: string;
  tags: string[];
  thumbnailUrl: string;
  binUrl: string;
  downloadCount: number;
  featured: boolean;
  publishedAt: number;
  rating: number;
  ratingCount: number;
}
