import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.oidc import User, current_user
from app.config import Settings
from app.database import get_db
from app.plugins import registry
from app.repositories.imports import ImportRepository

router = APIRouter(prefix="/api/v1")


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status, {"error": {"code": code, "message": message}})


def _allowed(request: Request, user: User) -> list[str]:
    cfg = request.app.state.customers.customers.get(user.customer)
    if cfg is None:
        raise _err(403, "unknown_customer", f"Customer {user.customer!r} is not configured")
    return cfg.plugins


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/config")
def config(request: Request) -> dict:
    """Public: what the browser needs to sign in. Contains no secret."""
    s: Settings = request.app.state.settings
    return {"authDisabled": s.auth_disabled, "authority": s.oidc_public_authority or s.oidc_issuer, "clientId": s.oidc_client_id}


@router.get("/me")
def me(request: Request, user: User = Depends(current_user)) -> dict:
    cfg = request.app.state.customers.customers.get(user.customer)
    return {"username": user.username, "customer": user.customer, "label": cfg.label if cfg else user.customer,
            "roles": sorted(user.roles)}


@router.get("/plugins")
def plugins(request: Request, user: User = Depends(current_user)) -> list[dict]:
    allowed = _allowed(request, user)
    return [{k: v for k, v in p.items() if k != "module"} for pid, p in registry.discover().items() if pid in allowed]


@router.post("/imports")
async def import_files(request: Request, plugin: str = Form(...), drawing: UploadFile = File(...), bom: UploadFile = File(...),
                       user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    """Parse the uploaded PDFs on this server and keep the resulting model (not the PDFs) for the customer."""
    if plugin not in registry.discover() or plugin not in _allowed(request, user):
        raise _err(403, "plugin_not_allowed", f"Plugin {plugin!r} is not available for your customer")
    limit = request.app.state.settings.max_upload_bytes
    with tempfile.TemporaryDirectory() as tmp:
        paths: dict[str, Path] = {}
        for role, f in (("drawing", drawing), ("bom", bom)):
            data = await f.read()
            if len(data) > limit or not data.startswith(b"%PDF"):
                raise _err(422, "bad_file", f"{role}: not a PDF or too large")
            paths[role] = Path(tmp) / f"{role}.pdf"
            paths[role].write_bytes(data)
        try:
            model = await run_in_threadpool(registry.load(plugin).parse, paths["drawing"], paths["bom"])
        except Exception as exc:  # parser failure is reported, not hidden
            raise _err(422, "parse_failed", str(exc)) from exc
    body = model.model_dump(by_alias=True)
    sev = [i["severity"] for i in body["issues"]]
    rec = await ImportRepository(db, user.customer).add(
        plugin=plugin, created_by=user.username, drawing_name=drawing.filename or "drawing.pdf", bom_name=bom.filename or "bom.pdf",
        part_number=body.get("partNumber"), errors=sev.count("error"), warnings=sev.count("warning"), model=body)
    return {"id": rec.id, "model": body}


@router.get("/imports")
async def list_imports(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    return [{"id": r.id, "plugin": r.plugin, "partNumber": r.part_number, "drawing": r.drawing_name, "bom": r.bom_name,
             "createdAt": r.created_at.isoformat(), "createdBy": r.created_by, "errors": r.errors, "warnings": r.warnings}
            for r in await ImportRepository(db, user.customer).list()]


@router.get("/imports/{import_id}")
async def get_import(import_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    rec = await ImportRepository(db, user.customer).get(import_id)
    if rec is None:  # same answer for "absent" and "belongs to another customer"
        raise _err(404, "not_found", "Import not found")
    return {"id": rec.id, "model": rec.model}


@router.delete("/imports/{import_id}", status_code=204)
async def delete_import(import_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> None:
    if not await ImportRepository(db, user.customer).delete(import_id):
        raise _err(404, "not_found", "Import not found")
