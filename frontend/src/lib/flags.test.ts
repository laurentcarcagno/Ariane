import { describe, expect, it } from "vitest";
import { buildFlags, pinKey, topoKey } from "./flags";
import type { HarnessModel } from "./types";

const model = {
  issues: [
    { severity: "warning", code: "x", message: "w", where: [], refs: [{ conn: "INIT_B_P1", pin: "w" }] },
    { severity: "error", code: "duplicate-destination", message: "e", where: [], refs: [{ conn: "INIT_B_P1", pin: "w" }, { conn: "INIT_B_P1", pin: "W" }] },
  ],
} as unknown as HarnessModel;

describe("flags", () => {
  it("should keep the worst severity and stay case-sensitive when indexing pins", () => {
    const f = buildFlags(model);
    expect(f.pins.get(pinKey("INIT_B_P1", "w"))?.severity).toBe("error");
    expect(f.pins.get(pinKey("INIT_B_P1", "W"))?.issues).toHaveLength(1);
    expect(f.pins.has(pinKey("INIT_B_P1", "c"))).toBe(false);
  });
  it("should map netlist connector ids to topology keys", () => {
    expect(topoKey("INIT_A_P1")).toBe("INIT_A");
    expect(topoKey("SC3")).toBe("SC3");
  });
});
