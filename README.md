# ARIANE

Multi-customer wiring-harness tool. It imports a harness drawing and its parts list (PDF), rebuilds the netlist and the
topology, checks them against each other and shows the result in interactive views (harness, connectors, wiring sheet,
report) and in an Excel export. Each customer is a **plugin**; the first one is **Beyond Gravity**
(`plugins/beyond_gravity`).

Rules the code keeps everywhere:

* **Local only.** The PDFs are parsed in memory by the API and are not stored (only the extracted model is). No CDN, no
  external service at runtime.
* **Never invent a connection.** An ambiguity becomes an issue in the report; it is not corrected silently. The only
  way to change the extracted data is an explicit user edit, which is logged (see [topology edits](docs/architecture.md#topology-edits)).
* **Pin letters are case-sensitive** (`c` is not `C`).
* **Customer isolation.** Every query is scoped to the customer of the signed-in user; another customer's data answers `404`.

| Document | Content |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Components, data model, request flow, security model |
| [docs/plugin-guide.md](docs/plugin-guide.md) | How to write a customer plugin |
| [docs/api.md](docs/api.md) | REST API reference |
| [docs/operations.md](docs/operations.md) | Install, secrets, migrations, backup, upgrade, troubleshooting, production checklist |
| [docs/manual/](docs/manual) | French user manual (Word) and the scripts that rebuild it |

## Run it (Docker)

```
cp .env.example .env        # fill the passwords
docker compose up -d --build
```

Open `https://localhost` (Caddy internal CA: accept the certificate once). Sign in with `alice.bg` / `dev-only-change-me`
(the realm asks for a new password at first login). Keycloak admin console: `https://localhost/auth`.

| Service | Role |
|---|---|
| caddy | TLS and single entry point: `/` UI, `/api` API, `/auth` Keycloak |
| frontend | Next.js UI (OIDC code flow with PKCE, silent token renewal) |
| backend | FastAPI: token validation (JWKS), plugins, per-customer storage, Alembic migrations at start-up |
| postgres | `ariane` and `keycloak` databases, one owner each |
| keycloak | realm `ariane` imported from `infra/keycloak/realm-ariane.json` |
| openbao | KV v2 + AppRole; the API reads `secret/ariane` at start-up |

## Develop

```
cd backend  && pip install -r requirements.txt pytest && ARIANE_AUTH_DISABLED=true python -m uvicorn app.main:app --port 8008
cd frontend && npm install && npm run dev      # proxies /api to http://localhost:8008
cd backend  && python -m pytest                # sample PDFs (git-ignored) are needed for the harness tests
cd frontend && npx tsc --noEmit && npx vitest run
```

`ARIANE_AUTH_DISABLED=true` is for local development only: every request then runs as the customer `ARIANE_DEV_CUSTOMER`.

End-to-end checks against the Docker stack (they need the sample PDFs and `npm install` in `docs/manual`):

```
cd docs/manual && node login-check.mjs     # Keycloak sign-in and sign-out
cd docs/manual && node e2e-check.mjs       # sign-in, import, segment edit, expired token
```

## Database

The schema is managed by Alembic (`backend/migrations`). The API upgrades to `head` at start-up. See
[docs/operations.md](docs/operations.md#database-migrations) for adding a migration and for upgrading a database created by
the prototype.

## Before production

See the checklist in [docs/operations.md](docs/operations.md#production-checklist).
