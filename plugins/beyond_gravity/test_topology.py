"""Topology of the example harness: graph from the blue strokes, node numbers, diameters, routes."""
from pathlib import Path

import pytest

from plugins.beyond_gravity.plugin import parse

ROOT = Path(__file__).resolve().parents[2]
DRW = ROOT / "DRW3500402-907_Init_Lower_1-6.pdf"
PL = ROOT / "PL_3500402-907_A.1.pdf"
pytestmark = pytest.mark.skipif(not (DRW.exists() and PL.exists()), reason="sample PDFs missing")


@pytest.fixture(scope="module")
def model():
    return parse(DRW, PL)


def seg(model, a, b):
    return next(s for s in model.topology["segments"]
                if {s["a"], s["b"]} == {a, b})


def test_should_extract_graph_with_numbered_nodes(model):
    t = model.topology
    assert t["status"] == "ok" and len(t["segments"]) == 28
    ids = {n["id"] for n in t["nodes"]}
    assert {"N1A", "N1B", "N12", "N7", "INIT_A", "INIT_B", "SC1", "SC6"} <= ids
    assert {f"N{i}{s}" for i in range(1, 6) for s in "AB"} <= ids  # 1..5 on both trees, 7..12 shared
    assert not [i for i in model.issues if i.code.startswith(("node-id", "node-label", "connector-"))
                and i.code != "connector-suffix"]


def test_should_attach_diameters_and_bom_items(model):
    assert seg(model, "N1A", "INIT_A")["diameterMm"] == 22
    assert seg(model, "N1A", "INIT_A")["bomItems"] == ["07", "10"]
    assert seg(model, "N12", "SC1")["diameterMm"] == 12.5
    assert seg(model, "N2A", "N11")["diameterMm"] == 9
    assert seg(model, "N3B", "N2B")["diameterMm"] == 17.5


def test_should_flag_missing_diameter_instead_of_guessing(model):
    assert seg(model, "N3A", "N1A")["diameterMm"] is None
    assert any(i.code == "diameter-missing" and "N3A-N1A" in i.message for i in model.issues)


def test_should_route_all_48_pairs(model):
    assert len(model.routes) == 48 and not any(i.code in ("unrouted", "route-disconnected") for i in model.issues)
    s = {x["id"]: x for x in model.topology["segments"]}
    first = [(s[i]["a"], s[i]["b"]) for i in model.routes["907-01"]]
    assert first[0] == ("N12", "SC1") or first[0] == ("SC1", "N12") or "SC1" in first[0]
    assert "INIT_A" in first[-1]
    assert "INIT_B" in [e for i in model.routes["907-25"] for e in (s[i]["a"], s[i]["b"])]
