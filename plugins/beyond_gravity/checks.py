"""Cross-checks: S/C table <-> INIT table, and counts against the parts list."""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from app.plugins.model import BomItem, Issue, Location, Ref

from .netlist import Block, Row

CAPACITY = re.compile(r"\d{2}[A-Z]{2}(\d{2,3})[A-Z]{2}$")
BLOCK_NO = re.compile(r"#x-(\d+)")


def conn_id(b: Block) -> str:
    if b.kind == "src":
        m = BLOCK_NO.search(b.name)
        return f"SC{m.group(1)}" if m else re.sub(r"\W+", "_", b.name)
    return re.sub(r"\s+", "_", b.name.strip())


def rref(r: Row) -> Ref:
    return Ref(conn=conn_id(r.block), pin=r.pin)


def capacity(pn: str) -> int | None:
    m = CAPACITY.search(pn)
    return int(m.group(1)) if m else None


def crosscheck(blocks: list[Block]) -> list[Issue]:
    issues: list[Issue] = []
    src_blocks = [b for b in blocks if b.kind == "src"]
    dst_blocks = {conn_id(b): b for b in blocks if b.kind == "dst"}
    src_by_no = {conn_id(b)[2:]: b for b in src_blocks}

    # duplicate pins inside one connector
    for b in blocks:
        seen: dict[str, Row] = {}
        for r in b.rows:
            if r.pin is None:
                continue
            if r.pin in seen:
                issues.append(Issue(severity="error", code="duplicate-pin",
                                    message=f"{b.name}: pin {r.pin!r} used twice ({seen[r.pin].anchor.t} and {r.anchor.t})",
                                    where=[seen[r.pin].loc(), r.loc()], refs=[rref(r)]))
            seen.setdefault(r.pin, r)

    # destination used twice from the S/C side
    dest_use: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for b in src_blocks:
        for r in b.rows:
            if r.dest:
                dest_use[r.dest].append(r)
    for (cn, pin), rs in dest_use.items():
        if len(rs) > 1:
            issues.append(Issue(severity="error", code="duplicate-destination",
                                message=f"{cn}:{pin} is the destination of {len(rs)} S/C rows: "
                                        + ", ".join(f"{r.block.name} {r.polarity} {r.anchor.t} {r.nom_red}" for r in rs),
                                where=[r.loc() for r in rs],
                                refs=[Ref(conn=cn, pin=pin)] + [rref(r) for r in rs]))

    # S/C -> INIT
    matched: set[int] = set()
    for b in src_blocks:
        for r in b.rows:
            if not r.dest:
                continue
            cn, ipin = r.dest
            blk = dst_blocks.get(cn)
            if blk is None:
                issues.append(Issue(severity="error", code="unknown-connector",
                                    message=f"{b.name} {r.anchor.t}: destination connector {cn} has no block", where=[r.loc()],
                                    refs=[rref(r)]))
                continue
            hits = [d for d in blk.rows if d.pin == ipin]
            if not hits:
                issues.append(Issue(severity="error", code="orphan-src",
                                    message=f"{b.name} pin {r.pin!r} -> {cn}:{ipin} has no matching row on {blk.name}",
                                    where=[r.loc()], refs=[rref(r), Ref(conn=cn, pin=ipin)]))
                continue
            if len(hits) > 1:
                issues.append(Issue(severity="error", code="duplicate-pin",
                                    message=f"{blk.name}: pin {ipin!r} listed {len(hits)} times", where=[h.loc() for h in hits], refs=[Ref(conn=cn, pin=ipin)]))
            d = hits[0]
            matched.add(id(d))
            if d.origin:
                no, j, opin = d.origin
                own_no = conn_id(b)[2:]
                if no != own_no or opin != r.pin:
                    issues.append(Issue(severity="error", code="origin-mismatch",
                                        message=f"{b.name} pin {r.pin!r} -> {cn}:{ipin}, but {blk.name} pin {ipin!r} says origin "
                                                f"SC_I_#x-{no}_J{j}:{opin}", where=[r.loc(), d.loc()],
                                        refs=[rref(r), rref(d)]))
            if d.wire and r.wire and d.wire != r.wire:
                issues.append(Issue(severity="error", code="wire-number-mismatch",
                                    message=f"{b.name} pin {r.pin!r} wire {r.wire} vs {blk.name} pin {ipin!r} wire {d.wire}",
                                    where=[r.loc(), d.loc()], refs=[rref(r), rref(d)]))
    # J suffix coherence (reported once per distinct pair, never corrected)
    j_of_src = {conn_id(b)[2:]: re.search(r"J(\d+)", b.name) for b in src_blocks}
    seen_j: Counter = Counter()
    for blk in dst_blocks.values():
        for d in blk.rows:
            if d.origin:
                no, j, _ = d.origin
                m = j_of_src.get(no)
                if m and m.group(1) != j:
                    seen_j[(blk.name, no, j, m.group(1))] += 1
    for (bn, no, j, expected), n in seen_j.items():
        bn_id = re.sub(r"\s+", "_", bn.strip())
        issues.append(Issue(severity="warning", code="connector-suffix",
                            message=f"{bn}: {n} origins read 'SC_I_#x-{no}_J{j}' while the S/C block is named J{expected}",
                            refs=[Ref(conn=bn_id)]))

    # INIT -> S/C: orphans
    for blk in dst_blocks.values():
        for d in blk.rows:
            if id(d) not in matched:
                issues.append(Issue(severity="error", code="orphan-dst",
                                    message=f"{blk.name} pin {d.pin!r} (origin {d.anchor.t}) is not referenced by any S/C row",
                                    where=[d.loc()], refs=[rref(d)]))
    return issues


def label_checks(blocks: list[Block], bom: list[BomItem]) -> list[Issue]:
    """Block headers must match the harness labels (BOM 'Marking: ...'), compared as written."""
    labels = {re.sub(r"\s+", " ", m.group(1)).strip()
              for i in bom if (m := re.search(r"Marking:\s*(.*?)(?:\s+\"\w+\")?$", i.notes))}
    out = []
    for b in blocks:
        name = re.sub(r"\s+", " ", b.name).strip()
        if labels and name not in labels:
            near = sorted(l for l in labels if BLOCK_NO.search(l) and BLOCK_NO.search(name)
                          and BLOCK_NO.search(l).group(0) == BLOCK_NO.search(name).group(0))
            out.append(Issue(severity="warning", code="label-mismatch",
                             message=f"Block header {name!r} does not match any BOM label" + (f" (BOM: {near[0]!r})" if near else ""),
                             where=[Location(page=b.header.page, x=round(b.header.x0, 1), y=round(b.header.cy, 1))],
                             refs=[Ref(conn=conn_id(b))]))
    return out


def count_checks(blocks: list[Block], wires_total: int, pairs: int, bom: list[BomItem]) -> tuple[list[Issue], dict]:
    issues: list[Issue] = []
    stats: dict = {"pairs": pairs, "conductors": wires_total}
    by_pos = {i.position: i for i in bom}
    pn_count = Counter(b.part_number for b in blocks)
    cap_by_type: dict[str, int] = {}
    for pn, n in pn_count.items():
        for item in bom:
            if item.description.startswith(pn):
                exp = int(item.amount) if item.amount.isdigit() else None
                if exp != n:
                    issues.append(Issue(severity="error", code="connector-count",
                                        message=f"{pn}: {n} blocks on the drawing vs {item.amount} in BOM pos {item.position}"))
                break
        else:
            issues.append(Issue(severity="warning", code="bom-missing", message=f"{pn} not found in the parts list"))
        c = capacity(pn)
        if c:
            cap_by_type[pn] = c
    # contacts: pin/socket from the PN suffix (…PN = pin contacts, …SN = socket contacts)
    for pn, n in pn_count.items():
        c = cap_by_type.get(pn)
        gender = "Pin" if pn.endswith("PN") else "Socket" if pn.endswith("SN") else None
        if not c or not gender:
            continue
        total = c * n
        stats[f"contacts_{gender.lower()}"] = total
        item = next((i for i in bom if f"Contact {gender}" in i.description), None)
        if item and item.amount.isdigit() and int(item.amount) != total:
            issues.append(Issue(severity="error", code="contact-count",
                                message=f"{n} x {c} = {total} {gender.lower()} contacts expected from the drawing, BOM pos {item.position} says {item.amount}"))
    twisted = next((i for i in bom if "TSP" in i.description and "2x" in i.description), None)
    stats["tsp_item"] = twisted.position if twisted else None
    for i in bom:
        if i.tbd:
            issues.append(Issue(severity="info", code="bom-tbd", message=f"BOM pos {i.position} ({i.description}): {i.amount} {i.unit} — TBD"))
    return issues, stats
