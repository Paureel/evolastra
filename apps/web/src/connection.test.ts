import { describe, expect, it } from "vitest";
import { safeEndpoint } from "./connection";

describe("private companion endpoint policy", () => {
  it("allows only loopback companion origins", () => {
    expect(safeEndpoint("http://127.0.0.1:8000/")).toBe("http://127.0.0.1:8000");
    expect(safeEndpoint("http://localhost:8123")).toBe("http://localhost:8123");
    expect(safeEndpoint("https://localhost:8443")).toBe("https://localhost:8443");
  });

  it("rejects every remote endpoint, embedded credentials, and API paths", () => {
    expect(() => safeEndpoint("http://example.com")).toThrow();
    expect(() => safeEndpoint("https://api.evolastra.example")).toThrow();
    expect(() => safeEndpoint("https://user:secret@example.com")).toThrow();
    expect(() => safeEndpoint("http://127.0.0.1:8000/api/v1")).toThrow();
  });
});
