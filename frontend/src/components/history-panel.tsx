"use client";

import { useCallback, useEffect, useState } from "react";
import { deleteImport, getImport, listImports, type ImportSummary } from "@/lib/api";
import type { HarnessModel } from "@/lib/types";

/** Earlier analyses of the signed-in customer. Only the extracted model is kept, never the PDFs. */
export function HistoryPanel({ refreshKey, onOpen }: { refreshKey: number; onOpen: (m: HarnessModel, id: string) => void }) {
  const [rows, setRows] = useState<ImportSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => { listImports().then(setRows).catch((e: Error) => setError(e.message)); }, []);
  useEffect(reload, [reload, refreshKey]);

  if (!rows.length && !error) return null;
  return (
    <section className="space-y-2 border-b border-line p-4">
      <div className="label">Analyses précédentes</div>
      {error && <p role="alert" className="text-danger">{error}</p>}
      <ul className="border border-line">
        {rows.map((r) => (
          <li key={r.id} className="flex items-center gap-1 border-b border-line last:border-0">
            <button type="button" className="min-w-0 flex-1 px-2 py-1.5 text-left hover:bg-hover"
              onClick={() => getImport(r.id).then((m) => onOpen(m, r.id)).catch((e: Error) => setError(e.message))}>
              <span className="block truncate font-mono">{r.partNumber ?? r.drawing}</span>
              <span className="block text-label text-mute">
                {new Date(r.createdAt).toLocaleString("fr-FR")} · <span className="text-danger">{r.errors} err.</span> · <span className="text-warn">{r.warnings} alertes</span>
              </span>
            </button>
            <button type="button" aria-label={`Supprimer ${r.drawing}`} className="px-2 text-mute hover:text-danger"
              onClick={() => deleteImport(r.id).then(reload).catch((e: Error) => setError(e.message))}>×</button>
          </li>
        ))}
      </ul>
    </section>
  );
}
