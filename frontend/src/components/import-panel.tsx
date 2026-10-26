"use client";

import { useEffect, useState } from "react";
import { importHarness, listPlugins } from "@/lib/api";
import type { HarnessModel, PluginInfo, SourceFiles } from "@/lib/types";

export function ImportPanel({ onLoaded }: { onLoaded: (m: HarnessModel, files: SourceFiles) => void }) {
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [plugin, setPlugin] = useState("");
  const [files, setFiles] = useState<Record<string, File>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const info = plugins.find((p) => p.id === plugin);

  useEffect(() => {
    listPlugins().then((p) => { setPlugins(p); setPlugin(p[0]?.id ?? ""); }).catch((e: Error) => setError(e.message));
  }, []);

  const run = async () => {
    setBusy(true);
    setError(null);
    try { onLoaded(await importHarness(plugin, files), { drawing: files.drawing, bom: files.bom }); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <section className="space-y-3 border-b border-line p-4">
      <div className="label">Import</div>
      <select aria-label="Plugin client" value={plugin} onChange={(e) => { setPlugin(e.target.value); setFiles({}); }} className="h-8 w-full border border-line bg-paper px-2">
        {plugins.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
      </select>
      {info?.inputs.map((inp) => (
        <label key={inp.role}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) setFiles({ ...files, [inp.role]: f }); }}
          className="block cursor-pointer border border-dashed border-sky bg-hover p-3 hover:bg-veil">
          <span className="label block">{inp.label}</span>
          <span className="block truncate font-mono">{files[inp.role]?.name ?? "Glisser un PDF ou cliquer"}</span>
          <input type="file" accept={inp.accept} className="sr-only" onChange={(e) => { const f = e.target.files?.[0]; if (f) setFiles({ ...files, [inp.role]: f }); }} />
        </label>
      ))}
      <button type="button" className="btn-primary w-full" disabled={busy || !info || info.inputs.some((i) => !files[i.role])} onClick={run}>
        {busy ? "Analyse…" : "Analyser"}
      </button>
      {error && <p role="alert" className="border border-danger bg-danger-bg p-2 text-danger">{error}</p>}
      <p className="text-label text-mute">Traitement local : les PDF ne quittent pas cette machine.</p>
    </section>
  );
}
