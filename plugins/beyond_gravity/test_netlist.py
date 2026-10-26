"""Netlist of the example harness 3500402-907 (needs the two sample PDFs at the repo root)."""
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


def codes(model):
    return [i.code for i in model.issues]


def test_should_find_48_pairs_and_96_conductors(model):
    assert len({w.pairId for w in model.wires}) == 48
    assert len(model.wires) == 96
    assert {w.id for w in model.wires} == {f"907-{n:02d}" for n in range(1, 49)}
    assert all(w.type == "TSP-20" for w in model.wires)


def test_should_find_8_connectors_with_expected_capacity(model):
    caps = sorted(c.capacity for c in model.connectors)
    assert caps == [19] * 6 + [61] * 2


def test_should_map_first_pair_like_the_acceptance_criteria(model):
    w = {w.conductorId: w for w in model.wires}
    assert (w["907-01+"].from_.conn, w["907-01+"].from_.pin) == ("SC1", "N")
    assert (w["907-01+"].to.conn, w["907-01+"].to.pin) == ("INIT_A_P1", "c")
    assert (w["907-01-"].from_.pin, w["907-01-"].to.pin) == ("A", "B")


def test_should_keep_pin_case_sensitive(model):
    init_a = next(c for c in model.connectors if c.id == "INIT_A_P1")
    pins = {c.pin for c in init_a.contacts}
    assert {"c", "C", "B"} <= pins and any(len(p) == 2 for p in pins)


def test_should_cross_check_both_tables_without_orphans_except_known_anomaly(model):
    errs = [i for i in model.issues if i.severity == "error"]
    assert {i.code for i in errs} <= {"duplicate-destination", "origin-mismatch",
                                      "wire-number-mismatch", "orphan-dst"}
    assert any("INIT_B_P1:w" in i.message for i in errs if i.code == "duplicate-destination")


def test_should_flag_j02_vs_j01_without_correcting(model):
    assert codes(model).count("connector-suffix") == 6


def test_should_flag_missing_i_in_headers_3_and_6(model):
    msgs = [i.message for i in model.issues if i.code == "label-mismatch"]
    assert len(msgs) == 2 and all("#x-3" in m or "#x-6" in m for m in msgs)


def test_should_match_bom_counts(model):
    assert "contact-count" not in codes(model) and "connector-count" not in codes(model)
    assert model.topology["stats"]["contacts_pin"] == 122
    assert model.topology["stats"]["contacts_socket"] == 114
    assert any(i.code == "bom-tbd" for i in model.issues)
