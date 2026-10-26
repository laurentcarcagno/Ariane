from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def test_should_list_beyond_gravity_plugin():
    r = client.get("/api/v1/plugins")
    assert r.status_code == 200 and r.json()[0]["id"] == "beyond_gravity"


def test_should_reject_non_pdf_upload():
    r = client.post("/api/v1/imports", data={"plugin": "beyond_gravity"},
                    files={"drawing": ("a.pdf", b"nope"), "bom": ("b.pdf", b"nope")})
    assert r.status_code == 422


@pytest.mark.skipif(not (ROOT / "DRW3500402-907_Init_Lower_1-6.pdf").exists(), reason="sample PDFs missing")
def test_should_import_example_harness():
    with open(ROOT / "DRW3500402-907_Init_Lower_1-6.pdf", "rb") as d, open(ROOT / "PL_3500402-907_A.1.pdf", "rb") as b:
        r = client.post("/api/v1/imports", data={"plugin": "beyond_gravity"}, files={"drawing": d, "bom": b})
    body = r.json()
    assert r.status_code == 200 and len(body["wires"]) == 96 and len(body["routes"]) == 48
    assert body["wires"][0]["from"]["conn"]
