"use client";

import { useState } from "react";
import { downloadXlsx, EMPTY_SETTINGS, type ExportSettings } from "@/lib/api";

const KEY = "ariane.exportSettings";

function remembered(username: string): ExportSettings {
  try {
    return { ...EMPTY_SETTINGS, redactor: username, ...JSON.parse(localStorage.getItem(KEY) ?? "{}") };
  } catch {
    return { ...EMPTY_SETTINGS, redactor: username };
  }
}

const CLASSIFICATIONS: [ExportSettings["classification"], string][] = [["", "Non précisée"], ["public", "Public"], ["commercial", "Commer. In confidence"], ["internal", "Internal Only"]];
const CONTROLS: [ExportSettings["export_control"], string][] = [["", "Non précisé"], ["Not Listed/Not Controlled", "Not Listed/Not Controlled"], ["Listed/Controlled", "Listed/Controlled"]];

/** Cover-page fields of the Excel export that cannot be deduced from the PDFs. Client, reference and date are filled in by the server. */
export function ExportDialog({ importId, username, onClose }: { importId: string; username: string; onClose: () => void }) {
  const [s, setS] = useState<ExportSettings>(() => remembered(username));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = <K extends keyof ExportSettings>(k: K, v: ExportSettings[K]) => setS((p) => ({ ...p, [k]: v }));
  const text = (k: "edition" | "subtitle" | "quality_manager" | "project_manager" | "redactor", label: string) => (
    <label className="block space-y-1"><span className="label">{label}</span>
      <input value={s[k]} onChange={(e) => set(k, e.target.value)} className="h-8 w-full border border-line bg-hover px-2.5" /></label>
  );

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try { localStorage.setItem(KEY, JSON.stringify(s)); } catch { /* private window: nothing remembered */ }
    downloadXlsx(importId, s).then(onClose).catch((err: Error) => { setError(err.message); setBusy(false); });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.45)" }} role="dialog" aria-modal="true" aria-label="Export Excel">
      <form onSubmit={submit} className="w-[460px] max-w-[95vw] space-y-3 border border-line bg-paper p-5">
        <h2 className="text-[16px] font-medium">Export Excel — page de garde</h2>
        <p className="text-label text-mute">Client, projet, référence et date sont déduits de l'analyse. Complète seulement ce qui manque.</p>
        <div className="grid grid-cols-3 gap-3">
          <div>{text("edition", "Édition")}</div>
          <div className="col-span-2">{text("subtitle", "Sous-titre")}</div>
        </div>
        <label className="block space-y-1"><span className="label">Classification du document</span>
          <select value={s.classification} onChange={(e) => set("classification", e.target.value as ExportSettings["classification"])} className="h-8 w-full border border-line bg-hover px-2">
            {CLASSIFICATIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <label className="block space-y-1"><span className="label">Export control</span>
          <select value={s.export_control} onChange={(e) => set("export_control", e.target.value as ExportSettings["export_control"])} className="h-8 w-full border border-line bg-hover px-2">
            {CONTROLS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        {text("redactor", "Rédaction")}
        {text("project_manager", "Vérification (Project Manager)")}
        {text("quality_manager", "Approbation qualité (Quality Manager)")}
        {error && <p role="alert" className="text-danger">{error}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="btn" onClick={onClose}>Annuler</button>
          <button type="submit" className="btn bg-blue text-paper hover:bg-blue" disabled={busy}>{busy ? "Export…" : "Exporter"}</button>
        </div>
      </form>
    </div>
  );
}
