"use client";

import { useMemo, useRef, useState } from "react";
import { downloadXlsx } from "@/lib/api";
import { buildFlags, counts } from "@/lib/flags";
import { exportCsv, exportJson, exportSvg } from "@/lib/export";
import type { HarnessModel, Issue, Selection, SourceFiles } from "@/lib/types";
import { CablageView } from "./cablage-view";
import { useSession } from "./auth-gate";
import { HistoryPanel } from "./history-panel";
import { ConnectorsView } from "./connectors-view";
import { DrawingView } from "./drawing-view";
import { HarnessView } from "./harness-view";
import { ImportPanel } from "./import-panel";
import { InfoPanel } from "./info-panel";
import { ReportView } from "./report-view";

type Tab = "harness" | "connectors" | "cablage" | "drawing" | "report";
const TABS: [Tab, string][] = [["harness", "Faisceau"], ["connectors", "Connecteurs"], ["cablage", "Câblage"], ["drawing", "Dessin"], ["report", "Rapport"]];

export function AppShell() {
  const [model, setModel] = useState<HarnessModel | null>(null);
  const [files, setFiles] = useState<SourceFiles>({});
  const [refresh, setRefresh] = useState(0);
  const [importId, setImportId] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const { user, logout } = useSession();
  const [tab, setTab] = useState<Tab>("report");
  const [sel, setSel] = useState<Selection>({});
  const [query, setQuery] = useState("");
  const [labels, setLabels] = useState(true);
  const svgRef = useRef<SVGSVGElement>(null);
  const flags = useMemo(() => (model ? buildFlags(model) : null), [model]);
  const c = model ? counts(model.issues) : null;

  const search = (q: string) => {
    setQuery(q);
    const s = q.trim().toLowerCase();
    const hit = s && model?.wires.find((w) => w.conductorId.toLowerCase() === s || w.id.toLowerCase() === s || w.signal.toLowerCase().includes(s));
    if (hit) setSel({ conductorId: hit.conductorId, conn: hit.from.conn, pin: hit.from.pin });
  };
  const openIssue = (i: Issue) => {
    const r = i.refs[0];
    if (r?.segment) { setSel({ segment: r.segment }); setTab("harness"); return; }
    if (r?.conn) {
      const w = model?.wires.find((x) => (x.from.conn === r.conn && x.from.pin === r.pin) || (x.to?.conn === r.conn && x.to?.pin === r.pin));
      setSel({ conn: r.conn, ...(r.pin ? { pin: r.pin } : {}), ...(w ? { conductorId: w.conductorId } : {}) });
      setTab("connectors");
    }
  };

  return (
    <div className="flex h-screen flex-col">
      <div className="h-1 bg-[linear-gradient(90deg,var(--blue)_33%,var(--paper)_33%_66%,var(--red)_66%)]" />
      <header className="flex items-center gap-4 bg-deep px-4 py-2 text-paper">
        <h1 className="text-[18px] font-medium tracking-[0.18em]">ARIANE</h1>
        <span className="text-label opacity-70">{model ? `${model.plugin} · ${model.partNumber ?? ""}` : "Plans de faisceau"}</span>
        <div className="ml-auto flex items-center gap-2">
          {user && <span className="text-label opacity-80">{user.label} · {user.username}</span>}
          {logout && <button type="button" className="btn border-paper/40 bg-transparent text-paper hover:bg-paper/10" onClick={logout}>Déconnexion</button>}
          {c && (
            <>
              <span className="pill bg-danger text-paper">{c.error} erreurs</span>
              <span className="pill bg-warn text-paper">{c.warning} alertes</span>
            </>
          )}
        </div>
      </header>
      <div className="flex min-h-0 flex-1">
        <aside className="w-[300px] shrink-0 overflow-y-auto border-r border-line bg-paper">
          <ImportPanel onLoaded={(m, f, id) => { setModel(m); setFiles(f); setImportId(id); setSel({}); setTab("report"); setRefresh((n) => n + 1); }} />
          <HistoryPanel refreshKey={refresh} onOpen={(m, id) => { setModel(m); setFiles({}); setImportId(id); setSel({}); setTab("report"); }} />
          {model && (
            <div className="space-y-2 p-4">
              <input aria-label="Recherche" value={query} onChange={(e) => search(e.target.value)} placeholder="Fil 907-01+, signal, pin…" className="h-8 w-full border border-line bg-hover px-2.5" />
              <div className="grid grid-cols-2 gap-2">
                <button type="button" className="btn" onClick={() => exportCsv(model)}>CSV</button>
                <button type="button" className="btn" disabled={!importId}
                  onClick={() => { setExportError(null); if (importId) downloadXlsx(importId).catch((e: Error) => setExportError(e.message)); }}>Excel</button>
                <button type="button" className="btn" onClick={() => exportJson(model)}>JSON</button>
                <button type="button" className="btn col-span-2" disabled={tab !== "harness"} onClick={() => exportSvg(svgRef.current, "faisceau.svg")}>SVG de la vue</button>
              </div>
              {exportError && <p role="alert" className="text-danger">{exportError}</p>}
            </div>
          )}
        </aside>
        <main className="flex min-w-0 flex-1 flex-col">
          <nav className="flex border-b border-line bg-paper" role="tablist">
            {TABS.map(([id, label]) => (
              <button key={id} role="tab" aria-selected={tab === id} type="button" onClick={() => setTab(id)}
                className={`label border-b-2 px-4 py-3 ${tab === id ? "border-sky text-deep" : "border-transparent hover:bg-hover"}`}>{label}</button>
            ))}
            {tab === "harness" && (
              <label className="ml-auto flex items-center gap-2 px-4">
                <input type="checkbox" checked={labels} onChange={(e) => setLabels(e.target.checked)} /><span className="label">Ø / repères</span>
              </label>
            )}
          </nav>
          <div className="min-h-0 flex-1 overflow-auto">
            {!model || !flags ? (
              <p className="p-8 text-mute">Importer un plan et sa nomenclature pour afficher la netlist, la topologie et les contrôles.</p>
            ) : tab === "harness" ? (
              <HarnessView ref={svgRef} model={model} flags={flags} sel={sel} onSelect={setSel} showLabels={labels} />
            ) : tab === "cablage" ? (
              <CablageView model={model} flags={flags} sel={sel} onSelect={setSel} />
            ) : tab === "drawing" ? (
              <DrawingView model={model} flags={flags} sel={sel} onSelect={setSel} file={files.drawing} />
            ) : tab === "connectors" ? (
              <ConnectorsView model={model} flags={flags} sel={sel} onSelect={setSel} filter={query} />
            ) : (
              <ReportView model={model} onOpen={openIssue} />
            )}
          </div>
        </main>
        {model && flags && (
          <aside className="w-[340px] shrink-0 overflow-y-auto border-l border-line bg-paper">
            <InfoPanel model={model} flags={flags} sel={sel} onSelect={setSel} />
          </aside>
        )}
      </div>
    </div>
  );
}
