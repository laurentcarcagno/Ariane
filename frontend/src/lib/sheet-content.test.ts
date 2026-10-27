import { describe, expect, it } from "vitest";
import { usefulContent } from "./sheet-content";
import type { Cell, GPath, Sheet } from "./types";

const line = (x0: number, y0: number, x1: number, y1: number, c = "#000000"): GPath => ({ d: `M${x0} ${y0}L${x1} ${y1}`, c, w: 0.7, f: null });
const word = (t: string, x0: number, y0: number): Cell => ({ t, x0, y0, x1: x0 + 8, y1: y0 + 8 });

describe("usefulContent", () => {
  const sheet: Sheet = {
    width: 1000, height: 700,
    texts: [word("A", 240, 1), word("3", 2, 300), word("WIRES:", 600, 650), word("Approved", 850, 660), word("note", 300, 380)],
  };
  const paths = [
    line(0, 0, 1000, 0), line(7, 7, 993, 7), line(7, 7, 7, 693), line(500, 693, 503, 699), // frame and a zone tick
    line(800, 640, 993, 640), line(800, 640, 800, 693), // title block outline
    line(100, 100, 400, 100, "#0000ff"), line(400, 100, 400, 300, "#0000ff"),
    line(600, 640, 640, 640, "#0000ff"), // legend sketch far from the tables
  ];
  const r = usefulContent(paths, sheet, [{ x0: 90, y0: 90, x1: 410, y1: 310 }]);

  it("drops the frame, its zone letters and the title block", () => {
    expect(r.paths).toHaveLength(2);
    expect(r.texts.map((t) => t.t)).toEqual(["note"]);
  });
  it("leaves out strays far from the tables and encloses only what is left", () => {
    expect(r.box).toEqual({ x0: 90, y0: 90, x1: 410, y1: 388 });
  });
});
