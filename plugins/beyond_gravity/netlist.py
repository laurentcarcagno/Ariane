"""Wiring-schematic (sheet 2) parser: blocks found from headers and token types.

No absolute coordinates: blocks are located from connector part-number headers,
rows from their anchor tokens, and cells from token regexes and relative x/y.
Nothing is corrected silently; ambiguities become Issues.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.pdf.extract import PageData, Word
from app.plugins.model import Issue, Location

CONNECTOR_PN = re.compile(r"^D38999/\w+$")
SRC_ANCHOR = re.compile(r"^S/C_#(\d+)_N(\d+)$")
DEST_SPLIT = re.compile(r"[A-Z]+_[A-Z]_P\d+:[A-Za-z]+?(?=[A-Z]+_[A-Z]_P\d+:|$)")
DEST = re.compile(r"^([A-Z]+_[A-Z]_P\d+):(\w+)$")
ORIGIN_SPLIT = re.compile(r"(?=SC_I_#)")
ORIGIN = re.compile(r"^SC_I_#x-(\d+)_J(\d+):(\w+)$")
POLARITY = re.compile(r"^[+-]$")
KIND = re.compile(r"^(Nom|Red)$")
PIN = re.compile(r"^[A-Za-z]{1,2}$")
WIRE_NO = re.compile(r"^(\d{3})-(\d{2})$")
WIRES_TYPE = re.compile(r"^TSP-\d+$")
ROW_TOL = 7.0
COL_TOL = 25.0


@dataclass
class Row:
    kind: str  # "src" | "dst"
    anchor: Word
    page: int
    block: "Block | None" = None
    polarity: str | None = None
    signal: str | None = None
    nom_red: str | None = None
    pin: str | None = None
    dest: tuple[str, str] | None = None  # (connector, pin) in src rows
    origin: tuple[str, str, str] | None = None  # (sc number, J, pin) in dst rows
    wire: str | None = None
    pin_cands: list[Word] = field(default_factory=list)
    dest_x: float | None = None
    cells: list[Word] = field(default_factory=list)
    wire_word: Word | None = None
    pin_word: Word | None = None

    @property
    def y(self) -> float:
        return self.anchor.cy

    def row_words(self) -> list[Word]:
        """Words that belong to the table row (stray words further right, e.g. a dimension label, are left out)."""
        xs = [x for x in (self.dest_x, self.pin_word.x0 if self.pin_word else None) if x is not None]
        limit = max(xs) + 1 if xs else self.anchor.x1
        return [w for w in (self.anchor, *self.cells) if w.x0 <= limit]

    def bbox(self) -> tuple[float, float, float, float]:
        ws = self.row_words()
        return (min(w.x0 for w in ws), min(w.y0 for w in ws), max(w.x1 for w in ws), max(w.y1 for w in ws))

    def loc(self) -> Location:
        return Location(page=self.page, x=round(self.anchor.x0, 1), y=round(self.anchor.cy, 1))


@dataclass
class Block:
    kind: str
    name: str
    part_number: str
    header: Word
    rows: list[Row] = field(default_factory=list)
    title: list[Word] = field(default_factory=list)

    @property
    def left(self) -> float:
        return min(r.anchor.x0 for r in self.rows)

    @property
    def right(self) -> float:
        return max(r.anchor.x1 for r in self.rows) + 120  # dest/pin cells sit right of the anchor


@dataclass
class SchematicResult:
    blocks: list[Block]
    wire_type: str | None
    issues: list[Issue]


def _cluster(values: list[float], tol: float) -> list[float]:
    out: list[list[float]] = []
    for v in sorted(values):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [sum(c) / len(c) for c in out]


def _col_index(centres: list[float], x: float) -> int:
    return min(range(len(centres)), key=lambda i: abs(centres[i] - x))


def parse_schematic(page: PageData) -> SchematicResult:
    issues: list[Issue] = []
    words = page.words
    pno = page.index

    anchors = [w for w in words if CONNECTOR_PN.match(w.t)]
    src = [Row("src", w, pno) for w in words if SRC_ANCHOR.match(w.t)]
    dst: list[Row] = []
    for w in words:
        if "SC_I_#" in w.t:
            pieces = [p for p in ORIGIN_SPLIT.split(w.t) if p]
            if len(pieces) > 1:
                issues.append(Issue(severity="warning", code="merged-token",
                                    message=f"Merged words {w.t!r} split into {pieces}",
                                    where=[Location(page=pno, x=round(w.x0, 1), y=round(w.cy, 1))]))
            for p in pieces:
                dst.append(Row("dst", Word(p, w.x0, w.y0, w.x1, w.y1, w.page), pno))
    rows = src + dst
    if not anchors or not rows:
        issues.append(Issue(severity="error", code="no-blocks",
                            message="No connector headers or no wiring rows found on the schematic page"))
        return SchematicResult([], None, issues)

    # Pair block columns (header x) with row columns left-to-right.
    head_cols = _cluster([a.x0 for a in anchors], 40)
    row_cols = _cluster([r.anchor.x0 for r in rows], COL_TOL)
    if len(head_cols) != len(row_cols):
        issues.append(Issue(severity="error", code="column-mismatch",
                            message=f"{len(head_cols)} header columns vs {len(row_cols)} row columns; cannot pair blocks"))
        return SchematicResult([], None, issues)

    blocks_by_col: list[list[Block]] = [[] for _ in head_cols]
    for a in sorted(anchors, key=lambda w: w.y0):
        ci = _col_index(head_cols, a.x0)
        hdr = [w for w in words if a.y0 - 48 <= w.y0 < a.y0 - 2 and a.x0 - 40 <= w.x0 <= a.x0 + 160]
        hdr.sort(key=lambda w: (round(w.y0 / 4), w.x0))
        name = " ".join(w.t for w in hdr)
        blocks_by_col[ci].append(Block("?", name, a.t, a, title=[*hdr, a]))

    for r in rows:
        ci = _col_index(row_cols, r.anchor.x0)
        cand = [b for b in blocks_by_col[ci] if b.header.y0 <= r.y]
        if not cand:
            issues.append(Issue(severity="error", code="row-outside-block",
                                message=f"Row {r.anchor.t!r} has no block header above it", where=[r.loc()]))
            continue
        b = max(cand, key=lambda b: b.header.y0)
        b.kind = r.kind
        r.block = b
        b.rows.append(r)

    # Cells: assign every remaining word to the nearest row of its column band.
    bounds = [(row_cols[i] - COL_TOL, row_cols[i + 1] - COL_TOL if i + 1 < len(row_cols) else 1e9)
              for i in range(len(row_cols))]
    anchor_words = {id(r.anchor) for r in rows}
    for w in words:
        if id(w) in anchor_words or w.t == "" or WIRE_NO.match(w.t):
            continue
        for ci, (lo, hi) in enumerate(bounds):
            if not lo <= w.x0 < hi:
                continue
            cands = [r for b in blocks_by_col[ci] for r in b.rows if abs(r.y - w.cy) <= ROW_TOL]
            if not cands:
                continue
            r = min(cands, key=lambda r: abs(r.y - w.cy))
            _fill(r, w, issues)

    _assign_wires(words, [b for col in blocks_by_col for b in col if b.rows], issues)

    for col in blocks_by_col:
        for b in col:
            b.rows.sort(key=lambda r: r.y)
            for r in b.rows:
                _check_row(r, issues)

    wire_type = None
    for i, w in enumerate(words):
        if w.t == "WIRES:":
            nxt = [x for x in words if x.t and WIRES_TYPE.match(x.t) and 0 <= x.cy - w.cy < 60 and x.x0 > w.x0 - 10 and x.x0 < w.x1 + 120]
            if nxt:
                wire_type = nxt[0].t
    return SchematicResult([b for col in blocks_by_col for b in col if b.rows], wire_type, issues)


def _fill(r: Row, w: Word, issues: list[Issue]) -> None:
    r.cells.append(w)
    loc = Location(page=w.page, x=round(w.x0, 1), y=round(w.cy, 1))

    def put(attr: str, value) -> None:
        old = getattr(r, attr)
        if old is not None and old != value:
            issues.append(Issue(severity="error", code="ambiguous-cell",
                                message=f"Row {r.anchor.t!r}: two values for {attr}: {old!r} / {value!r}",
                                where=[r.loc(), loc]))
        else:
            setattr(r, attr, value)

    t = w.t
    if r.kind == "src":
        if POLARITY.match(t):
            put("polarity", t)
        elif KIND.match(t):
            put("nom_red", t)
        elif SRC_ANCHOR.match(t):
            pass
        elif "_P" in t and ":" in t:
            pieces = DEST_SPLIT.findall(t) or [t]
            if len(pieces) > 1:
                issues.append(Issue(severity="warning", code="merged-token",
                                    message=f"Merged words {t!r} split into {pieces}", where=[loc]))
            for p in pieces:
                m = DEST.match(p)
                if m:
                    put("dest", (m.group(1), m.group(2)))
                    r.dest_x = w.x0
                else:
                    issues.append(Issue(severity="error", code="bad-dest", message=f"Unreadable destination {p!r}", where=[loc]))
        elif PIN.match(t):
            r.pin_cands.append(w)
    elif PIN.match(t):
        r.pin_cands.append(w)


def _assign_wires(words: list[Word], blocks: list[Block], issues: list[Issue]) -> None:
    for w in words:
        if not WIRE_NO.match(w.t):
            continue
        loc = Location(page=w.page, x=round(w.x0, 1), y=round(w.cy, 1))
        cands: list[tuple[float, Block]] = []
        for b in blocks:
            ys = [r.y for r in b.rows]
            if not min(ys) - 10 <= w.cy <= max(ys) + 10:
                continue
            # src blocks carry the number to the right of the cells, dst blocks to the left of the origin
            if b.kind == "src" and w.x0 >= b.right - 120:
                cands.append((w.x0 - b.right + 120, b))
            elif b.kind == "dst" and w.x1 <= b.left:
                cands.append((b.left - w.x1, b))
        if not cands:
            issues.append(Issue(severity="warning", code="wire-unassigned",
                                message=f"Wire number {w.t} not attached to any block", where=[loc]))
            continue
        b = min(cands, key=lambda c: c[0])[1]
        rows = sorted(b.rows, key=lambda r: r.y)
        pairs = [(rows[i], rows[i + 1]) for i in range(0, len(rows) - 1, 2)]
        if not pairs:
            continue
        a, c = min(pairs, key=lambda p: abs((p[0].y + p[1].y) / 2 - w.cy))
        for r in (a, c):
            if r.wire is not None and r.wire != w.t:
                issues.append(Issue(severity="error", code="wire-conflict",
                                    message=f"Row {r.anchor.t!r} gets two wire numbers {r.wire} / {w.t}",
                                    where=[r.loc(), loc]))
            else:
                r.wire = w.t
                r.wire_word = w


def _resolve_pin(r: Row, issues: list[Issue]) -> None:
    """The pin cell sits between the anchor and the destination; stray words further right are ignored."""
    cands = [w for w in r.pin_cands if w.x0 > r.anchor.x0 and (r.dest_x is None or w.x0 < r.dest_x)]
    if len(cands) > 1 and r.kind == "dst":
        cands = [min(cands, key=lambda w: w.x0)]
    if len(cands) > 1:
        issues.append(Issue(severity="error", code="ambiguous-cell",
                            message=f"Row {r.anchor.t!r}: several pin candidates {[w.t for w in cands]}", where=[r.loc()]))
    elif cands:
        r.pin = cands[0].t
        r.pin_word = cands[0]


def _check_row(r: Row, issues: list[Issue]) -> None:
    _resolve_pin(r, issues)
    if r.kind == "src":
        for attr in ("polarity", "nom_red", "pin", "dest", "wire"):
            if getattr(r, attr) is None:
                issues.append(Issue(severity="error", code="missing-cell",
                                    message=f"{r.block.name if r.block else '?'} row {r.anchor.t}: missing {attr}",
                                    where=[r.loc()]))
        r.signal = r.anchor.t
    else:
        m = ORIGIN.match(r.anchor.t)
        if m:
            r.origin = (m.group(1), m.group(2), m.group(3))
        else:
            issues.append(Issue(severity="error", code="bad-origin",
                                message=f"Unreadable origin {r.anchor.t!r}", where=[r.loc()]))
        for attr in ("pin", "wire"):
            if getattr(r, attr) is None:
                issues.append(Issue(severity="error", code="missing-cell",
                                    message=f"{r.block.name if r.block else '?'} row {r.anchor.t}: missing {attr}",
                                    where=[r.loc()]))
