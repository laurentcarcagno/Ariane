# ARIANE

Multi-customer wiring-harness tool: import a harness drawing and its parts list, rebuild the netlist and the
topology, check them against each other, and browse the result (harness, connectors, wiring sheet, original
drawing, report). Each customer is a **plugin**; the first one is **Beyond Gravity** (`plugins/beyond_gravity`).

Everything is processed on your own servers: the PDFs are parsed in memory by the API and **not stored** (only the
extracted model is), no CDN or external service is used at runtime.

## Run it (Docker)

```
cp .env.example .env        # fill the four passwords
docker compose up -d --build
```

Open `https://localhost` (Caddy internal CA: accept the certificate once). Sign in with `alice.bg` / `dev-only-change-me`
(the realm asks for a new password at first login). Keycloak admin console: `https://localhost/auth`.

| Service | Role |
|---|---|
| caddy | TLS and single entry point: `/` UI, `/api` API, `/auth` Keycloak |
| frontend | Next.js UI (OIDC code flow with PKCE) |
| backend | FastAPI: token validation (JWKS), plugins, per-customer storage |
| postgres | `ariane` and `keycloak` databases, one owner each |
| keycloak | realm `ariane` imported from `infra/keycloak/realm-ariane.json` |
| openbao | KV v2 + AppRole; the API reads `secret/ariane` at start-up |

## Customers and plugins

* `config/customers.json` lists customers and the plugins each may use.
* A user belongs to one customer through the `customer` attribute (admin-only in Keycloak), exposed as the `customer`
  claim. Every query is filtered by it; another customer's data answers `404`.
* A plugin is `plugins/<name>/` with a `manifest.json` and a `plugin.py` exposing `parse(drawing, bom) -> HarnessModel`
  (`backend/app/plugins/model.py`). The UI only depends on that model.

## Develop

```
cd backend  && pip install -r requirements.txt pytest && ARIANE_AUTH_DISABLED=true uvicorn app.main:app --port 8008
cd frontend && npm install && npm run dev      # proxies /api to http://localhost:8008
cd backend  && python -m pytest                # sample PDFs (git-ignored) are needed for the harness tests
```

`ARIANE_AUTH_DISABLED=true` is for local development only.

## Before production

* OpenBao: `infra/openbao/init.sh` keeps a single unseal key in a volume so the stack restarts unattended. Use several
  key shares held by different people and delete `/openbao/init`.
* Keycloak: remove the dev user from the realm file, set real hostnames and redirect URIs (`https://localhost/*`).
* Replace `create_all` with Alembic migrations before the first schema change.
