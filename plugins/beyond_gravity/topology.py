"""Sheet 1 (topology) + sheet 3 (diameters) -> nodes, segments, routes.

Blue strokes become a planar graph (app.core.pdf.graph). Red numbers name the branch points,
leader lines attach BOM item numbers to segments, and the diameter labels of sheet 3 attach to
the nearest segment. Whatever cannot be established is reported, never guessed silently.
"""
from __future__ import annotations

import re
from collections import defaultdict

from app.core.pdf.extract import PageData, Word
from app.core.pdf.graph import Pt, build_graph, contract, dist, point_poly, shortest_path
from app.plugins.model import Issue, Location, Ref, Wire

RED = 0xFF0000
WIRE_STROKE = (0.0, 0.0, 1.0)
WIRE_WIDTH = (1.5, 3.0)
BOM_LABEL = re.compile(r"^\d{2}$")
ROUTED_ITEMS = {"07", "08", "09", "10"}  # cable and braids carried by segments
DIAM = re.compile(r"^\d+(?:\.\d+)?$")
S_C_TITLE = re.compile(r"#x-(\d+)")
INIT_TITLE = re.compile(r"^INIT$")


def _is_wire(d) -> bool:
    return (d.stroke is not None and tuple(round(c, 2) for c in d.stroke) == WIRE_STROKE
            and d.width is not None and WIRE_WIDTH[0] <= d.width <= WIRE_WIDTH[1])


def _polyline(d) -> list[Pt]:
    pts: list[Pt] = []
    for it in d.items:
        for x, y in it[1:]:
            if not pts or dist(pts[-1], (x, y)) > 1e-6:
                pts.append((x, y))
    return pts


def _loc(page: int, p: Pt) -> Location:
    return Location(page=page, x=round(p[0], 1), y=round(p[1], 1))


def _titles(words: list[Word]) -> dict[str, Pt]:
    """Connector titles on the topology sheet: key ('SC1', 'INIT_A') -> centre of the title text."""
    out: dict[str, Pt] = {}
    for w in words:
        m = S_C_TITLE.fullmatch(w.t)
        if m:
            out[f"SC{m.group(1)}"] = ((w.x0 + w.x1) / 2, w.cy)
        elif INIT_TITLE.match(w.t):
            side = next((x for x in words if abs(x.cy - w.cy) < 4 and 0 < x.x0 - w.x1 < 30 and re.fullmatch(r"[A-Z]", x.t)), None)
            if side:
                out[f"INIT_{side.t}"] = ((w.x0 + side.x1) / 2, w.cy)
    return out


def extract_topology(topo: PageData, diam: PageData | None) -> tuple[dict, list[Issue], dict]:
    """Returns (topology dict, issues, internal) where internal holds the graph for routing."""
    issues: list[Issue] = []
    pno = topo.index
    polys = [_polyline(d) for d in topo.drawings if _is_wire(d)]
    g = build_graph([p for p in polys if len(p) >= 2])
    deg = g.degree()
    if not g.edges:
        issues.append(Issue(severity="error", code="topo-no-strokes", message="No blue wire strokes found on the topology sheet"))
        return {"status": "failed"}, issues, {}

    # --- red node labels -> branch vertices
    reds = [w for w in topo.words if w.color == RED and w.t.isdigit()]
    branch = [v for v, d in deg.items() if d >= 3]
    label_of: dict[int, str] = {}
    for w in reds:
        c = ((w.x0 + w.x1) / 2, w.cy)
        ranked = sorted(branch, key=lambda v: dist(c, g.pts[v]))
        if not ranked:
            continue
        v = ranked[0]
        if dist(c, g.pts[v]) > 45:
            issues.append(Issue(severity="warning", code="node-label-far",
                                message=f"Node number {w.t} is {dist(c, g.pts[v]):.0f} pt from the nearest branch point", where=[_loc(pno, c)]))
        if len(ranked) > 1 and dist(c, g.pts[ranked[1]]) < 1.25 * dist(c, g.pts[v]):
            issues.append(Issue(severity="warning", code="node-label-ambiguous",
                                message=f"Node number {w.t} is almost as close to a second branch point", where=[_loc(pno, c)]))
        if v in label_of:
            issues.append(Issue(severity="error", code="node-label-duplicate",
                                message=f"Branch point already numbered {label_of[v]}, also claimed by {w.t}", where=[_loc(pno, c)]))
        else:
            label_of[v] = w.t
    for v in branch:
        if v not in label_of:
            issues.append(Issue(severity="warning", code="node-unnumbered",
                                message="Branch point without a red number", where=[_loc(pno, g.pts[v])]))

    # --- terminals (degree 1) -> connectors by nearest title
    titles = _titles(topo.words)
    terminals = {v for v, d in deg.items() if d == 1}
    conn_of: dict[int, str] = {}
    for v in terminals:
        if not titles:
            break
        k = min(titles, key=lambda k: dist(g.pts[v], titles[k]))
        conn_of[v] = k
    for k in titles:
        if k not in conn_of.values():
            issues.append(Issue(severity="error", code="connector-unattached",
                                message=f"Connector {k} has no wire end", where=[_loc(pno, titles[k])]))
    dup = defaultdict(list)
    for v, k in conn_of.items():
        dup[k].append(v)
    for k, vs in dup.items():
        if len(vs) > 1:
            issues.append(Issue(severity="error", code="connector-multi-ends",
                                message=f"Connector {k} would own {len(vs)} wire ends", where=[_loc(pno, g.pts[v]) for v in vs]))

    keep = set(label_of) | terminals
    segs = contract(g, keep)

    # --- node ids: unique label -> N<label>; repeated label -> N<label>A/B, side = INIT trunk of its tree
    count: dict[str, int] = defaultdict(int)
    for lab in label_of.values():
        count[lab] += 1
    node_id: dict[int, str] = {}
    dup_nodes = {v for v, lab in label_of.items() if count[lab] > 1}
    comp = {v: v for v in dup_nodes}

    def find(v: int) -> int:
        while comp[v] != v:
            comp[v] = comp[comp[v]]
            v = comp[v]
        return v
    for s in segs:
        if s.a in dup_nodes and s.b in dup_nodes:
            comp[find(s.a)] = find(s.b)
    side_of_comp: dict[int, str] = {}
    for s in segs:
        for t, n in ((s.a, s.b), (s.b, s.a)):
            if conn_of.get(t, "").startswith("INIT") and n in dup_nodes:
                side_of_comp[find(n)] = conn_of[t][-1]
    for v, lab in label_of.items():
        if count[lab] == 1:
            node_id[v] = f"N{lab}"
        else:
            side = side_of_comp.get(find(v))
            if side is None:
                side = "?"
                issues.append(Issue(severity="warning", code="node-side-unknown",
                                    message=f"Node {lab}: cannot tell which INIT trunk its tree reaches", where=[_loc(pno, g.pts[v])]))
            node_id[v] = f"N{lab}{side}"
    for v, k in conn_of.items():
        node_id[v] = k
    for v in range(len(g.pts)):
        node_id.setdefault(v, f"V{v}")
    seen_ids: dict[str, int] = {}
    for v, nid in node_id.items():
        if nid in seen_ids and v in label_of:
            issues.append(Issue(severity="error", code="node-id-collision", message=f"Two branch points resolve to {nid}",
                                where=[_loc(pno, g.pts[v])]))
        seen_ids[nid] = v

    # --- BOM items via leader lines (thin black), diameters via proximity
    leaders = [_polyline(d) for d in topo.drawings
               if d.stroke == (0.0, 0.0, 0.0) and d.width and d.width < 1.0 and len(d.items) == 1 and d.items[0][0] == "l"]
    leaders = [p for p in leaders if len(p) == 2 and dist(p[0], p[1]) >= 8]
    seg_items: dict[int, list[str]] = defaultdict(list)
    for w in topo.words:
        if w.t not in ROUTED_ITEMS or w.color:
            continue
        box = (w.x0 - 14, w.y0 - 14, w.x1 + 14, w.y1 + 24)
        best = None
        for p in leaders:
            for near, far in ((p[0], p[1]), (p[1], p[0])):
                if box[0] <= near[0] <= box[2] and box[1] <= near[1] <= box[3]:
                    si, d = min(((i, min(point_poly(far, e.poly) for e in s.pieces)) for i, s in enumerate(segs)), key=lambda t: t[1])
                    if d <= 3.5 and (best is None or d < best[1]):
                        best = (si, d)
        if best is None:
            issues.append(Issue(severity="warning", code="bom-leader-missing",
                                message=f"BOM number {w.t}: no leader line reaching a wire segment", where=[_loc(pno, (w.x0, w.cy))]))
        elif w.t not in seg_items[best[0]]:
            seg_items[best[0]].append(w.t)

    seg_diam: dict[int, list[str]] = defaultdict(list)
    if diam is not None:
        for w in diam.words:
            if DIAM.match(w.t):
                nxt = next((x for x in diam.words if x.t == "mm" and abs(x.cy - w.cy) < 3 and 0 <= x.x0 - w.x1 < 12), None)
                if not nxt:
                    continue
                c = ((w.x0 + nxt.x1) / 2, w.cy)
                ranked = sorted((dist(c, _midpoint(s.poly)), i) for i, s in enumerate(segs))
                d0, i0 = ranked[0]
                if len(ranked) > 1 and ranked[1][0] < d0 * 1.3 + 3:
                    issues.append(Issue(severity="warning", code="diameter-ambiguous",
                                        message=f"Diameter {w.t} mm sits between two segments ({ranked[0][0]:.0f} / {ranked[1][0]:.0f} pt)",
                                        where=[_loc(diam.index, c)]))
                seg_diam[i0].append(w.t)

    out_segs = []
    for i, s in enumerate(segs):
        ds = seg_diam.get(i, [])
        if len(set(ds)) > 1:
            issues.append(Issue(severity="error", code="diameter-conflict",
                                message=f"Segment {node_id[s.a]}-{node_id[s.b]} gets several diameters: {ds}", where=[_loc(pno, s.poly[0])], refs=[Ref(segment=f"S{i + 1:02d}")]))
        if not ds:
            issues.append(Issue(severity="warning", code="diameter-missing",
                                message=f"Segment {node_id[s.a]}-{node_id[s.b]}: no diameter on the diameter sheet", where=[_loc(pno, s.poly[len(s.poly) // 2])],
                                refs=[Ref(segment=f"S{i + 1:02d}")]))
        if not seg_items.get(i):
            issues.append(Issue(severity="info", code="segment-no-bom",
                                message=f"Segment {node_id[s.a]}-{node_id[s.b]}: no BOM item attached by a leader line",
                                where=[_loc(pno, _midpoint(s.poly))], refs=[Ref(segment=f"S{i + 1:02d}")]))
        out_segs.append({"id": f"S{i + 1:02d}", "a": node_id[s.a], "b": node_id[s.b],
                         "diameterMm": float(ds[0]) if ds else None,
                         "bomItems": seg_items.get(i, []), "lengthPt": round(s.length, 1),
                         "polyline": [[round(x, 1), round(y, 1)] for x, y in s.poly]})
    nodes = [{"id": node_id[v], "label": label_of.get(v), "connector": conn_of.get(v),
              "x": round(g.pts[v][0], 1), "y": round(g.pts[v][1], 1)}
             for v in sorted(keep, key=lambda v: node_id[v])]
    topology = {"status": "ok", "nodes": nodes, "segments": out_segs}
    return topology, issues, {"graph": g, "segs": segs, "vertex_of_conn": {k: v for v, k in conn_of.items()}}


def _midpoint(poly: list[Pt]) -> Pt:
    """Point at half the arc length: diameter labels sit next to the middle of their segment."""
    total = sum(dist(poly[i], poly[i + 1]) for i in range(len(poly) - 1))
    acc = 0.0
    for i in range(len(poly) - 1):
        d = dist(poly[i], poly[i + 1])
        if acc + d >= total / 2 and d > 0:
            t = (total / 2 - acc) / d
            return (poly[i][0] + t * (poly[i + 1][0] - poly[i][0]), poly[i][1] + t * (poly[i + 1][1] - poly[i][1]))
        acc += d
    return poly[0]


def _dist_map(segs, src: int) -> dict[int, float]:
    import heapq
    adj: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for s in segs:
        adj[s.a].append((s.b, s.length))
        adj[s.b].append((s.a, s.length))
    best = {src: 0.0}
    h = [(0.0, src)]
    while h:
        d, v = heapq.heappop(h)
        if d > best[v]:
            continue
        for w, l in adj[v]:
            if d + l < best.get(w, 1e18):
                best[w] = d + l
                heapq.heappush(h, (d + l, w))
    return best


def route_wires(wires: list[Wire], topology: dict, internal: dict, init_key) -> tuple[dict[str, list[str]], list[Issue]]:
    """One route per twisted pair (both conductors share it); unroutable pairs are reported."""
    issues: list[Issue] = []
    routes: dict[str, list[str]] = {}
    if topology.get("status") != "ok":
        return routes, [Issue(severity="error", code="route-no-topology", message="No topology: no wire can be routed")]
    segs, vmap = internal["segs"], internal["vertex_of_conn"]
    for w in wires:
        if w.pairId in routes or w.to is None:
            continue
        a, b = vmap.get(w.from_.conn), vmap.get(init_key(w.to.conn))
        if a is None or b is None:
            issues.append(Issue(severity="error", code="route-unresolved",
                                message=f"{w.id}: no topology end for {w.from_.conn if a is None else w.to.conn}"))
            continue
        path = shortest_path(segs, a, b)
        if path is None:
            issues.append(Issue(severity="error", code="route-disconnected",
                                message=f"{w.id}: {w.from_.conn} and {w.to.conn} are not connected on the topology sheet",
                                refs=[Ref(wire=w.pairId)]))
        else:
            routes[w.pairId] = [f"S{i + 1:02d}" for i in path]
    return routes, issues
