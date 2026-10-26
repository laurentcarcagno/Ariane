"""Exploration: dump words (derotated, x/y) and vector drawings of a PDF to JSON.

Usage: python explore_pdf.py <pdf> <out.json>
Local only: no network access.
"""
import json
import sys

import fitz  # PyMuPDF


def extract(path: str) -> dict:
    doc = fitz.open(path)
    pages = []
    for page in doc:
        m = page.rotation_matrix  # unrotated space -> displayed space
        words = []
        for x0, y0, x1, y1, text, block, line, _w in page.get_text("words"):
            r = fitz.Rect(x0, y0, x1, y1) * m
            r.normalize()
            words.append({"t": text, "x0": round(r.x0, 2), "y0": round(r.y0, 2),
                          "x1": round(r.x1, 2), "y1": round(r.y1, 2)})
        draws = []
        for d in page.get_drawings():
            items = []
            for it in d["items"]:
                kind = it[0]
                pts = [fitz.Point(p) * m for p in it[1:] if isinstance(p, fitz.Point)]
                items.append([kind] + [[round(p.x, 2), round(p.y, 2)] for p in pts])
            draws.append({"stroke": d.get("color"), "fill": d.get("fill"),
                          "w": d.get("width"), "items": items})
        pages.append({"rotation": page.rotation, "width": page.rect.width,
                      "height": page.rect.height, "words": words, "drawings": draws})
    return {"file": path, "pages": pages}


if __name__ == "__main__":
    data = extract(sys.argv[1])
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(data, f)
    for i, p in enumerate(data["pages"], 1):
        print(i, p["rotation"], p["width"], p["height"], len(p["words"]), len(p["drawings"]))
