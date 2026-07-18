import { describe, expect, it } from "vitest";
import { advanceReplay, replayStart } from "./replay";

describe("timeline replay", () => {
  it("starts live playback at the beginning", () => {
    expect(replayStart(null, 218)).toBe(1);
    expect(replayStart(218, 218)).toBe(1);
  });

  it("resumes from a historical sequence", () => {
    expect(replayStart(42, 218)).toBe(42);
  });

  it("advances by rate without passing the event horizon", () => {
    expect(advanceReplay(10, 218, 4)).toBe(14);
    expect(advanceReplay(216, 218, 12)).toBe(218);
  });
});
