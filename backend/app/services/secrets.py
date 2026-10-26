"""OpenBao client (KV v2 through AppRole). No SDK: two HTTPS calls with httpx."""
from __future__ import annotations

from pathlib import Path

import httpx

from app.config import Settings


def _approle(s: Settings) -> tuple[str, str]:
    if s.bao_approle_dir:
        d = Path(s.bao_approle_dir)
        return (d / "role_id").read_text().strip(), (d / "secret_id").read_text().strip()
    return s.bao_role_id, s.bao_secret_id


def fetch_secrets(s: Settings, client: httpx.Client | None = None) -> dict[str, str]:
    if not s.bao_addr:
        return {}
    own = client is None
    http = client or httpx.Client(base_url=s.bao_addr, timeout=10)
    try:
        role_id, secret_id = _approle(s)
        login = http.post("/v1/auth/approle/login", json={"role_id": role_id, "secret_id": secret_id})
        login.raise_for_status()
        token = login.json()["auth"]["client_token"]
        r = http.get(f"/v1/{s.bao_kv_mount}/data/{s.bao_kv_path}", headers={"X-Vault-Token": token})
        r.raise_for_status()
        return {k: str(v) for k, v in r.json()["data"]["data"].items()}
    finally:
        if own:
            http.close()


def resolve_database_url(s: Settings, secrets: dict[str, str]) -> str:
    password = secrets.get("DB_PASSWORD") or s.db_password
    return s.database_url.replace("${DB_PASSWORD}", password)
