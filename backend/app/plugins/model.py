"""Customer-independent harness model produced by every plugin."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Location(BaseModel):
    page: int
    x: float
    y: float


class Box(BaseModel):
    """Rectangle on a source PDF page, in displayed (derotated) points."""
    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    role: Literal["from", "to"]


class Ref(BaseModel):
    """Model entity an issue is about: lets a viewer flag it (connector face pin, segment, node, wire)."""
    conn: str | None = None
    pin: str | None = None
    segment: str | None = None
    node: str | None = None
    wire: str | None = None


class Issue(BaseModel):
    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    where: list[Location] = Field(default_factory=list)
    refs: list[Ref] = Field(default_factory=list)


class Cell(BaseModel):
    """A word of the drawing with its position (displayed points), so a viewer can redraw the sheet layout."""
    t: str
    x0: float
    y0: float
    x1: float
    y1: float


class Contact(BaseModel):
    pin: str  # case-sensitive: "c" != "C"
    wireIds: list[str] = Field(default_factory=list)
    # row as written on the drawing (kept verbatim so a viewer can redraw the table, anomalies included)
    polarity: str | None = None
    signal: str | None = None
    nomRed: str | None = None
    dest: str | None = None  # "INIT_B_P1:w"
    origin: str | None = None  # "SC_I_#x-4_J02:G"
    wire: str | None = None  # "907-37"
    cells: list[Cell] = Field(default_factory=list)  # every word of the row, at its drawing position
    wireCell: Cell | None = None  # the red wire number written between the two rows of a pair


class Connector(BaseModel):
    id: str
    ref: str
    partNumber: str
    capacity: int | None = None
    contacts: list[Contact] = Field(default_factory=list)
    emptyPins: list[str] | None = None  # unused places of the insert; None when the plugin does not know its pin layout
    page: int | None = None
    header: list[Cell] = Field(default_factory=list)  # title words ("S/C I #x-1 J01", part number) at their position


class Endpoint(BaseModel):
    conn: str
    pin: str


class Wire(BaseModel):
    id: str  # "907-01" (twisted pair number)
    conductorId: str  # "907-01+"
    type: str | None = None
    pairId: str
    polarity: Literal["+", "-"]
    signal: str
    nomRed: str
    from_: Endpoint = Field(alias="from")
    to: Endpoint | None = None
    marks: list[Box] = Field(default_factory=list)  # where this conductor is written on the drawing

    model_config = {"populate_by_name": True}


class BomItem(BaseModel):
    position: str
    partNumber: str
    description: str
    amount: str
    unit: str = ""
    notes: str = ""
    tbd: bool = False


class GPath(BaseModel):
    """A vector path of a source sheet (colours as #rrggbb), to redraw the sheet without the PDF."""
    d: str
    c: str | None = None  # stroke
    w: float = 0.7
    f: str | None = None  # fill


class Sheet(BaseModel):
    """Size of a source sheet and the words not owned by any connector table (notes, title block...)."""
    width: float
    height: float
    texts: list[Cell] = Field(default_factory=list)


class HarnessModel(BaseModel):
    plugin: str
    partNumber: str | None = None
    connectors: list[Connector] = Field(default_factory=list)
    wires: list[Wire] = Field(default_factory=list)
    bom: list[BomItem] = Field(default_factory=list)
    topology: dict | None = None
    routes: dict[str, list[str]] = Field(default_factory=dict)
    issues: list[Issue] = Field(default_factory=list)
    graphics: dict[str, list[GPath]] = Field(default_factory=dict)  # page index -> vector paths
    sheets: dict[str, Sheet] = Field(default_factory=dict)  # page index -> size and free text
