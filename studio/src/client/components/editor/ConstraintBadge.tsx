import { useEditor } from "../../lib/store/editor.ts";
import { MAX_IMAGE_COUNT, MAX_LAYOUT_BYTES } from "@shared/constants.ts";

export function ConstraintBadge() {
  const { doc } = useEditor();

  const imageCount = 1 + doc.assets.length;
  const imgPct = (imageCount / MAX_IMAGE_COUNT) * 100;
  const imgColor = imageCount > MAX_IMAGE_COUNT ? "text-red-400" : imgPct > 80 ? "text-yellow-400" : "text-green-400";

  let layoutBytes = 2;
  for (const el of doc.elements) {
    layoutBytes += estimateElementSize(el);
  }
  const layoutPct = (layoutBytes / MAX_LAYOUT_BYTES) * 100;
  const layoutColor = layoutBytes > MAX_LAYOUT_BYTES ? "text-red-400" : layoutPct > 80 ? "text-yellow-400" : "text-green-400";

  return (
    <div className="flex items-center gap-4 text-xs">
      <span className={imgColor}>
        Images: {imageCount} / {MAX_IMAGE_COUNT}
      </span>
      <span className={layoutColor}>
        Layout: {layoutBytes} / {MAX_LAYOUT_BYTES}B
      </span>
    </div>
  );
}

function estimateElementSize(el: any): number {
  switch (el.kind) {
    case "background": return 8;
    case "image": return 12;
    case "digits": return 35;
    case "pictureSet": return 15 + el.assetIds?.length || 0;
    case "animation": return 15 + el.assetIds?.length || 0;
    case "vectorHand": return 30 + el.points.length * 6 + el.circles.length * 14;
    case "bitmapHand": return 30;
    default: return 20;
  }
}
