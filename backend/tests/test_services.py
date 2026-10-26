import json

import httpx
import pytest

from app.config import Settings
from app.services.customers import load_customers
from app.services.secrets import fetch_secrets, resolve_database_url


def test_should_load_shipped_customers_config():
    cfg = load_customers(Settings(_env_file=None).customers_config_path)
    assert cfg.customers["beyond-gravity"].plugins == ["beyond_gravity"]


def test_should_reject_empty_customers(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"customers": {}}))
    with pytest.raises(ValueError):
        load_customers(p)


def test_should_read_secrets_from_openbao_with_approle():
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append((req.method, req.url.path, req.headers.get("X-Vault-Token")))
        if req.url.path == "/v1/auth/approle/login":
            assert json.loads(req.content) == {"role_id": "r", "secret_id": "s"}
            return httpx.Response(200, json={"auth": {"client_token": "tok"}})
        return httpx.Response(200, json={"data": {"data": {"DB_PASSWORD": "pw"}}})

    s = Settings(bao_addr="http://bao:8200", bao_role_id="r", bao_secret_id="s", _env_file=None,
                 database_url="postgresql+asyncpg://ariane:${DB_PASSWORD}@db/ariane")
    secrets = fetch_secrets(s, httpx.Client(base_url=s.bao_addr, transport=httpx.MockTransport(handler)))
    assert secrets == {"DB_PASSWORD": "pw"}
    assert calls[1] == ("GET", "/v1/secret/data/ariane", "tok")
    assert resolve_database_url(s, secrets) == "postgresql+asyncpg://ariane:pw@db/ariane"


def test_should_use_environment_when_openbao_is_not_configured():
    s = Settings(_env_file=None, db_password="envpw", database_url="x://u:${DB_PASSWORD}@h/d")
    assert fetch_secrets(s) == {} and resolve_database_url(s, {}) == "x://u:envpw@h/d"
