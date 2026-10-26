import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.plugins import registry

router = APIRouter(prefix="/api/v1")
MAX_BYTES = 50 * 1024 * 1024


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/plugins")
def plugins() -> list[dict]:
    return [{k: v for k, v in p.items() if k != "module"} for p in registry.discover().values()]


@router.post("/imports")
async def import_files(plugin: str = Form(...), drawing: UploadFile = File(...), bom: UploadFile = File(...)) -> dict:
    """Parse the uploaded PDFs locally and return the harness model. Nothing is stored or sent elsewhere."""
    if plugin not in registry.discover():
        raise HTTPException(422, {"error": {"code": "unknown_plugin", "message": f"Unknown plugin {plugin!r}"}})
    with tempfile.TemporaryDirectory() as tmp:
        paths = {}
        for role, f in (("drawing", drawing), ("bom", bom)):
            data = await f.read()
            if len(data) > MAX_BYTES or not data.startswith(b"%PDF"):
                raise HTTPException(422, {"error": {"code": "bad_file", "message": f"{role}: not a PDF or too large"}})
            paths[role] = Path(tmp) / f"{role}.pdf"
            paths[role].write_bytes(data)
        try:
            model = registry.load(plugin).parse(paths["drawing"], paths["bom"])
        except Exception as exc:  # parser failure is reported, not hidden
            raise HTTPException(422, {"error": {"code": "parse_failed", "message": str(exc)}}) from exc
    return model.model_dump(by_alias=True)
