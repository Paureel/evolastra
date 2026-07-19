interface CanvasBackingStore {
  width: number;
  height: number;
}

interface TransformContext {
  setTransform(a: number, b: number, c: number, d: number, e: number, f: number): void;
}

export function syncCanvasBackingStore(
  canvas: CanvasBackingStore,
  context: TransformContext,
  cssWidth: number,
  cssHeight: number,
  devicePixelRatio: number,
): boolean {
  const width = Math.max(1, Math.floor(cssWidth * devicePixelRatio));
  const height = Math.max(1, Math.floor(cssHeight * devicePixelRatio));
  const resized = canvas.width !== width || canvas.height !== height;

  // Assigning either dimension clears the bitmap, even when the value is
  // unchanged. Preserve the last frame across replay/layout effect restarts.
  if (resized) {
    canvas.width = width;
    canvas.height = height;
  }
  context.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  return resized;
}
