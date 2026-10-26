"""Excel export of an analysed harness (built on the server, from the stored model)."""
from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HEAD_FILL = PatternFill("solid", fgColor="12293A")
HEAD_FONT = Font(bold=True, color="FFFFFF")
SEVERITY_FILL = {"error": PatternFill("solid", fgColor="FBE9E9"), "warning": PatternFill("solid", fgColor="FBF3DC")}


def _sheet(wb: Workbook, title: str, head: list[str], rows: list[list], fills: list[PatternFill | None] | None = None) -> None:
    ws = wb.create_sheet(title)
    ws.append(head)
    for c in ws[1]:
        c.fill, c.font = HEAD_FILL, HEAD_FONT
    for i, r in enumerate(rows):
        ws.append(r)
        if fills and fills[i]:
            for c in ws[ws.max_row]:
                c.fill = fills[i]
    for i, h in enumerate(head, 1):
        width = max([len(str(h))] + [len(str(r[i - 1])) for r in rows if i - 1 < len(r) and r[i - 1] is not None]) + 2
        ws.column_dimensions[get_column_letter(i)].width = min(width, 70)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(vertical="top", wrap_text=False)


def build_workbook(model: dict) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    flagged = {(r.get("conn"), r.get("pin")) for i in model["issues"] if i["severity"] == "error" for r in i["refs"] if r.get("pin")}
    segs = {s["id"]: s for s in (model.get("topology") or {}).get("segments", [])}

    rows, fills = [], []
    for w in sorted(model["wires"], key=lambda w: w["conductorId"]):
        to = w.get("to") or {}
        route = model["routes"].get(w["pairId"], [])
        diam = [segs[s]["diameterMm"] for s in route if s in segs]
        rows.append([w["conductorId"], w["pairId"], w["polarity"], w["signal"], w["nomRed"], w.get("type"),
                     w["from"]["conn"], w["from"]["pin"], to.get("conn"), to.get("pin"),
                     " > ".join(route) if route else "NON ROUTÉ", max((d for d in diam if d), default=None)])
        bad = (w["from"]["conn"], w["from"]["pin"]) in flagged or (to.get("conn"), to.get("pin")) in flagged or not route
        fills.append(SEVERITY_FILL["error"] if bad else None)
    _sheet(wb, "From-To", ["Fil", "Paire", "Polarité", "Signal", "Nom/Red", "Type", "De connecteur", "De pin", "Vers connecteur",
                           "Vers pin", "Segments", "Ø max (mm)"], rows, fills)

    rows, fills = [], []
    for c in model["connectors"]:
        for k in c["contacts"]:
            bad = (c["id"], k["pin"]) in flagged
            rows.append([c["ref"], c["partNumber"], k["pin"], ", ".join(k["wireIds"]), k.get("origin") or k.get("dest"), k.get("wire")])
            fills.append(SEVERITY_FILL["error"] if bad else None)
    _sheet(wb, "Connecteurs", ["Connecteur", "Référence", "Pin", "Fils", "Origine / destination (plan)", "N° fil (plan)"], rows, fills)

    _sheet(wb, "Segments", ["Segment", "Nœud A", "Nœud B", "Ø (mm)", "Repères nomenclature", "Longueur (pt plan)"],
           [[s["id"], s["a"], s["b"], s["diameterMm"], " / ".join(s["bomItems"]), s["lengthPt"]] for s in segs.values()])
    _sheet(wb, "Nomenclature", ["Pos", "Référence", "Description", "Quantité", "Unité", "Notes", "TBD"],
           [[b["position"], b["partNumber"], b["description"], b["amount"], b["unit"], b["notes"], "oui" if b["tbd"] else ""] for b in model["bom"]])
    order = {"error": 0, "warning": 1, "info": 2}
    issues = sorted(model["issues"], key=lambda i: order[i["severity"]])
    _sheet(wb, "Rapport", ["Gravité", "Code", "Message"], [[i["severity"], i["code"], i["message"]] for i in issues],
           [SEVERITY_FILL.get(i["severity"]) for i in issues])

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
