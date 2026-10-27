# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

ARIANE is a multi-customer wiring-harness tool: it imports a harness drawing and parts list (PDF), rebuilds the netlist and topology, cross-checks them, and shows the result in interactive views and an Excel export. Each customer is a plugin (first one: `plugins/beyond_gravity`). `README.md` and `docs/` (architecture, plugin-guide, api, operations) are the detailed references; the user manual in `docs/manual` is in French. `instructions.md` is the original French mission brief.

## Commands

```
# Backend (Python >= 3.11)
cd backend && pip install -r requirements.txt pytest
cd backend && ARIANE_AUTH_DISABLED=true python -m uvicorn app.main:app --port 8008
cd backend && python -m pytest                       # also collects ../plugins (see pyproject testpaths)
cd backend && python -m pytest tests/test_api.py -k name
cd backend && python -m pytest ../plugins/beyond_gravity/test_netlist.py

# Frontend (Next.js, proxies /api to localhost:8008)
cd frontend && npm install && npm run dev
cd frontend && npx tsc --noEmit && npx vitest run    # npx vitest run src/lib/flags.test.ts for one file

# Full stack
cp .env.example .env && docker compose up -d --build   # https://localhost via Caddy
cd docs/manual && node e2e-check.mjs                   # end-to-end against the Docker stack (needs sample PDFs)
```

`ARIANE_AUTH_DISABLED=true` is dev-only: every request runs as customer `ARIANE_DEV_CUSTOMER`. Sample PDFs are git-ignored; tests needing them must skip when absent. Schema changes need an Alembic migration in `backend/migrations/versions` (API upgrades to `head` at start-up).

## Architecture

- Backend layering: `routers` → `services` → `repositories` (the only code touching the DB) → `models`. `app/core/pdf` is generic PDF extraction (derotated words, vector drawings, graph helpers); `app/plugins` holds the plugin contract (`model.py`) and discovery (`registry.py`, discovered once at first use).
- A plugin's `parse(drawing, bom)` returns a customer-independent `HarnessModel`, stored as JSON in `imports.model`. The frontend and Excel export depend only on this model — never on a customer. The model also carries the schematic's vector graphics/words so the UI redraws without the PDF.
- `config/customers.json` maps customer → enabled plugins; the customer comes from the `customer` claim of the Keycloak token. Auth is RS256/JWKS (`app/auth/oidc.py`); DB password comes from OpenBao at start-up.
- Topology edits (only `diameterMm` and `bomItems` of a segment) go through `services/topology_edit.py` and are always logged in `topology.edits`, with issues updated and the Excel `Source` column showing `plan`/`saisi`. Connections are never editable.
- Plugin module `plugins/beyond_gravity`: `netlist.py`, `topology.py`, `bom.py`, `checks.py`, `inserts.py` (known insert pin layouts → `Connector.emptyPins`; add a layout only when known from the standard).
- Frontend: Next.js client components in `frontend/src/components`, API client in `lib/api.ts`, OIDC via `lib/auth.ts`. Design tokens in `DESIGN.md`/`DESIGN.json` (Hemeria charter).

## Invariants to preserve

- **Never invent a connection.** Ambiguity becomes an `Issue` (stable `code`), never a silent correction.
- **Pin letters are case-sensitive**; do not normalise.
- **Customer isolation:** every repository statement filters on `customer_id`; another customer's data answers `404` (not 403).
- **Local only:** PDFs parsed in memory/temp dir and never stored; no CDN or external call at runtime.
- Excel export writes text starting with `=` as a string (injection guard).
- Locate PDF blocks from headers and token types, not hard-coded coordinates.
- Customer data (PDFs, screenshots) stays out of the repo.
