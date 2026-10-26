"""Parts-list (nomenclature) parser: columns are located from the header words."""
from __future__ import annotations

import re

from app.core.pdf.extract import PageData, Word
from app.plugins.model import BomItem

HEADERS = ["Position", "Part", "Revision", "Description", "Amount", "Unit", "Notes", "CRI"]
POS = re.compile(r"^\d{2}$")


def parse_bom(pages: list[PageData]) -> tuple[list[BomItem], str | None]:
    pos = [w for w in pages[0].words if w.t == "Position"]
    if not pos:
        raise ValueError("Parts list header row not found")
    head = {w.t: w for w in pages[0].words if w.t in HEADERS and abs(w.cy - pos[0].cy) < 4}
    if len(head) < len(HEADERS):
        raise ValueError("Parts list header row not found")
    xs = [head[h].x0 for h in HEADERS]
    top = min((w for w in pages[0].words if w.t == "Part"), key=lambda w: w.y0)
    nxt = sorted((x for x in pages[0].words if abs(x.cy - top.cy) < 4 and x.x0 > 200), key=lambda x: x.x0)
    part_no = nxt[0].t if nxt else None

    def col(w: Word) -> int:
        return max(i for i, x in enumerate(xs) if w.x0 >= x - 8)

    items: list[dict] = []
    for p in pages:
        lines: dict[int, list[Word]] = {}
        for w in p.words:
            if w.y0 <= head["Position"].y1 + 2 and p.index == 0:
                continue
            lines.setdefault(round(w.cy / 4), []).append(w)
        for key in sorted(lines):
            ws = sorted(lines[key], key=lambda w: w.x0)
            first = ws[0]
            cells = {i: [] for i in range(len(HEADERS))}
            for w in ws:
                cells[col(w)].append(w.t)
            if POS.match(first.t) and col(first) == 0 and len(ws) > 2:
                items.append({i: " ".join(v) for i, v in cells.items()})
            elif items:  # continuation line of the previous row
                for i, v in cells.items():
                    if v:
                        items[-1][i] = (items[-1][i] + " " + " ".join(v)).strip()
    out = []
    for r in items:
        text = r[6] + " " + r[4] + " " + r[5]
        out.append(BomItem(position=r[0], partNumber=r[1], description=r[3], amount=r[4],
                           unit=r[5], notes=r[6], tbd="TBD" in text))
    return out, part_no
