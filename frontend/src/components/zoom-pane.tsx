"use client";

import { forwardRef, useEffect, useRef, useState } from "react";

interface Props {
  viewBox: { x: number; y: number; w: number; h: number };
  label: string;
  children: React.ReactNode;
}

/** SVG viewport with zoom buttons (and Ctrl+wheel) inside a scrollable area: bars appear when zoomed in. */
export const ZoomPane = forwardRef<SVGSVGElement, Props>(function ZoomPane({ viewBox, label, children }, ref) {
  const box = useRef<HTMLDivElement>(null);
  const [fit, setFit] = useState(1);
  const [zoom, setZoom] = useState(0); // 0 = fit the whole drawing in the pane
  const z = zoom || fit;

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const measure = () => setFit(Math.max(0.02, Math.min((el.clientWidth - 2) / viewBox.w, (el.clientHeight - 2) / viewBox.h)));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [viewBox.w, viewBox.h]);

  const step = (f: number) => setZoom(Math.min(8, Math.max(0.02, z * f)));
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      setZoom((cur) => Math.min(8, Math.max(0.02, (cur || fit) * (e.deltaY < 0 ? 1.15 : 1 / 1.15))));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [fit]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-line bg-paper px-4 py-2">
        <button type="button" className="btn" aria-label="Zoom arrière" onClick={() => step(1 / 1.25)}>−</button>
        <span className="w-14 text-center font-mono">{Math.round(z * 100)}%</span>
        <button type="button" className="btn" aria-label="Zoom avant" onClick={() => step(1.25)}>+</button>
        <button type="button" className="btn" onClick={() => setZoom(0)}>Ajuster</button>
        <button type="button" className="btn" onClick={() => setZoom(1)}>100 %</button>
        <span className="ml-auto text-label text-mute">Ctrl + molette : zoom · barres de défilement : déplacement</span>
      </div>
      <div ref={box} className="min-h-0 flex-1 overflow-scroll bg-paper">
        <svg ref={ref} viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`} width={viewBox.w * z} height={viewBox.h * z}
          className="block" role="img" aria-label={label}>
          {children}
        </svg>
      </div>
    </div>
  );
});
