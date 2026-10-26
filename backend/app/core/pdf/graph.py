"""Vector polylines -> planar graph (vertices, edges), then contraction into segments.

Rules: endpoints within ``merge_tol`` are one vertex; an endpoint lying on the interior of a
straight edge splits it (T-junction); a pure crossing (no endpoint on the other line) stays
disconnected; duplicate/overlapping collinear pieces collapse into one edge.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

Pt = tuple[float, float]


def dist(a: Pt, b: Pt) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def point_seg(p: Pt, a: Pt, b: Pt) -> tuple[float, float]:
    """(distance, t) of p to segment ab, t in [0,1]."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = dx * dx + dy * dy
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n))
    return dist(p, (a[0] + t * dx, a[1] + t * dy)), t


def point_poly(p: Pt, poly: list[Pt]) -> float:
    return min(point_seg(p, poly[i], poly[i + 1])[0] for i in range(len(poly) - 1))


@dataclass
class Edge:
    a: int
    b: int
    poly: list[Pt]

    @property
    def length(self) -> float:
        return sum(dist(self.poly[i], self.poly[i + 1]) for i in range(len(self.poly) - 1))


@dataclass
class Graph:
    pts: list[Pt] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def degree(self) -> dict[int, int]:
        d: dict[int, int] = {i: 0 for i in range(len(self.pts))}
        for e in self.edges:
            d[e.a] += 1
            d[e.b] += 1
        return d


def build_graph(polylines: list[list[Pt]], merge_tol: float = 2.5, line_tol: float = 1.2) -> Graph:
    g = Graph()

    def vid(p: Pt) -> int:
        for i, q in enumerate(g.pts):
            if dist(p, q) <= merge_tol:
                return i
        g.pts.append(p)
        return len(g.pts) - 1

    for poly in polylines:
        if len(poly) < 2:
            continue
        a, b = vid(poly[0]), vid(poly[-1])
        if a != b:
            g.edges.append(Edge(a, b, [g.pts[a]] + poly[1:-1] + [g.pts[b]]))

    changed = True
    while changed:  # split straight edges at vertices lying on them
        changed = False
        out: list[Edge] = []
        for e in g.edges:
            if len(e.poly) == 2:
                on = []
                for i, p in enumerate(g.pts):
                    if i in (e.a, e.b):
                        continue
                    d, t = point_seg(p, e.poly[0], e.poly[1])
                    if d <= line_tol and 0.0 < t < 1.0:
                        on.append((t, i))
                if on:
                    chain = [e.a] + [i for _, i in sorted(on)] + [e.b]
                    out += [Edge(chain[k], chain[k + 1], [g.pts[chain[k]], g.pts[chain[k + 1]]])
                            for k in range(len(chain) - 1) if chain[k] != chain[k + 1]]
                    changed = True
                    continue
            out.append(e)
        seen: set[tuple[int, int]] = set()
        g.edges = []
        for e in out:  # drop duplicates from overlapping drawings
            k = (min(e.a, e.b), max(e.a, e.b))
            if k not in seen:
                seen.add(k)
                g.edges.append(e)
    return g


@dataclass
class Segment:
    a: int
    b: int
    poly: list[Pt]
    pieces: list[Edge]

    @property
    def length(self) -> float:
        return sum(p.length for p in self.pieces)


def contract(g: Graph, keep: set[int]) -> list[Segment]:
    """Chain edges through degree-2 vertices that are not in ``keep``."""
    deg = g.degree()
    adj: dict[int, list[int]] = {i: [] for i in range(len(g.pts))}
    for k, e in enumerate(g.edges):
        adj[e.a].append(k)
        adj[e.b].append(k)
    stop = {v for v, d in deg.items() if d != 2 or v in keep}
    used: set[int] = set()
    segs: list[Segment] = []
    for start in sorted(stop):
        for k0 in adj[start]:
            if k0 in used:
                continue
            chain, cur, k = [], start, k0
            poly: list[Pt] = [g.pts[start]]
            while True:
                used.add(k)
                e = g.edges[k]
                nxt = e.b if e.a == cur else e.a
                pts = e.poly if e.a == cur else e.poly[::-1]
                poly += pts[1:]
                chain.append(e)
                cur = nxt
                if cur in stop:
                    break
                k = next(x for x in adj[cur] if x not in used)
            segs.append(Segment(start, cur, poly, chain))
    return segs


def shortest_path(segs: list[Segment], src: int, dst: int) -> list[int] | None:
    """Indices of segments on the shortest (length-weighted) path from vertex src to dst."""
    adj: dict[int, list[tuple[int, int, float]]] = {}
    for i, s in enumerate(segs):
        adj.setdefault(s.a, []).append((s.b, i, s.length))
        adj.setdefault(s.b, []).append((s.a, i, s.length))
    best = {src: 0.0}
    prev: dict[int, tuple[int, int]] = {}
    h = [(0.0, src)]
    while h:
        d, v = heapq.heappop(h)
        if v == dst:
            break
        if d > best.get(v, 1e18):
            continue
        for w, i, l in adj.get(v, []):
            if d + l < best.get(w, 1e18):
                best[w] = d + l
                prev[w] = (v, i)
                heapq.heappush(h, (d + l, w))
    if dst not in best:
        return None
    path, v = [], dst
    while v != src:
        v, i = prev[v][0], prev[v][1]
        path.append(i)
    return path[::-1]
