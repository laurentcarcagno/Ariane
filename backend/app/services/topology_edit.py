"""User corrections of what the topology sheets could not give (a missing diameter, a missing BOM item).

An edit never hides its origin: it is logged in `topology.edits`, the segment is reported as edited
(`topology-edited`, info) and the Excel export marks it "saisi". Only the fields below can be edited.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone

from pydantic import BaseModel, Field

DIAMETER_CODES = {"diameter-missing", "diameter-ambiguous", "diameter-conflict"}


class SegmentEdit(BaseModel):
    diameterMm: float | None = Field(default=None, gt=0, le=100)
    bomItems: list[str] | None = Field(default=None, max_length=10)

    def checked_items(self) -> list[str] | None:
        if self.bomItems is None:
            return None
        items = [i.strip() for i in self.bomItems]
        if any(not (len(i) == 2 and i.isdigit()) for i in items) or len(set(items)) != len(items):
            raise ValueError("BOM items are two-digit positions, each used once")
        return items


class UnknownSegment(KeyError):
    pass


def edit_segment(model: dict, segment_id: str, edit: SegmentEdit, username: str) -> dict:
    """Returns a new model with the edit applied; the input is left untouched."""
    out = copy.deepcopy(model)
    topo = out.get("topology") or {}
    seg = next((s for s in topo.get("segments", []) if s["id"] == segment_id), None)
    if seg is None:
        raise UnknownSegment(segment_id)
    items = edit.checked_items()
    changes: dict[str, tuple] = {}
    if edit.diameterMm is not None and edit.diameterMm != seg["diameterMm"]:
        changes["diameterMm"] = (seg["diameterMm"], edit.diameterMm)
        seg["diameterMm"] = edit.diameterMm
    if items is not None and items != seg["bomItems"]:
        changes["bomItems"] = (seg["bomItems"], items)
        seg["bomItems"] = items
    if not changes:
        return out
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    topo.setdefault("edits", []).extend(
        {"segment": segment_id, "field": f, "before": b, "after": a, "by": username, "at": now} for f, (b, a) in changes.items())

    def about_segment(i: dict) -> bool:
        return any(r.get("segment") == segment_id for r in i["refs"])

    issues = out["issues"]
    drop = {"topology-edited"}
    if "diameterMm" in changes:
        drop |= DIAMETER_CODES
    if seg["bomItems"]:
        drop.add("segment-no-bom")
    issues[:] = [i for i in issues if not (about_segment(i) and i["code"] in drop)]
    label = f"{seg['a']}-{seg['b']}"
    parts = []
    if "diameterMm" in changes:
        parts.append(f"diameter {changes['diameterMm'][1]:g} mm (plan: {changes['diameterMm'][0] if changes['diameterMm'][0] is not None else 'none'})")
    if "bomItems" in changes:
        parts.append(f"BOM items {', '.join(seg['bomItems']) or 'none'}")
    issues.append({"severity": "info", "code": "topology-edited", "where": [], "refs": [{"segment": segment_id}],
                   "message": f"Segment {label} edited by {username}: {'; '.join(parts)}"})
    return out
