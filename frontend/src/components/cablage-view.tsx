"use client";

import { forwardRef } from "react";
import { pinKey, type Flags } from "@/lib/flags";
import { ZoomPane } from "./zoom-pane";
import type { Cell, Connector, Contact, HarnessModel, Selection } from "@/lib/types";

interface Props { model: HarnessModel; flags: Flags; sel: Selection; onSelect: (s: Selection) => void }

const COL = { deep: "#12293a", sky: "#006eb1", red: "#c80a26", warn: "#c68a00", line: "#c2ddf0", veil: "#cee5fc", ink: "#001423" };
const PAD = 8;

/** One word of the drawing, drawn at its original position and size. */
function Word({ c, fill, bold }: { c: Cell; fill: string; bold?: boolean }) {
  const h = c.y1 - c.y0;
  return (
    <text x={c.x0} y={c.y1 - h * 0.2} fontSize={h * 0.88} fontFamily="IBM Plex Mono, monospace" fontWeight={bold ? 700 : 500} fill={fill}
      textLength={c.x1 - c.x0} lengthAdjust="spacingAndGlyphs" pointerEvents="none">{c.t}</text>
  );
}

const rowBox = (k: Contact): { x0: number; y0: number; x1: number; y1: number } | null => {
  const cs = k.cells ?? [];
  if (!cs.length) return null;
  return { x0: Math.min(...cs.map((c) => c.x0)), y0: Math.min(...cs.map((c) => c.y0)), x1: Math.max(...cs.map((c) => c.x1)), y1: Math.max(...cs.map((c) => c.y1)) };
};

/** Sheet 2 redrawn at its real layout: every table sits where it is on the drawing, rows as written. */
export const CablageView = forwardRef<SVGSVGElement, Props>(function CablageView({ model, flags, sel, onSelect }, ref) {
  const wire = model.wires.find((w) => w.conductorId === sel.conductorId);
  const partner = wire ? model.wires.find((w) => w.pairId === wire.pairId && w.conductorId !== wire.conductorId) : undefined;
  const hit = (w: typeof wire, conn: string, pin: string): boolean =>
    !!w && ((w.from.conn === conn && w.from.pin === pin) || (w.to?.conn === conn && w.to.pin === pin));
  const conductorOf = (conn: string, pin: string): string | undefined =>
    model.wires.find((w) => (w.from.conn === conn && w.from.pin === pin) || (w.to?.conn === conn && w.to.pin === pin))?.conductorId;

  const blocks = model.connectors.filter((c) => c.header?.length && c.contacts.some((k) => k.cells?.length));
  if (!blocks.length) return <p className="p-6 text-dim">Positions du plan indisponibles : relancer l&apos;analyse.</p>;

  const extent = (c: Connector) => {
    const all: Cell[] = [...(c.header ?? []), ...c.contacts.flatMap((k) => [...(k.cells ?? []), ...(k.wireCell ? [k.wireCell] : [])])];
    return { x0: Math.min(...all.map((a) => a.x0)) - PAD, y0: Math.min(...all.map((a) => a.y0)) - PAD, x1: Math.max(...all.map((a) => a.x1)) + PAD, y1: Math.max(...all.map((a) => a.y1)) + PAD };
  };
  const ext = new Map(blocks.map((c) => [c.id, extent(c)]));
  const all = [...ext.values()];
  const vx = Math.min(...all.map((e) => e.x0)) - 20, vy = Math.min(...all.map((e) => e.y0)) - 20;
  const vw = Math.max(...all.map((e) => e.x1)) - vx + 20, vh = Math.max(...all.map((e) => e.y1)) - vy + 20;

  const link = (() => {
    if (!wire?.to) return null;
    const a = blocks.find((b) => b.id === wire.from.conn), b = blocks.find((x) => x.id === wire.to!.conn);
    const ra = a?.contacts.find((k) => k.pin === wire.from.pin), rb = b?.contacts.find((k) => k.pin === wire.to!.pin);
    const ba = ra && rowBox(ra), bb = rb && rowBox(rb);
    if (!a || !b || !ba || !bb) return null;
    const ea = ext.get(a.id)!, eb = ext.get(b.id)!;
    return { x1: ea.x1, y1: (ba.y0 + ba.y1) / 2, x2: eb.x0, y2: (bb.y0 + bb.y1) / 2 };
  })();

  const sheet = model.topology?.pages?.schematic ?? blocks[0]?.page ?? 0;
  return (
    <ZoomPane ref={ref} viewBox={{ x: vx, y: vy, w: vw, h: vh }} label="Schéma de câblage (disposition de la feuille 2)">
      {/* original vector strokes of the sheet (tables, pair links, twisted-pair wires), under the text */}
      <g pointerEvents="none">
        {(model.graphics?.[String(sheet)] ?? []).map((p, i) => (
          <path key={i} d={p.d} fill={p.f ?? "none"} stroke={p.c ?? "none"} strokeWidth={p.w} strokeLinecap="round" strokeLinejoin="round" />
        ))}
      </g>
      {blocks.map((c) => {
        const e = ext.get(c.id)!;
        const cflag = flags.connectors.get(c.id);
        return (
          <g key={c.id}>
            <rect x={e.x0} y={e.y0} width={e.x1 - e.x0} height={e.y1 - e.y0} fill="none" stroke={sel.conn === c.id ? COL.sky : cflag?.severity === "error" ? COL.red : COL.deep} strokeWidth={sel.conn === c.id || cflag ? 2.5 : 1} />
            {cflag && (
              <g><title>{cflag.issues.map((i) => i.message).join("\n")}</title>
                <rect x={e.x1 - 78} y={e.y0 - 17} width={78} height={16} fill={cflag.severity === "error" ? COL.red : COL.warn} />
                <text x={e.x1 - 39} y={e.y0 - 5} fontSize={10} fontWeight={700} fill="#fff" textAnchor="middle">{cflag.issues.length} à vérifier</text>
              </g>
            )}
            {c.header?.map((h, i) => <Word key={i} c={h} fill={COL.ink} bold />)}
            {c.contacts.map((k, i) => {
              const b = rowBox(k);
              if (!b) return null;
              const f = flags.pins.get(pinKey(c.id, k.pin));
              const on = hit(wire, c.id, k.pin), pair = hit(partner, c.id, k.pin);
              const tone = f?.severity === "error" ? COL.red : f?.severity === "warning" ? COL.warn : COL.ink;
              const pinIdx = (k.cells ?? []).map((x) => x.t).lastIndexOf(k.pin);
              const prev = c.contacts[i - 1]?.wireCell;
              return (
                <g key={`${k.pin}-${i}`} className="cursor-pointer"
                  onClick={() => { const cid = conductorOf(c.id, k.pin); onSelect(cid ? { conductorId: cid, conn: c.id, pin: k.pin } : { conn: c.id, pin: k.pin }); }}>
                  <title>{[`${c.id}:${k.pin}`, ...(f?.issues.map((x) => `⚠ ${x.message}`) ?? [])].join("\n")}</title>
                  <rect x={b.x0 - 3} y={b.y0 - 1} width={b.x1 - b.x0 + 6} height={b.y1 - b.y0 + 2}
                    fill={f?.severity === "error" ? "#fbe9e9" : f ? "#fbf3dc" : on ? COL.veil : "transparent"}
                    stroke={on || pair ? COL.sky : f ? tone : "none"} strokeWidth={on ? 2 : 1.2} strokeDasharray={pair ? "5 3" : undefined} />
                  {(k.cells ?? []).map((cell, j) => <Word key={j} c={cell} fill={j === pinIdx ? tone : COL.ink} bold={j === pinIdx} />)}
                  {k.wireCell && k.wireCell.y0 !== prev?.y0 && <Word c={k.wireCell} fill={COL.red} bold />}
                </g>
              );
            })}
          </g>
        );
      })}
      {link && <path d={`M${link.x1} ${link.y1} C${link.x1 + 160} ${link.y1} ${link.x2 - 160} ${link.y2} ${link.x2} ${link.y2}`} fill="none" stroke={COL.sky} strokeWidth={3} strokeOpacity={0.75} pointerEvents="none" />}
    </ZoomPane>
  );
});
