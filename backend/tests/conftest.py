import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

ISSUER = "https://sso.test/realms/ariane"


class FakeKeys:
    """Stands in for the JWKS client: one RSA key pair generated for the test run."""

    def __init__(self) -> None:
        self.private = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def get_signing_key_from_jwt(self, token: str):
        pub = self.private.public_key()

        class K:
            key = pub

        return K()

    def token(self, customer: str | None = "beyond-gravity", **over) -> str:
        claims = {"sub": str(uuid.uuid4()), "preferred_username": "alice", "iss": ISSUER, "aud": "ariane-api",
                  "exp": int(time.time()) + 300, "realm_access": {"roles": ["user"]}, **({"customer": customer} if customer else {}), **over}
        return jwt.encode(claims, self.private, algorithm="RS256")


@pytest.fixture(scope="session")
def keys() -> FakeKeys:
    return FakeKeys()


def make_client(tmp_path, keys: FakeKeys, **over) -> TestClient:
    s = Settings(database_url=f"sqlite+aiosqlite:///{tmp_path / 't.db'}", oidc_issuer=ISSUER, _env_file=None, **over)
    app = create_app(s)
    app.state.key_resolver = keys
    return TestClient(app)


@pytest.fixture
def client(tmp_path, keys):
    with make_client(tmp_path, keys) as c:
        yield c


@pytest.fixture
def dev_client(tmp_path, keys):
    with make_client(tmp_path, keys, auth_disabled=True) as c:
        yield c
