import type { Cell, GPath, Sheet } from "./types";

export interface Box { x0: number; y0: number; x1: number; y1: number }

/** Width of the band along the sheet edges that holds the frame, its zone ticks and the zone letters. */
const MARGIN = 14;
/** Title blocks sit in the bottom-right corner: black strokes starting in the last 20 % of the width and 10 % of the height. */
const CORNER = { x: 0.8, y: 0.9 };
/** Strokes and words farther than this from the connector tables are stray annotations: they are left out of the view. */
const REACH = 150;

export const pathBox = (d: string): Box => {
  const n = (d.match(/-?\d+\.?\d*/g) ?? []).map(Number);
  const xs = n.filter((_, i) => i % 2 === 0), ys = n.filter((_, i) => i % 2 === 1);
  return { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) };
};

const inBand = (b: Box, s: Sheet): boolean =>
  b.x1 <= MARGIN || b.y1 <= MARGIN || b.x0 >= s.width - MARGIN || b.y0 >= s.height - MARGIN;

const within = (b: Box, r: Box): boolean => b.x0 >= r.x0 - 0.5 && b.y0 >= r.y0 - 0.5 && b.x1 <= r.x1 + 0.5 && b.y1 <= r.y1 + 0.5;

const touches = (b: Box, r: Box): boolean => b.x0 <= r.x1 && b.x1 >= r.x0 && b.y0 <= r.y1 && b.y1 >= r.y0;

const union = (boxes: Box[]): Box | null =>
  boxes.length ? { x0: Math.min(...boxes.map((b) => b.x0)), y0: Math.min(...boxes.map((b) => b.y0)), x1: Math.max(...boxes.map((b) => b.x1)), y1: Math.max(...boxes.map((b) => b.y1)) } : null;

export interface SheetContent { paths: GPath[]; texts: Cell[]; box: Box | null }

/**
 * What the sheet shows once the frame (border, zone ticks and letters) and the title block are left out, and the box that
 * encloses it together with `extra` (the connector tables). The title block is the box of the black strokes in the
 * bottom-right corner; the frame is whatever lies in the band along the edges; strays far from the tables are dropped.
 */
export function usefulContent(paths: GPath[], sheet: Sheet, extra: Box[]): SheetContent {
  const all = paths.map((p) => ({ p, b: pathBox(p.d) })).filter((x) => !inBand(x.b, sheet));
  const title = union(all.filter((x) => x.p.c === "#000000" && x.b.x0 >= sheet.width * CORNER.x && x.b.y0 >= sheet.height * CORNER.y).map((x) => x.b));
  const tables = union(extra);
  const reach = tables && { x0: tables.x0 - REACH, y0: tables.y0 - REACH, x1: tables.x1 + REACH, y1: tables.y1 + REACH };
  const outTitle = (b: Box) => (!title || !within(b, title)) && (!reach || touches(b, reach));
  const kept = all.filter((x) => outTitle(x.b));
  const texts = sheet.texts.filter((t) => !inBand(t, sheet) && outTitle(t));
  return { paths: kept.map((x) => x.p), texts, box: union([...kept.map((x) => x.b), ...texts, ...extra]) };
}
