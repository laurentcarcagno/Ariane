# Operations

## Install

```
cp .env.example .env     # POSTGRES_ADMIN_PASSWORD, ARIANE_DB_PASSWORD, KEYCLOAK_DB_PASSWORD, KEYCLOAK_ADMIN_PASSWORD
docker compose up -d --build
docker compose ps         # every service Up or healthy; openbao-init exits 0 once
```

Behind a corporate proxy, set `HTTP_PROXY` and `HTTPS_PROXY` in `.env` (used at image build time only). Set `ARIANE_HOST`
to the public host name (default `localhost`); it feeds the Caddy site, the Keycloak hostname and the token issuer.

## Configuration

Environment variables of the API (prefix `ARIANE_`, see `backend/app/config.py`):

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | SQLAlchemy async URL. `${DB_PASSWORD}` is replaced by the OpenBao secret `DB_PASSWORD` |
| `CUSTOMERS_CONFIG_PATH` | `config/customers.json` |
| `MAX_UPLOAD_BYTES` | Upload limit per PDF (default 50 MB; Caddy limits the whole body to 60 MB) |
| `OIDC_ISSUER`, `OIDC_JWKS_URL`, `OIDC_AUDIENCE`, `OIDC_PUBLIC_AUTHORITY`, `OIDC_CLIENT_ID`, `CUSTOMER_CLAIM` | Keycloak validation and what the browser is told |
| `BAO_ADDR`, `BAO_APPROLE_DIR`, `BAO_KV_MOUNT`, `BAO_KV_PATH` | OpenBao lookup; an empty `BAO_ADDR` means environment only |
| `AUTH_DISABLED`, `DEV_CUSTOMER` | Development only |

## Customers and users

* Add a customer and its plugins in `config/customers.json`, then restart the backend.
* Create the user in Keycloak (`https://<host>/auth`, realm `ariane`), set the **`customer`** attribute to the customer id
  and give the realm role `user`. A token without exactly one `customer` claim is refused (`403 no_customer`).

## Database migrations

Alembic lives in `backend/` (`alembic.ini`, `migrations/`). The API runs `upgrade head` when it starts, so a normal
deployment needs no manual step.

* A database created by the prototype (tables made by `create_all`, no `alembic_version`) is adopted by revision `0001`,
  which leaves an existing `imports` table alone. Revision `0002` then adds `updated_at`.
* New migration after a change in `app/models.py`:

  ```
  cd backend
  ARIANE_DATABASE_URL=postgresql+asyncpg://ariane:<password>@localhost:5432/ariane alembic revision --autogenerate -m "what changed"
  ```

  Read the generated file: autogenerate does not see everything (renames, data moves). Name revisions `000N_...`.
* By hand: `alembic upgrade head`, `alembic downgrade -1`, `alembic current`. The CLI needs a full URL (it does not call OpenBao).
* Back up before an upgrade.

## Backup and restore

```
docker compose exec -T postgres pg_dump -U postgres ariane > ariane-backup.sql
docker compose exec -T postgres psql -U postgres ariane < ariane-backup.sql     # into an empty database
```

Back up the `bao_data`, `bao_init` and `pg_data` volumes too. The PDFs are not stored, so a restored model cannot be re-parsed
without the original files. Keep the Keycloak realm file (`infra/keycloak/realm-ariane.json`) in version control.

## Upgrade

```
git pull
docker compose build backend frontend
docker compose up -d backend frontend       # the backend migrates the database on start
```

After a backend change in development, restart both the dev API (port 8008) and the Docker backend. The Docker frontend needs a rebuild.

## Troubleshooting

| Symptom | Check |
|---|---|
| Login loops or "Connexion impossible" | `curl -k https://<host>/api/v1/config` returns `authority`; browser clock; certificate accepted |
| `401 invalid_token` | `ARIANE_OIDC_ISSUER` must equal the token `iss` (the public host name); the client `ariane-web` needs the audience `ariane-api` |
| `403 no_customer` | the user has no `customer` attribute |
| `403 plugin_not_allowed` | plugin missing in `config/customers.json` for that customer |
| Backend unhealthy at start | `docker compose logs backend`: OpenBao sealed or not initialised, wrong DB password, failed migration |
| Export lacks the cover or the logo | stale backend: rebuild and restart it; Pillow must be installed |
| `422 parse_failed` | the PDFs do not match the plugin; the message names the cause |

## Production checklist

- [ ] Real host name in `ARIANE_HOST`, a real certificate (replace `tls internal`), redirect URIs in the realm file limited to that host.
- [ ] Development user removed from `infra/keycloak/realm-ariane.json`; Keycloak admin password set; MFA for admins.
- [ ] OpenBao: `infra/openbao/init.sh` keeps one unseal key in a volume so the stack restarts unattended. Use several key shares held by
      different people and delete `/openbao/init`.
- [ ] Access token and SSO session lifetimes set in the realm to your policy (the UI renews tokens silently).
- [ ] Backups scheduled and a restore tested.
- [ ] No published port other than 80 and 443; no `AUTH_DISABLED`.
- [ ] Customer drawings and the generated manual (its screenshots show real plan data) kept out of public repositories.
