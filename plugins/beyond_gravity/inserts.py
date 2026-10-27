"""Contact layout of the connector inserts, so unused places can be named instead of only counted.

Keyed by the insert code of the part number (D38999/20FD19SN -> 20FD19: shell 20, insert arrangement 19).
Add an insert only once its layout is known from the standard (MIL-DTL-38999); a connector whose insert is
absent here keeps `emptyPins = None` and the UI shows the count only.
"""
from __future__ import annotations

import re

INSERT_CODE = re.compile(r"D38999/(\d{2}[A-Z]{2}\d{2,3})[A-Z]{2}$")
# letters skip I, O and Q; 20-19 carries 19 contacts
INSERTS: dict[str, str] = {"20FD19": "ABCDEFGHJKLMNPRSTUV"}


def empty_pins(part_number: str, used: list[str], capacity: int | None) -> list[str] | None:
    """Places of the insert not used by any row, or None if the layout is unknown or contradicts the drawing."""
    m = INSERT_CODE.search(part_number)
    layout = INSERTS.get(m.group(1)) if m else None
    if layout is None or (capacity and len(layout) != capacity) or not set(used) <= set(layout):
        return None
    return [p for p in layout if p not in used]
