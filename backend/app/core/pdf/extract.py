"""Generic PDF extraction: words and vector drawings in the *displayed* frame.

Pages with /Rotate are mapped through ``page.rotation_matrix`` so that x/y match
what the user sees. Text is never normalised (pin letters are case-sensitive).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


@dataclass(frozen=True, slots=True)
class Word:
    t: str
    x0: float
    y0: float
    x1: float
    y1: float
    page: int = 0
    color: int = 0  # sRGB int of the text span (0 = black, 0xff0000 = red)

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass(slots=True)
class Drawing:
    stroke: tuple[float, ...] | None
    fill: tuple[float, ...] | None
    width: float | None
    items: list[list]  # ["l", [x,y], [x,y]] | ["c", p0..p3] | ["re", ...]


@dataclass(slots=True)
class PageData:
    index: int
    rotation: int
    width: float
    height: float
    words: list[Word] = field(default_factory=list)
    drawings: list[Drawing] = field(default_factory=list)


def _points(args, m) -> list[fitz.Point]:
    """Points of a drawing item in displayed space; rectangles and quads become their corners."""
    out: list[fitz.Point] = []
    for a in args:
        if isinstance(a, fitz.Point):
            out.append(a * m)
        elif isinstance(a, fitz.Rect):
            out += [fitz.Point(a.x0, a.y0) * m, fitz.Point(a.x1, a.y0) * m, fitz.Point(a.x1, a.y1) * m, fitz.Point(a.x0, a.y1) * m]
        elif isinstance(a, fitz.Quad):
            out += [fitz.Point(q) * m for q in (a.ul, a.ur, a.lr, a.ll)]
    return out


def extract_pdf(path: str | Path, *, drawings: bool = True) -> list[PageData]:
    pages: list[PageData] = []
    with fitz.open(str(path)) as doc:
        for page in doc:
            m = page.rotation_matrix
            pd = PageData(page.number, page.rotation, page.rect.width, page.rect.height)
            colored = [(fitz.Rect(sp["bbox"]), sp["color"])
                       for b in page.get_text("dict")["blocks"] for ln in b.get("lines", [])
                       for sp in ln["spans"] if sp["color"] != 0]
            for x0, y0, x1, y1, text, *_ in page.get_text("words"):
                src = fitz.Rect(x0, y0, x1, y1)
                col = next((c for rc, c in colored if rc.contains(fitz.Point((x0 + x1) / 2, (y0 + y1) / 2))), 0)
                r = src * m
                r.normalize()
                pd.words.append(Word(text, r.x0, r.y0, r.x1, r.y1, page.number, col))
            if drawings:
                for d in page.get_drawings():
                    items = []
                    for it in d["items"]:
                        pts = _points(it[1:], m)
                        items.append([it[0]] + [[p.x, p.y] for p in pts])
                    pd.drawings.append(Drawing(d.get("color"), d.get("fill"), d.get("width"), items))
            pages.append(pd)
    return pages
