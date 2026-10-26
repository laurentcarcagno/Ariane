import type { HarnessModel, Issue, Severity } from "./types";

const RANK: Record<Severity, number> = { error: 3, warning: 2, info: 1 };

export interface Flag { severity: Severity; issues: Issue[] }
export type FlagMap = Map<string, Flag>;

export const pinKey = (conn: string, pin: string): string => `${conn}\u0000${pin}`;

function add(map: FlagMap, key: string, issue: Issue): void {
  const cur = map.get(key);
  if (!cur) { map.set(key, { severity: issue.severity, issues: [issue] }); return; }
  cur.issues.push(issue);
  if (RANK[issue.severity] > RANK[cur.severity]) cur.severity = issue.severity;
}

export interface Flags { pins: FlagMap; connectors: FlagMap; segments: FlagMap; wires: FlagMap }

/** Index every issue by the model entity it points at, so views can paint red/amber indicators. */
export function buildFlags(model: HarnessModel): Flags {
  const f: Flags = { pins: new Map(), connectors: new Map(), segments: new Map(), wires: new Map() };
  for (const issue of model.issues) {
    for (const r of issue.refs) {
      if (r.conn && r.pin) add(f.pins, pinKey(r.conn, r.pin), issue);
      if (r.conn) add(f.connectors, r.conn, issue);
      if (r.segment) add(f.segments, r.segment, issue);
      if (r.wire) add(f.wires, r.wire, issue);
    }
  }
  return f;
}

export const worst = (a: Severity | undefined, b: Severity): Severity => (a && RANK[a] >= RANK[b] ? a : b);

/** Topology connector key for a netlist connector id ("INIT_A_P1" -> "INIT_A", "SC1" -> "SC1"). */
export const topoKey = (connId: string): string =>
  connId.startsWith("INIT") ? connId.split("_").slice(0, 2).join("_") : connId;

export const counts = (issues: Issue[]): Record<Severity, number> =>
  issues.reduce((c, i) => ({ ...c, [i.severity]: c[i.severity] + 1 }), { error: 0, warning: 0, info: 0 });
