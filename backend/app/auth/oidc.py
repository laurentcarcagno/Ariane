"""Bearer-token validation against Keycloak (JWKS) and extraction of the customer scope."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings

bearer = HTTPBearer(auto_error=False)


class KeyResolver(Protocol):
    def get_signing_key_from_jwt(self, token: str): ...  # noqa: D102


@dataclass(frozen=True)
class User:
    sub: str
    username: str
    customer: str
    roles: frozenset[str] = field(default_factory=frozenset)

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles


def _deny(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status, {"error": {"code": code, "message": message}})


def decode_token(token: str, s: Settings, keys: KeyResolver) -> User:
    try:
        key = keys.get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"], audience=s.oidc_audience, issuer=s.oidc_issuer,
                            options={"require": ["exp", "iss", "sub"]})
    except jwt.PyJWTError as exc:
        raise _deny(401, "invalid_token", str(exc)) from exc
    customer = claims.get(s.customer_claim)
    if isinstance(customer, list):
        customer = customer[0] if len(customer) == 1 else None
    if not customer:
        raise _deny(403, "no_customer", "The token carries no single customer claim")
    roles = frozenset(claims.get("realm_access", {}).get("roles", []))
    return User(claims["sub"], claims.get("preferred_username", claims["sub"]), str(customer), roles)


def get_key_resolver(request: Request) -> KeyResolver | None:
    if request.app.state.settings.auth_disabled:  # no issuer configured in development: nothing to resolve
        return None
    resolver = getattr(request.app.state, "key_resolver", None)
    if resolver is None:
        resolver = request.app.state.key_resolver = jwt.PyJWKClient(request.app.state.settings.jwks_url, cache_keys=True)
    return resolver


async def current_user(request: Request, cred: HTTPAuthorizationCredentials | None = Depends(bearer),
                       keys: KeyResolver | None = Depends(get_key_resolver)) -> User:
    s: Settings = request.app.state.settings
    if s.auth_disabled:
        return User("dev", "dev", s.dev_customer, frozenset({"user", "admin"}))
    if cred is None or keys is None:
        raise _deny(401, "missing_token", "Authentication required")
    return await run_in_threadpool(decode_token, cred.credentials, s, keys)
