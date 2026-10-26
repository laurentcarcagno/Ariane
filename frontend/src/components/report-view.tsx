"use client";

import { useState } from "react";
import { counts } from "@/lib/flags";
import type { HarnessModel, Issue, Severity } from "@/lib/types";

const TONE: Record<Severity, string> = { error: "bg-danger-bg text-danger", warning: "bg-warn-bg text-warn", info: "bg-hover text-sky" };
const LABEL: Record<Severity, string> = { error: "Erreur", warning: "Alerte", info: "Info" };

export function ReportView({ model, onOpen }: { model: HarnessModel; onOpen: (i: Issue) => void }) {
  const [show, setShow] = useState<Record<Severity, boolean>>({ error: true, warning: true, info: false });
  const c = counts(model.issues);
  const rows = model.issues.filter((i) => show[i.severity]);
  const stats = (model.topology?.stats ?? {}) as Record<string, unknown>;
  const tiles: [string, string | number][] = [
    ["Connecteurs", model.connectors.length],
    ["Conducteurs", model.wires.length],
    ["Paires", new Set(model.wires.map((w) => w.pairId)).size],
    ["Routées", Object.keys(model.routes).length],
    ["Contacts pin", String(stats.contacts_pin ?? "–")],
    ["Contacts socket", String(stats.contacts_socket ?? "–")],
  ];
  return (
    <div className="p-4">
      <div className="mb-4 grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(160px,1fr))]">
        {tiles.map(([k, v]) => (
          <div key={k} className="border border-line border-t-[3px] border-t-sky bg-paper p-3">
            <div className="label">{k}</div>
            <div className="font-mono text-[22px] font-medium">{v}</div>
          </div>
        ))}
      </div>
      <div className="mb-3 flex gap-2">
        {(["error", "warning", "info"] as Severity[]).map((s) => (
          <button key={s} type="button" aria-pressed={show[s]} onClick={() => setShow({ ...show, [s]: !show[s] })}
            className={`pill border ${show[s] ? `${TONE[s]} border-current` : "border-line bg-paper text-mute"}`}>
            <span className="h-2 w-2 bg-current" />{LABEL[s]} · {c[s]}
          </button>
        ))}
      </div>
      <ul className="border border-line bg-paper">
        {rows.map((i, k) => (
          <li key={k} className="border-b border-line last:border-0">
            <button type="button" onClick={() => onOpen(i)} className="flex w-full items-start gap-3 px-3 py-2 text-left hover:bg-hover">
              <span className={`pill shrink-0 ${TONE[i.severity]}`}>{LABEL[i.severity]}</span>
              <span className="flex-1"><span className="font-mono text-label text-mute">{i.code}</span><br />{i.message}</span>
            </button>
          </li>
        ))}
        {!rows.length && <li className="p-4 text-mute">Aucun point pour ce filtre.</li>}
      </ul>
    </div>
  );
}
