"use client";

import { pinKey, type Flags } from "@/lib/flags";
import type { HarnessModel, Selection } from "@/lib/types";

export function InfoPanel({ model, flags, sel, onSelect }: { model: HarnessModel; flags: Flags; sel: Selection; onSelect: (s: Selection) => void }) {
  const wire = model.wires.find((w) => w.conductorId === sel.conductorId);
  const segs = new Map((model.topology?.segments ?? []).map((s) => [s.id, s]));
  const same = sel.conn && sel.pin
    ? model.wires.filter((w) => (w.from.conn === sel.conn && w.from.pin === sel.pin) || (w.to?.conn === sel.conn && w.to?.pin === sel.pin))
    : [];
  const pinFlag = sel.conn && sel.pin ? flags.pins.get(pinKey(sel.conn, sel.pin)) : undefined;
  const partner = wire ? model.wires.find((w) => w.pairId === wire.pairId && w.conductorId !== wire.conductorId) : undefined;
  const route = wire ? model.routes[wire.pairId] : undefined;
  const row = (k: string, v: React.ReactNode) => (
    <div className="flex justify-between gap-3 border-b border-line py-1"><dt className="label">{k}</dt><dd className="text-right font-mono">{v}</dd></div>
  );

  if (!wire && !sel.conn && !sel.segment) return <p className="p-4 text-mute">Cliquer un connecteur, une pin ou un fil.</p>;
  const seg = sel.segment ? segs.get(sel.segment) : undefined;
  const segFlag = sel.segment ? flags.segments.get(sel.segment) : undefined;
  return (
    <div className="space-y-4 p-4">
      {seg && (
        <div>
          <h2 className="text-[18px] font-medium tracking-[0.04em]">Segment {seg.id}</h2>
          <dl>
            {row("Nœuds", `${seg.a} – ${seg.b}`)}
            {row("Diamètre", seg.diameterMm !== null ? `Ø ${seg.diameterMm} mm` : "non renseigné")}
            {row("Repères", seg.bomItems.join(" / ") || "–")}
          </dl>
          {segFlag && <ul className="mt-2 list-disc border border-warn bg-warn-bg p-3 pl-7 text-warn">{segFlag.issues.map((i, k) => <li key={k}>{i.message}</li>)}</ul>}
        </div>
      )}
      {pinFlag && (
        <div className="border border-danger bg-danger-bg p-3 text-danger">
          <div className="label text-danger">Pin {sel.pin} — à vérifier</div>
          <ul className="mt-1 list-disc pl-4">{pinFlag.issues.map((i, k) => <li key={k}>{i.message}</li>)}</ul>
        </div>
      )}
      {same.length > 1 && (
        <div className="border border-warn bg-warn-bg p-3">
          <div className="label text-warn">{same.length} fils sur cette pin</div>
          {same.map((w) => (
            <button key={w.conductorId} type="button" className="mr-2 mt-1 font-mono underline" onClick={() => onSelect({ ...sel, conductorId: w.conductorId })}>{w.conductorId}</button>
          ))}
        </div>
      )}
      {wire && (
        <>
          <h2 className="text-[18px] font-medium tracking-[0.04em]">Fil {wire.conductorId}</h2>
          <dl>
            {row("Signal", `${wire.signal} ${wire.nomRed}`)}
            {row("Polarité", wire.polarity)}
            {row("Type", wire.type ?? "–")}
            {row("Départ", `${wire.from.conn}:${wire.from.pin}`)}
            {row("Arrivée", wire.to ? `${wire.to.conn}:${wire.to.pin}` : "–")}
            {partner && row("Paire", (
              <button type="button" className="underline" onClick={() => onSelect({ conductorId: partner.conductorId })}>
                {partner.conductorId} ({partner.from.conn}:{partner.from.pin} → {partner.to?.conn}:{partner.to?.pin})
              </button>
            ))}
          </dl>
          <div>
            <div className="label mb-1">Chemin ({route?.length ?? 0} segments)</div>
            {route ? (
              <ol className="border border-line bg-paper">
                {route.map((id) => {
                  const s = segs.get(id);
                  const f = flags.segments.get(id);
                  return (
                    <li key={id} className="flex items-center justify-between gap-2 border-b border-line px-2 py-1 font-mono last:border-0">
                      <span>{s ? `${s.a} → ${s.b}` : id}</span>
                      <span className={f ? "text-warn" : "text-dim"}>
                        {s?.diameterMm != null ? `Ø${s.diameterMm}` : "Ø ?"}{s?.bomItems.length ? ` · ${s.bomItems.join("/")}` : ""}{f ? " ⚠" : ""}
                      </span>
                    </li>
                  );
                })}
              </ol>
            ) : <p className="border border-danger bg-danger-bg p-2 text-danger">Non routé : voir le rapport.</p>}
          </div>
        </>
      )}
    </div>
  );
}
