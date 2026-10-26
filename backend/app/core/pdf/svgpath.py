"""Drawings -> compact SVG path data (for redrawing a sheet in a browser)."""
from __future__ import annotations

from app.core.pdf.extract import Drawing, PageData


def _hex(c: tuple[float, ...] | None) -> str | None:
    return None if c is None else "#" + "".join(f"{round(v * 255):02x}" for v in c[:3])


def drawing_path(d: Drawing) -> str:
    out: list[str] = []
    for it in d.items:
        k, pts = it[0], it[1:]
        if k == "l" and len(pts) == 2:
            out.append("M%.1f %.1fL%.1f %.1f" % (*pts[0], *pts[1]))
        elif k == "c" and len(pts) == 4:
            out.append("M%.1f %.1fC%.1f %.1f %.1f %.1f %.1f %.1f" % (*pts[0], *pts[1], *pts[2], *pts[3]))
        elif len(pts) >= 3:  # rectangle / quad corners
            out.append("M" + "L".join("%.1f %.1f" % tuple(p) for p in pts) + "Z")
    return "".join(out)


def page_paths(page: PageData, min_len: float = 0.3) -> list[dict]:
    """Visible paths of a page; the zero-length duplicates PDF generators leave behind are dropped."""
    res = []
    for d in page.drawings:
        pts = [p for it in d.items for p in it[1:]]
        if not pts:
            continue
        span = max(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
        if span < min_len and d.fill is None:
            continue
        path = drawing_path(d)
        if path:
            res.append({"d": path, "c": _hex(d.stroke), "w": round(d.width or 0.7, 2), "f": _hex(d.fill)})
    return res
