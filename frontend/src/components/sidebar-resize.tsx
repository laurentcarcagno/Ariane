"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// Same width and limits in ARIANE, pdf2md-ui and REQMAP: keep the three copies of this file in step.
export const SIDEBAR_DEFAULT = 300;
const MIN = 220;
const MAX = 560;
const STORAGE_KEY = "hemeria.sidebar.width";

const clamp = (w: number) => Math.min(MAX, Math.max(MIN, Math.round(w)));

/** Width of the side panel in px, kept in this browser. Starts at SIDEBAR_DEFAULT (also on the server render). */
export function useSidebarWidth() {
  const [width, setWidthState] = useState(SIDEBAR_DEFAULT);
  useEffect(() => {
    try {
      const saved = Number(window.localStorage.getItem(STORAGE_KEY));
      if (saved) setWidthState(clamp(saved));
    } catch { /* storage blocked: keep the default */ }
  }, []);
  const setWidth = useCallback((w: number) => {
    const v = clamp(w);
    setWidthState(v);
    try { window.localStorage.setItem(STORAGE_KEY, String(v)); } catch { /* not persisted */ }
  }, []);
  return [width, setWidth] as const;
}

/** Drag handle on the right edge of the panel (the panel must be `relative`). Arrow keys resize, double-click resets. */
export function SidebarHandle({ width, onChange }: { width: number; onChange: (w: number) => void }) {
  const drag = useRef<{ x: number; w: number } | null>(null);
  const [active, setActive] = useState(false);
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Largeur du panneau latéral"
      aria-valuemin={MIN}
      aria-valuemax={MAX}
      aria-valuenow={width}
      tabIndex={0}
      title="Glisser pour redimensionner (double-clic : largeur initiale)"
      className={`absolute inset-y-0 right-0 z-10 w-1.5 cursor-col-resize touch-none transition-colors hover:bg-sky focus-visible:bg-sky ${active ? "bg-sky" : ""}`}
      onPointerDown={(e) => {
        e.currentTarget.setPointerCapture(e.pointerId);
        drag.current = { x: e.clientX, w: width };
        setActive(true);
      }}
      onPointerMove={(e) => { if (drag.current) onChange(drag.current.w + e.clientX - drag.current.x); }}
      onPointerUp={() => { drag.current = null; setActive(false); }}
      onPointerCancel={() => { drag.current = null; setActive(false); }}
      onDoubleClick={() => onChange(SIDEBAR_DEFAULT)}
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") { e.preventDefault(); onChange(width - 16); }
        else if (e.key === "ArrowRight") { e.preventDefault(); onChange(width + 16); }
        else if (e.key === "Home") { e.preventDefault(); onChange(SIDEBAR_DEFAULT); }
      }}
    />
  );
}
