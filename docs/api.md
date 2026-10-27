# REST API

Base path `/api/v1`. Every route except `health` and `config` needs `Authorization: Bearer <access token>`
(`ARIANE_AUTH_DISABLED=true` skips this in development). Errors have the shape
`{"detail": {"error": {"code": "...", "message": "..."}}}`.

| Method and path | Purpose | Errors |
|---|---|---|
| `GET /health` | Liveness (public) | |
| `GET /config` | What the browser needs to sign in: `authDisabled`, `authority`, `clientId` (public, no secret) | |
| `GET /me` | Signed-in user, customer, roles | |
| `GET /plugins` | Plugins enabled for the customer | `403 unknown_customer` |
| `POST /imports` | Analyse a drawing and a BOM (multipart `plugin`, `drawing`, `bom`) | `403 plugin_not_allowed`, `422 bad_file`, `422 parse_failed` |
| `GET /imports` | The customer's analyses, newest first | |
| `GET /imports/{id}` | One stored model | `404` if absent or another customer's |
| `PATCH /imports/{id}/segments/{segment}` | Fill in `diameterMm` and/or `bomItems` of a segment; returns the updated model | `404 segment_not_found`, `422` on bad values |
| `GET /imports/{id}/export.xlsx` | Excel workbook with default cover settings | `404` |
| `POST /imports/{id}/export.xlsx` | Same, with the cover-page form: `edition`, `subtitle`, `classification`, `export_control`, `quality_manager`, `project_manager`, `redactor` | `404`, `422` on invalid values |
| `DELETE /imports/{id}` | Delete an analysis | `404`, `204` |

Interactive documentation: `/api/docs` (OpenAPI at `/api/openapi.json`).

## Segment edit

```
PATCH /api/v1/imports/{id}/segments/S03
{ "diameterMm": 2.5, "bomItems": ["07", "09"] }
```

Both fields are optional. `diameterMm` is in ]0, 100]; `bomItems` are two-digit positions, each used once. The change is
logged in `topology.edits` and reported as the info issue `topology-edited`.

## Excel workbook

Sheets: `Page de garde` (REQMAP HMA-C-049 cover, filled from the model and the form), then `From-To`, `Connecteurs`
(including the empty places of known inserts), `Segments` (with a `Source` column: `plan` or `saisi`), `Nomenclature`,
`Rapport`. Every data sheet starts with a 4-line banner (logo, title, reference, date, edition), one blank row, then the table.
