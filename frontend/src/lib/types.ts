export type Severity = "error" | "warning" | "info";

export interface Ref { conn?: string | null; pin?: string | null; segment?: string | null; node?: string | null; wire?: string | null }
export interface Location { page: number; x: number; y: number }
export interface Issue { severity: Severity; code: string; message: string; where: Location[]; refs: Ref[] }
export interface Cell { t: string; x0: number; y0: number; x1: number; y1: number }
export interface Contact {
  cells?: Cell[]; wireCell?: Cell | null;
  pin: string; wireIds: string[]; polarity?: string | null; signal?: string | null; nomRed?: string | null;
  dest?: string | null; origin?: string | null; wire?: string | null;
}
export interface Connector {
  id: string; ref: string; partNumber: string; capacity: number | null; contacts: Contact[];
  page?: number | null; header?: Cell[];
}
export interface Endpoint { conn: string; pin: string }
export interface Box { page: number; x0: number; y0: number; x1: number; y1: number; role: "from" | "to" }
export interface Wire {
  id: string; conductorId: string; type: string | null; pairId: string; polarity: "+" | "-";
  signal: string; nomRed: string; from: Endpoint; to: Endpoint | null; marks: Box[];
}
export interface BomItem { position: string; partNumber: string; description: string; amount: string; unit: string; notes: string; tbd: boolean }
export interface TopoNode { id: string; label: string | null; connector: string | null; x: number; y: number }
export interface TopoSegment {
  id: string; a: string; b: string; diameterMm: number | null; bomItems: string[]; lengthPt: number; polyline: [number, number][];
}
export interface SheetPages { schematic: number; topology: number; diameters: number | null }
export interface Topology { status: string; pages?: SheetPages; nodes?: TopoNode[]; segments?: TopoSegment[]; stats?: Record<string, unknown> }
export interface GPath { d: string; c: string | null; w: number; f: string | null }
export interface HarnessModel {
  graphics?: Record<string, GPath[]>;
  plugin: string; partNumber: string | null; connectors: Connector[]; wires: Wire[]; bom: BomItem[];
  topology: Topology | null; routes: Record<string, string[]>; issues: Issue[];
}
export interface PluginInfo { id: string; label: string; version: string; inputs: { role: string; label: string; accept: string }[] }

/** What the user has picked; every view reads it, so a click anywhere highlights everywhere. */
export interface Selection { conductorId?: string; conn?: string; pin?: string; segment?: string }

export interface SourceFiles { drawing?: File; bom?: File }
