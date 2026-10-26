"""Beyond Gravity plugin: drawing (sheet 2 schematic) + parts list -> HarnessModel."""
from __future__ import annotations

from pathlib import Path

from app.core.pdf.extract import extract_pdf
from app.core.pdf.svgpath import page_paths
from app.plugins.model import Box, Cell, Connector, Sheet, Contact, Endpoint, HarnessModel, Issue, Wire

from .bom import parse_bom
from .checks import capacity, conn_id, count_checks, crosscheck, label_checks
from .netlist import SRC_ANCHOR, parse_schematic
from .topology import extract_topology, route_wires

PLUGIN_ID = "beyond_gravity"


def _find_schematic_page(pages):
    best = max(pages, key=lambda p: sum(1 for w in p.words if SRC_ANCHOR.match(w.t)))
    return best


def _cell(w) -> Cell:
    return Cell(t=w.t, x0=w.x0, y0=w.y0, x1=w.x1, y1=w.y1)


def parse(drawing: str | Path, bom: str | Path) -> HarnessModel:
    pages = extract_pdf(drawing)
    sheet = _find_schematic_page(pages)
    res = parse_schematic(sheet)
    items, part_no = parse_bom(extract_pdf(bom, drawings=False))

    issues: list[Issue] = list(res.issues)
    connectors: list[Connector] = []
    wires: list[Wire] = []
    dst_rows = {(conn_id(b), r.pin): r for b in res.blocks if b.kind == "dst" for r in b.rows if r.pin is not None}

    def box(r, page: int, role: str) -> Box:
        x0, y0, x1, y1 = r.bbox()
        return Box(page=page, x0=x0, y0=y0, x1=x1, y1=y1, role=role)  # type: ignore[arg-type]

    for b in res.blocks:
        cid = conn_id(b)
        contacts = [Contact(pin=r.pin, polarity=r.polarity, signal=r.signal, nomRed=r.nom_red,
                            dest=f"{r.dest[0]}:{r.dest[1]}" if r.dest else None,
                            origin=r.anchor.t if b.kind == "dst" else None, wire=r.wire,
                            cells=[_cell(w) for w in r.row_words()],
                            wireCell=_cell(r.wire_word) if r.wire_word else None)
                    for r in b.rows if r.pin is not None]
        connectors.append(Connector(id=cid, ref=b.name, partNumber=b.part_number,
                                    capacity=capacity(b.part_number), contacts=contacts,
                                    page=b.header.page, header=[_cell(w) for w in b.title]))
        if b.kind != "src":
            continue
        for r in b.rows:
            if r.pin is None or r.polarity is None or not r.wire:
                continue
            marks = [box(r, sheet.index, "from")]
            if r.dest and (d := dst_rows.get(r.dest)) is not None:
                marks.append(box(d, sheet.index, "to"))
            wires.append(Wire(id=r.wire, marks=marks, conductorId=f"{r.wire}{r.polarity}", type=res.wire_type,
                              pairId=r.wire, polarity=r.polarity, signal=r.signal or "",
                              nomRed=r.nom_red or "", **{"from": Endpoint(conn=cid, pin=r.pin)},
                              to=Endpoint(conn=r.dest[0], pin=r.dest[1]) if r.dest else None))
    by_conn = {c.id: c for c in connectors}
    for w in wires:
        for ep in (w.from_, w.to):
            if ep and ep.conn in by_conn:
                for c in by_conn[ep.conn].contacts:
                    if c.pin == ep.pin:
                        c.wireIds.append(w.conductorId)

    issues += crosscheck(res.blocks)
    issues += label_checks(res.blocks, items)
    cids = [w.conductorId for w in wires]
    for cid in {c for c in cids if cids.count(c) > 1}:
        issues.append(Issue(severity="error", code="duplicate-conductor", message=f"Conductor {cid} defined more than once"))
    pairs = {w.pairId for w in wires}
    extra, stats = count_checks(res.blocks, len(wires), len(pairs), items)
    issues += extra
    used = {(w.t, round(w.x0, 1), round(w.y0, 1)) for b in res.blocks for w in b.title}
    for b in res.blocks:
        for r in b.rows:
            used |= {(w.t, round(w.x0, 1), round(w.y0, 1)) for w in (*r.row_words(), *([r.wire_word] if r.wire_word else []))}
    free = [_cell(w) for w in sheet.words if (w.t, round(w.x0, 1), round(w.y0, 1)) not in used]
    model = HarnessModel(plugin=PLUGIN_ID, partNumber=part_no, connectors=connectors, wires=wires,
                         bom=items, issues=issues, graphics={str(sheet.index): page_paths(sheet)},
                         sheets={str(sheet.index): Sheet(width=sheet.width, height=sheet.height, texts=free)})
    others = [p for p in pages if p is not sheet]
    diam_page = max(others, key=lambda p: sum(1 for w in p.words if w.t == "mm"), default=None)
    if diam_page is not None and not any(w.t == "mm" for w in diam_page.words):
        diam_page = None
    topo_page = max((p for p in others if p is not diam_page),
                    key=lambda p: sum(1 for w in p.words if w.color == 0xFF0000 and w.t.isdigit()), default=None)
    if topo_page is None or not any(w.color == 0xFF0000 and w.t.isdigit() for w in topo_page.words):
        model.topology = {"status": "not-found"}
        model.issues.append(Issue(severity="error", code="topo-sheet-missing", message="No topology sheet (red node numbers) found"))
    else:
        topology, t_issues, internal = extract_topology(topo_page, diam_page)
        topology["pages"] = {"schematic": sheet.index, "topology": topo_page.index,
                             "diameters": diam_page.index if diam_page is not None else None}
        routes, r_issues = route_wires(wires, topology, internal, lambda c: "_".join(c.split("_")[:2]))
        model.issues += t_issues + r_issues
        unrouted = sorted({w.pairId for w in wires} - set(routes))
        if unrouted:
            model.issues.append(Issue(severity="error", code="unrouted", message=f"{len(unrouted)} pairs not routed: {', '.join(unrouted)}"))
        model.topology, model.routes = topology, routes
    model.topology = {**(model.topology or {}), "stats": stats}
    return model
