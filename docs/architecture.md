# Architecture

## Components

```
browser --https--> caddy --/--------> frontend (Next.js)
                         |- /api ---> backend  (FastAPI) --> postgres (ariane)
                         '- /auth --> keycloak -----------> postgres (keycloak)
                                      backend --AppRole--> openbao (secret/ariane)
```

* **Caddy** terminates TLS (`tls internal` for a local CA), sets HSTS and `nosniff`, limits request bodies to 60 MB.
* **Frontend**: Next.js client components. It signs the user in with `oidc-client-ts` (authorization code + PKCE) and
  sends the access token as a bearer token. The token is renewed in the background; a `401` sends the user back through
  the login page.
* **Backend** layers: `routers` (HTTP) → `services` (export, topology edit, customers, secrets) → `repositories` (the only
  code that touches the database) → `models`. `core/pdf` holds the generic PDF extraction (words with derotated
  coordinates, vector drawings, graph helpers). `plugins/` holds the plugin contract and discovery.
* **Keycloak** authenticates users. A user has a `customer` attribute (admin-only) exposed as the `customer` claim.
* **OpenBao** stores the database password. The backend logs in with AppRole and reads `secret/ariane` at start-up.

## Source layout

```
backend/app/{routers,services,repositories,auth,core,plugins}   backend/migrations (Alembic)   backend/tests
plugins/<customer>/        manifest.json, plugin.py, parser modules, tests
frontend/src/{app,components,lib}
config/customers.json      customer -> enabled plugins
config/templates/          Excel cover sheet template (HMA-C-049)
infra/{caddy,keycloak,openbao,postgres}
docs/manual/               Word manual and its build scripts
```

## Data model

Plugins return a customer-independent `HarnessModel` (`backend/app/plugins/model.py`), stored as JSON in
`imports.model`: connectors (contacts and, when the insert layout is known, `emptyPins`), wires, BOM, topology (nodes,
segments, `edits`), routes (pair → segment ids), issues, plus the vector graphics and words of the schematic sheet so the
UI can redraw it without the PDF. The UI and the exports depend only on this model.

Table `imports` (one row per analysis): `id`, `customer_id` (indexed), `plugin`, `created_by`, `created_at`,
`updated_at` (set when a user edits the topology), file names, `part_number`, `errors`, `warnings`, `model`.

## Request flow: import

1. `POST /api/v1/imports` (multipart: `plugin`, `drawing`, `bom`). The token gives the customer; the plugin must be enabled for it.
2. Files are checked (`%PDF` header, size ≤ `max_upload_bytes`), written to a temporary directory and parsed in a worker
   thread by `plugin.parse(drawing, bom)`.
3. The temporary files are deleted; the model, the file names and the error and warning counters are stored for the customer.

## Security model

* **Authentication**: RS256 access tokens checked against the Keycloak JWKS: signature, `exp`, `iss`, `aud`
  (`ariane-api`) and a single `customer` claim. Anything else is `401` or `403`.
* **Isolation**: `ImportRepository` is built for one customer and every statement filters on `customer_id`. "Not found"
  and "belongs to another customer" both answer `404`. Tests cover read, export, edit and delete.
* **Plugins per customer**: `config/customers.json`; a plugin not listed for the customer answers `403`.
* **Uploads**: PDF signature and size checked; parsed server-side only; never stored.
* **Excel injection**: text starting with `=` is written as a string in every cell (extracted text and form fields).
* **Secrets**: nothing in the repository; `.env` holds bootstrap passwords only; the database password comes from OpenBao.
* **Network**: only Caddy publishes ports. The backend container runs as a non-root user.

## Topology edits

The topology sheets sometimes lack a diameter or a BOM item (for example the segment N3A–N1A has no diameter). A user can
fill them in from the segment panel (`PATCH /api/v1/imports/{id}/segments/{segment}`). Only `diameterMm` and `bomItems` are
editable. An edit never hides its origin:

* it is appended to `topology.edits` (`segment`, `field`, `before`, `after`, `by`, `at`);
* the matching `diameter-*` and `segment-no-bom` issues are removed and an info issue `topology-edited` records the change;
* the Excel `Segments` sheet has a `Source` column (`plan` or `saisi`);
* `imports.updated_at` and the error and warning counters are updated.

Connections (nodes, segment ends, routes) cannot be edited: they come from the drawing, or they are reported.

## Empty places

`Connector.emptyPins` lists the unused places of an insert when the plugin knows the pin layout of that insert
(`plugins/beyond_gravity/inserts.py`; today the 20FD19 insert, where C, F and M are free on every S/C block). It is `null`
when the layout is unknown or contradicts the drawing, and the UI then shows the count only. A layout is added only once it
is known from the standard.
