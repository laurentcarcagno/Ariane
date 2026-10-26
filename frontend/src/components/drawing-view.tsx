"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Flags } from "@/lib/flags";
import type { HarnessModel, Selection } from "@/lib/types";

interface Props { model: HarnessModel; flags: Flags; sel: Selection; onSelect: (s: Selection) => void; file: File | undefined }

interface PdfPage {
  getViewport(o: { scale: number }): { width: number; height: number };
  render(o: { canvasContext: CanvasRenderingContext2D; viewport: unknown; transform?: number[] }): { promise: Promise<void> };
}
interface PdfDoc { numPages: number; getPage(n: number): Promise<PdfPage> }

const C = { route: "#006eb1", error: "#c80a26", warn: "#c68a00" };

/** Original sheet rendered by pdf.js (bundled worker, no network) with the model drawn on top. */
export function DrawingView({ model, flags, sel, onSelect, file }: Props) {
  const [doc, setDoc] = useState<PdfDoc | null>(null);
  const [pageNo, setPageNo] = useState(0);
  const [zoom, setZoom] = useState(0);
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);
  const [showIssues, setShowIssues] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const topo = model.topology;
  const pages = topo?.pages;

  useEffect(() => {
    if (!file) { setDoc(null); return; }
    let dead = false;
    (async () => {
      try {
        const pdfjs = await import("pdfjs-dist");
        pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();
        const d = (await pdfjs.getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise) as unknown as PdfDoc;
        if (!dead) { setDoc(d); setPageNo(pages?.schematic ?? 0); setZoom(0); }
      } catch (e) { if (!dead) setErr((e as Error).message); }
    })();
    return () => { dead = true; };
  }, [file, pages?.schematic]);

  useEffect(() => {
    if (!doc || !canvas.current) return;
    let dead = false;
    (async () => {
      const page = await doc.getPage(pageNo + 1);
      const base = page.getViewport({ scale: 1 });
      const z = zoom || Math.max(0.2, ((box.current?.clientWidth ?? 1200) - 24) / base.width);
      if (!zoom) { setZoom(z); return; }
      const vp = page.getViewport({ scale: z });
      const dpr = window.devicePixelRatio || 1;
      const cv = canvas.current;
      if (!cv || dead) return;
      cv.width = Math.floor(vp.width * dpr);
      cv.height = Math.floor(vp.height * dpr);
      cv.style.width = `${vp.width}px`;
      cv.style.height = `${vp.height}px`;
      const ctx = cv.getContext("2d");
      if (!ctx) return;
      setSize({ w: base.width, h: base.height });
      await page.render({ canvasContext: ctx, viewport: vp, transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : [1, 0, 0, 1, 0, 0] }).promise;
    })().catch((e: Error) => !dead && setErr(e.message));
    return () => { dead = true; };
  }, [doc, pageNo, zoom]);

  const wire = model.wires.find((w) => w.conductorId === sel.conductorId);
  const partner = wire ? model.wires.find((w) => w.pairId === wire.pairId && w.conductorId !== wire.conductorId) : undefined;
  const route = useMemo(() => new Set(wire ? model.routes[wire.pairId] ?? [] : []), [wire, model.routes]);
  const sheets: [number, string][] = [
    ...(pages ? [[pages.topology, "Topologie"], [pages.schematic, "Câblage"]] as [number, string][] : []),
    ...(pages?.diameters != null ? [[pages.diameters, "Diamètres"] as [number, string]] : []),
  ].sort((a, b) => a[0] - b[0]);
  const onTopoSheet = pages != null && (pageNo === pages.topology || pageNo === pages.diameters);
  const issuesHere = model.issues.filter((i) => i.severity !== "info").flatMap((i) => i.where.filter((l) => l.page === pageNo).map((l) => ({ i, l })));

  if (!file) return <p className="p-8 text-mute">Le PDF du plan n&apos;est plus en mémoire : relancer l&apos;analyse pour afficher le dessin.</p>;
  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-line bg-paper px-4 py-2">
        {sheets.map(([n, label]) => (
          <button key={n} type="button" aria-pressed={pageNo === n} onClick={() => setPageNo(n)}
            className={`btn ${pageNo === n ? "border-sky bg-veil" : ""}`}>Feuille {n + 1} · {label}</button>
        ))}
        <span className="ml-auto flex items-center gap-2">
          <button type="button" className="btn" aria-label="Zoom arrière" onClick={() => setZoom(Math.max(0.2, (zoom || 1) / 1.25))}>−</button>
          <span className="w-12 text-center font-mono">{Math.round(zoom * 100)}%</span>
          <button type="button" className="btn" aria-label="Zoom avant" onClick={() => setZoom(Math.min(4, (zoom || 1) * 1.25))}>+</button>
          <button type="button" className="btn" onClick={() => setZoom(0)}>Ajuster</button>
          <label className="flex items-center gap-2"><input type="checkbox" checked={showIssues} onChange={(e) => setShowIssues(e.target.checked)} /><span className="label">Erreurs</span></label>
        </span>
      </div>
      <div ref={box} className="min-h-0 flex-1 overflow-auto bg-muted p-3">
        {err && <p role="alert" className="mb-2 border border-danger bg-danger-bg p-2 text-danger">{err}</p>}
        <div className="relative inline-block bg-paper" style={{ lineHeight: 0 }}>
          <canvas ref={canvas} />
          {size && (
            <svg viewBox={`0 0 ${size.w} ${size.h}`} className="absolute inset-0 h-full w-full" aria-label="Surcouche du modèle">
              {/* every conductor written on the schematic is clickable; the selected pair is boxed */}
              {model.wires.flatMap((w) => w.marks.filter((m) => m.page === pageNo).map((m) => {
                const on = w.conductorId === wire?.conductorId;
                const pair = w.conductorId === partner?.conductorId;
                const bad = flags.wires.has(w.pairId);
                return (
                  <rect key={`${w.conductorId}-${m.role}`} x={m.x0 - 3} y={m.y0 - 2} width={m.x1 - m.x0 + 6} height={m.y1 - m.y0 + 4}
                    fill={on ? C.route : "transparent"} fillOpacity={on ? 0.22 : 0} stroke={on || pair ? C.route : "none"}
                    strokeWidth={on ? 2.5 : 1.5} strokeDasharray={pair ? "5 3" : undefined}
                    className="cursor-pointer" onClick={() => onSelect({ conductorId: w.conductorId, conn: m.role === "from" ? w.from.conn : w.to?.conn ?? w.from.conn, pin: m.role === "from" ? w.from.pin : w.to?.pin ?? w.from.pin })}>
                    <title>{`${w.conductorId} ${w.signal} ${w.nomRed}${bad ? " ⚠" : ""}`}</title>
                  </rect>
                );
              }))}
              {onTopoSheet && topo?.segments?.map((s) => {
                const d = s.polyline.map((p, i) => `${i ? "L" : "M"}${p[0]} ${p[1]}`).join(" ");
                const on = route.has(s.id) || sel.segment === s.id;
                return (
                  <g key={s.id} className="cursor-pointer" onClick={() => onSelect({ ...sel, segment: s.id })}>
                    <path d={d} fill="none" stroke="transparent" strokeWidth={14} />
                    {on && <path d={d} fill="none" stroke={C.route} strokeWidth={8} strokeOpacity={0.55} strokeLinecap="round" strokeLinejoin="round" />}
                    {flags.segments.has(s.id) && <path d={d} fill="none" stroke={flags.segments.get(s.id)?.severity === "error" ? C.error : C.warn} strokeWidth={9} strokeOpacity={0.35} strokeDasharray="8 5" />}
                  </g>
                );
              })}
              {showIssues && issuesHere.map(({ i, l }, k) => (
                <g key={k}>
                  <circle cx={l.x} cy={l.y} r={11} fill={i.severity === "error" ? C.error : C.warn} fillOpacity={0.22} stroke={i.severity === "error" ? C.error : C.warn} strokeWidth={2} />
                  <title>{i.message}</title>
                </g>
              ))}
            </svg>
          )}
        </div>
      </div>
    </div>
  );
}
