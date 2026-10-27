# Writing a customer plugin

A plugin turns one customer's documents into the generic `HarnessModel`. Nothing else in ARIANE knows the customer.

## Layout

```
plugins/<name>/
  manifest.json     id, label, version, inputs[]
  plugin.py         parse(drawing, bom) -> HarnessModel
  ...               parsers, checks, tests
```

`manifest.json`:

```json
{ "id": "my_customer", "label": "My customer", "version": "0.1.0",
  "inputs": [ {"role": "drawing", "label": "Harness drawing", "accept": ".pdf"},
              {"role": "bom", "label": "Parts list", "accept": ".pdf"} ] }
```

The upload form is built from `inputs`. The API accepts the two roles `drawing` and `bom`; a new role needs a change in
`routers/api.py` (`import_files`).

## Contract

* `parse(drawing: Path, bom: Path) -> HarnessModel` (`backend/app/plugins/model.py`). Raise on an unreadable file: the API
  answers `422 parse_failed` with the message.
* **Never invent.** If the documents are ambiguous, add an `Issue` (`error`, `warning` or `info`, a stable `code`, a message,
  `where` locations on the source page, `refs` to the connector, pin, segment or wire concerned). Do not correct silently.
* **Case matters** for pin names. Do not normalise them.
* Fill `Contact.cells`, `Connector.header` and `Wire.marks` if you want the wiring sheet view to redraw the source layout.
* Routes: `routes[pairId] = [segmentId, ...]`. A pair that cannot be routed is an `unrouted` error, not a guess.
* `Connector.emptyPins`: set it only when the insert layout is known (see `inserts.py` in the Beyond Gravity plugin).
* Use `app.core.pdf` (words, drawings, graph) for extraction. Locate blocks from headers and token types, not from
  hard-coded coordinates, so other drawings of the same supplier keep working.

## Enabling it

1. Add the plugin id to the customer in `config/customers.json`.
2. Restart the API (plugins are discovered once, at first use).
3. Add tests next to the plugin (`test_*.py`). Sample PDFs are git-ignored, so skip the tests that need them when they are absent.

## Checklist

- [ ] Counts cross-checked against the parts list (as issues, not exceptions).
- [ ] No network call, no file written outside the temporary directory.
- [ ] Customer data (PDFs, screenshots) stays out of the repository. The Excel export already writes text starting with `=` as text.
