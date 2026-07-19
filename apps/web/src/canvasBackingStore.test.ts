import { describe, expect, it, vi } from "vitest";
import { syncCanvasBackingStore } from "./canvasBackingStore";

function trackedCanvas(initialWidth: number, initialHeight: number) {
  let width = initialWidth;
  let height = initialHeight;
  const writes = { width: 0, height: 0 };
  return {
    canvas: {
      get width() { return width; },
      set width(value: number) { writes.width += 1; width = value; },
      get height() { return height; },
      set height(value: number) { writes.height += 1; height = value; },
    },
    writes,
  };
}

describe("canvas backing-store continuity", () => {
  it("does not clear the bitmap when a replay step keeps the same viewport", () => {
    const { canvas, writes } = trackedCanvas(1200, 800);
    const context = { setTransform: vi.fn() };

    expect(syncCanvasBackingStore(canvas, context, 600, 400, 2)).toBe(false);
    expect(writes).toEqual({ width: 0, height: 0 });
    expect(context.setTransform).toHaveBeenCalledWith(2, 0, 0, 2, 0, 0);
  });

  it("resizes once when the CSS viewport actually changes", () => {
    const { canvas, writes } = trackedCanvas(1000, 700);
    const context = { setTransform: vi.fn() };

    expect(syncCanvasBackingStore(canvas, context, 600, 400, 2)).toBe(true);
    expect(canvas).toMatchObject({ width: 1200, height: 800 });
    expect(writes).toEqual({ width: 1, height: 1 });
  });
});
