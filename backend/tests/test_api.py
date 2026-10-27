from pathlib import Path

import pytest

from tests.conftest import make_client

ROOT = Path(__file__).resolve().parents[2]
DRW, PL = ROOT / "DRW3500402-907_Init_Lower_1-6.pdf", ROOT / "PL_3500402-907_A.1.pdf"
have_samples = pytest.mark.skipif(not (DRW.exists() and PL.exists()), reason="sample PDFs missing")


def bearer(keys, **kw):
    return {"Authorization": f"Bearer {keys.token(**kw)}"}


def upload(client, headers=None):
    with open(DRW, "rb") as d, open(PL, "rb") as b:
        return client.post("/api/v1/imports", data={"plugin": "beyond_gravity"}, files={"drawing": d, "bom": b}, headers=headers or {})


def test_should_expose_public_config_without_secret(client):
    r = client.get("/api/v1/config")
    assert r.status_code == 200 and set(r.json()) == {"authDisabled", "authority", "clientId"}


def test_should_require_a_token(client):
    assert client.get("/api/v1/plugins").status_code == 401
    assert client.get("/api/v1/plugins", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_should_reject_expired_wrong_audience_and_missing_customer(client, keys):
    for kw in ({"exp": 1}, {"aud": "other"}, {"iss": "https://evil/realms/x"}):
        assert client.get("/api/v1/me", headers=bearer(keys, **kw)).status_code == 401
    assert client.get("/api/v1/me", headers=bearer(keys, customer=None)).status_code == 403


def test_should_list_only_plugins_enabled_for_the_customer(client, keys):
    r = client.get("/api/v1/plugins", headers=bearer(keys))
    assert [p["id"] for p in r.json()] == ["beyond_gravity"]
    assert client.get("/api/v1/plugins", headers=bearer(keys, customer="unknown-corp")).status_code == 403


def test_should_reject_non_pdf_upload(dev_client):
    r = dev_client.post("/api/v1/imports", data={"plugin": "beyond_gravity"}, files={"drawing": ("a.pdf", b"nope"), "bom": ("b.pdf", b"nope")})
    assert r.status_code == 422


@have_samples
def test_should_import_store_and_reopen(client, keys):
    h = bearer(keys)
    r = upload(client, h)
    assert r.status_code == 200
    body = r.json()
    assert len(body["model"]["wires"]) == 96 and len(body["model"]["routes"]) == 48
    listing = client.get("/api/v1/imports", headers=h).json()
    assert [i["id"] for i in listing] == [body["id"]] and listing[0]["errors"] == 4
    assert client.get(f"/api/v1/imports/{body['id']}", headers=h).json()["model"]["partNumber"] == "3500402-907"


@have_samples
def test_should_not_show_another_customers_import(tmp_path, keys):
    """Isolation: a second configured customer sees nothing of the first, and gets 404 (not 403) by id."""
    import json
    cfg = tmp_path / "customers.json"
    cfg.write_text(json.dumps({"customers": {"beyond-gravity": {"label": "BG", "plugins": ["beyond_gravity"]},
                                              "other": {"label": "Other", "plugins": ["beyond_gravity"]}}}))
    with make_client(tmp_path, keys, customers_config_path=cfg) as c:
        mine = upload(c, bearer(keys, customer="beyond-gravity")).json()["id"]
        theirs = bearer(keys, customer="other")
        assert c.get("/api/v1/imports", headers=theirs).json() == []
        assert c.get(f"/api/v1/imports/{mine}", headers=theirs).status_code == 404
        assert c.delete(f"/api/v1/imports/{mine}", headers=theirs).status_code == 404
        assert c.get(f"/api/v1/imports/{mine}", headers=bearer(keys, customer="beyond-gravity")).status_code == 200
        assert c.delete(f"/api/v1/imports/{mine}", headers=bearer(keys, customer="beyond-gravity")).status_code == 204


def test_should_refuse_plugin_not_enabled_for_customer(tmp_path, keys):
    import json
    cfg = tmp_path / "customers.json"
    cfg.write_text(json.dumps({"customers": {"acme": {"label": "Acme", "plugins": []}}}))
    with make_client(tmp_path, keys, customers_config_path=cfg) as c:
        r = c.post("/api/v1/imports", data={"plugin": "beyond_gravity"}, files={"drawing": ("a.pdf", b"%PDF"), "bom": ("b.pdf", b"%PDF")},
                   headers=bearer(keys, customer="acme"))
        assert r.status_code == 403


@have_samples
def test_should_export_xlsx_for_the_owner_only(tmp_path, keys):
    import io
    import json

    from openpyxl import load_workbook
    cfg = tmp_path / "customers.json"
    cfg.write_text(json.dumps({"customers": {"beyond-gravity": {"label": "BG", "plugins": ["beyond_gravity"]},
                                              "other": {"label": "O", "plugins": ["beyond_gravity"]}}}))
    with make_client(tmp_path, keys, customers_config_path=cfg) as c:
        mine = bearer(keys, customer="beyond-gravity")
        imp = upload(c, mine).json()["id"]
        r = c.get(f"/api/v1/imports/{imp}/export.xlsx", headers=mine)
        assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
        wb = load_workbook(io.BytesIO(r.content))
        assert wb.sheetnames == ["Page de garde", "From-To", "Connecteurs", "Segments", "Nomenclature", "Rapport"]
        assert wb["Page de garde"]["H2"].value == "BG" and wb["Page de garde"]["H9"].value == "3500402-907"
        ft = wb["From-To"]
        assert ft.max_row == 102 and ft["C7"].value == "907-01+" and ft["C6"].value == "Fil" and ft["A5"].value is None
        banner = [c.value for r in ft.iter_rows(min_row=1, max_row=4) for c in r if c.value]
        assert banner[1:] == ["Réf : 3500402-907", f"Date : {__import__('datetime').date.today():%d/%m/%Y}", "Édition : 00"] and len(ft._images) == 1
        assert all(len(wb[n]._images) == 1 for n in wb.sheetnames[1:])
        assert {wb[n]["C2"].value for n in wb.sheetnames[1:]} == {"Réf : 3500402-907"}  # same banner position on every sheet
        assert c.get(f"/api/v1/imports/{imp}/export.xlsx", headers=bearer(keys, customer="other")).status_code == 404
        r = c.post(f"/api/v1/imports/{imp}/export.xlsx", headers=mine,
                   json={"edition": "02", "classification": "internal", "quality_manager": "=1+1", "export_control": "Listed/Controlled"})
        head = load_workbook(io.BytesIO(r.content))["Page de garde"]
        assert head["H11"].value == "02" and head["D10"].value.startswith("☒") and head["C10"].value.startswith("☐")
        assert head["D37"].value.startswith("=1+1") and head["D37"].data_type == "s" and "Listed/Controlled" in head["B53"].value
        assert head.sheet_view.view == "normal"
        assert len(head.conditional_formatting) == 0  # no rule left that paints the placeholders yellow
        assert head["H9"].fill.fill_type is None and head["B53"].fill.fill_type is None  # no yellow placeholder left
        assert load_workbook(io.BytesIO(c.get(f"/api/v1/imports/{imp}/export.xlsx", headers=mine).content))["Page de garde"]["B53"].value is None
        cx = load_workbook(io.BytesIO(r.content))["Connecteurs"]
        empties = [row for row in cx.iter_rows(min_row=7, min_col=3, values_only=True) if row[4] == "place vide"]
        assert sorted(row[2] for row in empties if row[0] == "S/C I #x-1 J01") == ["C", "F", "M"] and len(empties) == 18
        assert c.post(f"/api/v1/imports/{imp}/export.xlsx", headers=mine, json={"classification": "x"}).status_code == 422
        assert c.post(f"/api/v1/imports/{imp}/export.xlsx", headers=bearer(keys, customer="other"), json={}).status_code == 404


def test_should_serve_requests_without_any_oidc_setting_when_auth_is_disabled(tmp_path, keys):
    """Regression: the dev setup (no issuer, no JWKS URL) must not try to build a JWKS client."""
    s = make_client(tmp_path, keys, auth_disabled=True, oidc_issuer="")
    s.app.state.key_resolver = None
    with s as c:
        assert c.get("/api/v1/me").json()["customer"] == "beyond-gravity"
        assert c.get("/api/v1/plugins").status_code == 200


@have_samples
def test_should_name_the_empty_places_of_a_known_insert(dev_client):
    model = upload(dev_client).json()["model"]
    by_id = {c["id"]: c for c in model["connectors"]}
    assert by_id["SC1"]["emptyPins"] == ["C", "F", "M"] and by_id["SC6"]["emptyPins"] == ["C", "F", "M"]
    assert by_id["INIT_A_P1"]["emptyPins"] is None  # layout of the 61-contact insert is not known: count only


@have_samples
def test_should_edit_a_segment_and_keep_a_trace(tmp_path, keys):
    import io

    from openpyxl import load_workbook

    with make_client(tmp_path, keys) as c:
        mine = bearer(keys)
        imp = upload(c, mine).json()
        topo = imp["model"]["topology"]
        seg = next(s for s in topo["segments"] if s["diameterMm"] is None)
        before = {i["code"] for i in imp["model"]["issues"] if {"segment": seg["id"]} in [{k: v for k, v in r.items() if v} for r in i["refs"]]}
        assert "diameter-missing" in before
        url = f"/api/v1/imports/{imp['id']}/segments/{seg['id']}"
        r = c.patch(url, headers=mine, json={"diameterMm": 2.5})
        assert r.status_code == 200
        model = r.json()["model"]
        edited = next(s for s in model["topology"]["segments"] if s["id"] == seg["id"])
        assert edited["diameterMm"] == 2.5
        assert model["topology"]["edits"][0] | {"at": None} == {"segment": seg["id"], "field": "diameterMm", "before": None, "after": 2.5,
                                                                 "by": "alice", "at": None}
        codes = [i["code"] for i in model["issues"] if any(x.get("segment") == seg["id"] for x in i["refs"])]
        assert "diameter-missing" not in codes and codes.count("topology-edited") == 1
        assert c.get(f"/api/v1/imports/{imp['id']}", headers=mine).json()["model"]["topology"]["edits"]  # persisted
        counts = c.get("/api/v1/imports", headers=mine).json()[0]  # the counters follow the edited model
        assert counts["warnings"] == [i["severity"] for i in model["issues"]].count("warning")
        x = load_workbook(io.BytesIO(c.get(f"/api/v1/imports/{imp['id']}/export.xlsx", headers=mine).content))["Segments"]
        sources = {r[2]: r[8] for r in x.iter_rows(min_row=7, values_only=True)}
        assert sources[seg["id"]] == "saisi" and list(sources.values()).count("plan") == len(sources) - 1
        # refused: unknown segment, bad values, another customer
        assert c.patch(f"/api/v1/imports/{imp['id']}/segments/S99", headers=mine, json={"diameterMm": 2}).status_code == 404
        assert c.patch(url, headers=mine, json={"diameterMm": -1}).status_code == 422
        assert c.patch(url, headers=mine, json={"bomItems": ["7"]}).status_code == 422
        assert c.patch(url, headers=bearer(keys, customer="unknown-corp"), json={"diameterMm": 2}).status_code in (403, 404)


def test_should_migrate_a_prototype_database_and_a_new_one(tmp_path):
    import sqlite3
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    def upgrade(db):
        cfg = Config(str(ROOT / "backend" / "alembic.ini"))
        cfg.set_main_option("script_location", str(ROOT / "backend" / "migrations"))
        cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db}")
        command.upgrade(cfg, "head")
        return {c["name"] for c in inspect(create_engine(f"sqlite:///{db}")).get_columns("imports")}

    fresh = tmp_path / "fresh.db"
    assert "updated_at" in upgrade(fresh)
    old = tmp_path / "old.db"  # what create_all produced before Alembic
    con = sqlite3.connect(old)
    con.execute("create table imports (id varchar(36) primary key, customer_id varchar(64), plugin varchar(64), created_by varchar(128),"
                " created_at datetime, drawing_name varchar(255), bom_name varchar(255), part_number varchar(64), errors int,"
                " warnings int, model json)")
    con.execute("insert into imports values ('a','bg','p','u','2026-01-01','d','b','pn',0,0,'{}')")
    con.commit(); con.close()
    assert "updated_at" in upgrade(old)
    assert sqlite3.connect(old).execute("select id from imports").fetchall() == [("a",)]
