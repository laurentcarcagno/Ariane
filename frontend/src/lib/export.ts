import type { HarnessModel } from "./types";

function download(name: string, mime: string, data: string): void {
  const url = URL.createObjectURL(new Blob([data], { type: mime }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}

const csvCell = (v: string | number | null): string => `"${String(v ?? "").replaceAll('"', '""')}"`;

export function fromToCsv(model: HarnessModel): string {
  const head = ["Fil", "Paire", "Polarité", "Signal", "Type", "De connecteur", "De pin", "Vers connecteur", "Vers pin", "Segments"];
  const rows = model.wires.map((w) => [
    w.conductorId, w.pairId, w.polarity, `${w.signal} ${w.nomRed}`, w.type, w.from.conn, w.from.pin,
    w.to?.conn ?? "", w.to?.pin ?? "", (model.routes[w.pairId] ?? []).join(" > "),
  ]);
  return "﻿" + [head, ...rows].map((r) => r.map(csvCell).join(";")).join("\r\n");
}

export const exportCsv = (m: HarnessModel): void => download("from-to.csv", "text/csv;charset=utf-8", fromToCsv(m));
export const exportJson = (m: HarnessModel): void => download("harness-model.json", "application/json", JSON.stringify(m, null, 2));

export function exportSvg(svg: SVGSVGElement | null, name: string): void {
  if (!svg) return;
  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  download(name, "image/svg+xml", new XMLSerializer().serializeToString(clone));
}
