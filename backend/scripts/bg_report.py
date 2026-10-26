"""Print the extracted netlist and control report for a Beyond Gravity drawing + parts list.

Usage: python scripts/bg_report.py <drawing.pdf> <parts_list.pdf> [--json out.json]
"""
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[2])]

from plugins.beyond_gravity.plugin import parse  # noqa: E402


def main() -> None:
    m = parse(sys.argv[1], sys.argv[2])
    print(f"Harness {m.partNumber}: {len(m.connectors)} connectors, {len(m.wires)} conductors, "
          f"{len({w.pairId for w in m.wires})} pairs")
    print("\n== CONNECTORS ==")
    for c in m.connectors:
        print(f"{c.id:12} {c.ref:20} {c.partNumber:18} cap={c.capacity} used={len(c.contacts)}")
    print("\n== NETLIST (conductor: from -> to) ==")
    for w in sorted(m.wires, key=lambda w: w.conductorId):
        to = f"{w.to.conn}:{w.to.pin}" if w.to else "?"
        print(f"{w.conductorId:8} {w.signal:11} {w.nomRed:3} {w.from_.conn}:{w.from_.pin} -> {to}")
    print("\n== CONTROL REPORT ==")
    print(m.topology["stats"] if m.topology else "")
    for i in sorted(m.issues, key=lambda i: ("error", "warning", "info").index(i.severity)):
        print(f"[{i.severity.upper():7}] {i.code}: {i.message}")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(m.model_dump_json(by_alias=True, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
