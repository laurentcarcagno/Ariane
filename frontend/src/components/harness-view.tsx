"use client";

import { forwardRef, useMemo } from "react";
import { topoKey, type Flags } from "@/lib/flags";
import type { HarnessModel, Selection } from "@/lib/types";
import { ZoomPane } from "./zoom-pane";

interface Props {
  model: HarnessModel;
  flags: Flags;
  sel: Selection;
  onSelect: (s: Selection) => void;
  showLabels: boolean;
}

const COLOR = { base: "#12293a", route: "#006eb1", error: "#c80a26", warn: "#c68a00", dim: "#c2ddf0" };

/** Redrawn topology sheet: segments, numbered branch points, connector ends, with error markers. */
export const HarnessView = forwardRef<SVGSVGElement, Props>(function HarnessView({ model, flags, sel, onSelect, showLabels }, ref) {
  const topo = model.topology;
  const wire = model.wires.find((w) => w.conductorId === sel.conductorId);
  const routeIds = useMemo(() => new Set(wire ? model.routes[wire.pairId] ?? [] : []), [wire, model.routes]);
  const routeNodes = useMemo(() => {
    const s = new Set<string>();
    for (const seg of topo?.segments ?? []) if (routeIds.has(seg.id)) { s.add(seg.a); s.add(seg.b); }
    return s;
  }, [topo, routeIds]);
  const endKeys = useMemo(() => new Set(wire ? [topoKey(wire.from.conn), wire.to ? topoKey(wire.to.conn) : ""] : []), [wire]);

  if (!topo || topo.status !== "ok" || !topo.nodes || !topo.segments) {
    return <p className="p-6 text-dim">Topologie non extraite : voir le rapport de contrôle.</p>;
  }
  const pts = topo.segments.flatMap((s) => s.polyline);
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const pad = 60;
  const x0 = Math.min(...xs) - pad, y0 = Math.min(...ys) - pad - 20;
  const w = Math.max(...xs) - x0 + pad, h = Math.max(...ys) - y0 + pad + 30;
  const connByTopo = new Map(model.connectors.map((c) => [topoKey(c.id), c]));
  const hasSel = routeIds.size > 0;

  return (
    <ZoomPane ref={ref} viewBox={{ x: x0, y: y0, w, h }} label="Vue faisceau">
      {topo.segments.map((s) => {
        const flag = flags.segments.get(s.id);
        const onRoute = routeIds.has(s.id);
        const picked = sel.segment === s.id;
        const stroke = onRoute || picked ? COLOR.route : hasSel ? COLOR.dim : COLOR.base;
        const width = 2 + (s.diameterMm ?? 6) * 0.25;
        const d = s.polyline.map((p, i) => `${i ? "L" : "M"}${p[0]} ${p[1]}`).join(" ");
        const mid = s.polyline[Math.floor(s.polyline.length / 2)] ?? [0, 0];
        return (
          <g key={s.id} onClick={() => onSelect({ ...sel, segment: s.id })} className="cursor-pointer">
            <title>{`${s.id} ${s.a}–${s.b} · Ø ${s.diameterMm ?? "?"} mm · ${s.bomItems.join("/") || "sans repère"}`}</title>
            {flag?.severity === "error" && <path d={d} fill="none" stroke={COLOR.error} strokeWidth={width + 7} opacity={0.35} />}
            {flag?.severity === "warning" && <path d={d} fill="none" stroke={COLOR.warn} strokeWidth={width + 6} opacity={0.3} strokeDasharray="6 4" />}
            <path d={d} fill="none" stroke={stroke} strokeWidth={onRoute ? width + 2 : width} strokeLinejoin="round" />
            {showLabels && (
              <text x={mid[0] + 6} y={mid[1] - 5} fontSize={9} fontFamily="IBM Plex Mono" fill="#43474c">
                {s.diameterMm !== null ? `Ø${s.diameterMm}` : "Ø?"} {s.bomItems.join("/")}
              </text>
            )}
            {flag && <circle cx={mid[0]} cy={mid[1]} r={5} fill={flag.severity === "error" ? COLOR.error : COLOR.warn} stroke="#fff" strokeWidth={1.5} />}
          </g>
        );
      })}
      {topo.nodes.map((n) => {
        const conn = n.connector ? connByTopo.get(n.connector) : undefined;
        if (conn) {
          const flag = flags.connectors.get(conn.id);
          const picked = sel.conn === conn.id;
          const end = endKeys.has(n.connector ?? "");
          const bottom = n.y > y0 + h / 2;
          const top = bottom ? n.y : n.y - 26;
          return (
            <g key={n.id} onClick={() => onSelect({ conn: conn.id })} className="cursor-pointer">
              <title>{`${conn.ref} · ${conn.partNumber}${flag ? ` · ${flag.issues.length} point(s) à vérifier` : ""}`}</title>
              <rect x={n.x - 26} y={top} width={52} height={26}
                fill={picked || end ? "#cee5fc" : "#fcfdfe"} stroke={picked || end ? COLOR.route : COLOR.base} strokeWidth={picked || end ? 2.5 : 1.5} />
              <text x={n.x} y={bottom ? n.y + 40 : n.y - 32} textAnchor="middle" fontSize={11} fontWeight={700} fill="#12293a">{conn.ref}</text>
              {flag && (
                <g>
                  <circle cx={n.x + 26} cy={top} r={9} fill={flag.severity === "error" ? COLOR.error : COLOR.warn} stroke="#fff" strokeWidth={1.5} />
                  <text x={n.x + 26} y={top + 3.5} textAnchor="middle" fontSize={10} fontWeight={700} fill="#fff">{flag.issues.length}</text>
                </g>
              )}
            </g>
          );
        }
        const on = routeNodes.has(n.id);
        return (
          <g key={n.id}>
            <circle cx={n.x} cy={n.y} r={on ? 5 : 3.5} fill={on ? COLOR.route : COLOR.base} />
            <text x={n.x + 8} y={n.y - 7} fontSize={13} fontWeight={700} fill={COLOR.error}>{n.label}</text>
          </g>
        );
      })}
    </ZoomPane>
  );
});
