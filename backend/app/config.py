"""Runtime settings, read from the environment (see .env.example). Secrets may come from OpenBao instead."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ARIANE_", extra="ignore")

    # `${DB_PASSWORD}` is replaced by the OpenBao (or env) secret of the same name
    database_url: str = "sqlite+aiosqlite:///./data/ariane.db"
    customers_config_path: Path = ROOT / "config" / "customers.json"
    max_upload_bytes: int = 50 * 1024 * 1024

    # OIDC (Keycloak). The browser talks to `oidc_public_authority`, the backend fetches keys from `oidc_issuer`.
    auth_disabled: bool = False  # development only: every request runs as `dev_customer`
    dev_customer: str = "beyond-gravity"
    oidc_issuer: str = ""
    oidc_jwks_url: str = ""
    oidc_audience: str = "ariane-api"
    oidc_public_authority: str = ""
    oidc_client_id: str = "ariane-web"
    customer_claim: str = "customer"

    # OpenBao (AppRole). When `bao_addr` is empty, secrets come from the environment only.
    bao_addr: str = ""
    bao_role_id: str = ""
    bao_secret_id: str = ""
    bao_approle_dir: str = ""  # directory holding `role_id` and `secret_id` files (written by the init job)
    bao_kv_mount: str = "secret"
    bao_kv_path: str = "ariane"
    db_password: str = ""

    @property
    def jwks_url(self) -> str:
        return self.oidc_jwks_url or f"{self.oidc_issuer.rstrip('/')}/protocol/openid-connect/certs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
