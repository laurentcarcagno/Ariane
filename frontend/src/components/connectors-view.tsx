"use client";

import { pinKey, type Flags } from "@/lib/flags";
import type { Connector, HarnessModel, Selection } from "@/lib/types";

interface Props { model: HarnessModel; flags: Flags; sel: Selection; onSelect: (s: Selection) => void; filter: string }

/** Case-sensitive, shortest first: "c" and "C" stay two distinct pins. */
const byPin = (a: string, b: string): number => a.length - b.length || (a < b ? -1 : a > b ? 1 : 0);

export function ConnectorsView({ model, flags, sel, onSelect, filter }: Props) {
  const wire = model.wires.find((w) => w.conductorId === sel.conductorId);
  const partner = wire ? model.wires.find((w) => w.pairId === wire.pairId && w.conductorId !== wire.conductorId) : undefined;
  const q = filter.trim().toLowerCase();

  const role = (conn: string, pin: string): "end" | "partner" | null => {
    if (wire && ((wire.from.conn === conn && wire.from.pin === pin) || (wire.to?.conn === conn && wire.to.pin === pin))) return "end";
    if (partner && ((partner.from.conn === conn && partner.from.pin === pin) || (partner.to?.conn === conn && partner.to.pin === pin))) return "partner";
    return null;
  };
  const wiresOf = (conn: string, pin: string) =>
    model.wires.filter((w) => (w.from.conn === conn && w.from.pin === pin) || (w.to?.conn === conn && w.to.pin === pin));

  return (
    <div className="grid gap-4 p-4 [grid-template-columns:repeat(auto-fill,minmax(300px,1fr))]">
      {model.connectors.map((c: Connector) => {
        const cflag = flags.connectors.get(c.id);
        const pins = [...c.contacts].sort((a, b) => byPin(a.pin, b.pin));
        const empty = c.capacity ? c.capacity - pins.length : 0;
        return (
          <section key={c.id} className={`border bg-paper ${sel.conn === c.id ? "border-sky" : "border-line"}`}>
            <header className="flex items-center justify-between bg-deep px-3 py-2 text-paper">
              <div>
                <div className="label text-paper">{c.ref}</div>
                <div className="font-mono text-label opacity-80">{c.partNumber}</div>
              </div>
              {cflag && <span className={`pill ${cflag.severity === "error" ? "bg-danger" : "bg-warn"} text-paper`}>{cflag.issues.length} à vérifier</span>}
            </header>
            <div className="flex flex-wrap gap-1.5 p-3">
              {pins.map((p) => {
                const f = flags.pins.get(pinKey(c.id, p.pin));
                const r = role(c.id, p.pin);
                const hit = q !== "" && (p.pin.toLowerCase() === q || p.wireIds.some((id) => id.toLowerCase().includes(q)));
                const tone = f?.severity === "error" ? "border-danger bg-danger-bg text-danger"
                  : f?.severity === "warning" ? "border-warn bg-warn-bg text-warn" : "border-line bg-mist text-ink";
                const ring = r === "end" ? "ring-2 ring-sky" : r === "partner" ? "ring-2 ring-veil ring-offset-1" : "";
                return (
                  <button key={p.pin} type="button"
                    onClick={() => {
                      const w = wiresOf(c.id, p.pin)[0];
                      onSelect(w ? { conductorId: w.conductorId, conn: c.id, pin: p.pin } : { conn: c.id, pin: p.pin });
                    }}
                    title={[`${c.id}:${p.pin}`, ...p.wireIds, ...(f?.issues.map((i) => `⚠ ${i.message}`) ?? [])].join("\n")}
                    className={`relative h-8 min-w-8 border px-1.5 font-mono text-body font-medium ${tone} ${ring} ${hit ? "outline outline-2 outline-blue" : ""}`}>
                    {p.pin}
                    {f && <span className={`absolute -right-1 -top-1 h-2.5 w-2.5 ${f.severity === "error" ? "bg-danger" : "bg-warn"}`} aria-hidden />}
                  </button>
                );
              })}
            </div>
            {empty > 0 && (
              <div className="border-t border-line px-3 py-2 text-label text-mute">
                {c.emptyPins?.length ? (
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span>{empty} places vides (à combler, note 5) :</span>
                    {c.emptyPins.map((p) => <span key={p} className="inline-flex h-6 min-w-6 items-center justify-center border border-dashed border-line px-1 font-mono text-ink" title={`${c.id}:${p} (place vide)`}>{p}</span>)}
                  </div>
                ) : <>{empty} places vides (à combler par des pins, note 5)</>}
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
