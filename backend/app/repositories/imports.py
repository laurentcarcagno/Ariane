"""Customer-scoped access: a repository is built for ONE customer and cannot see the rows of another."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ImportRecord


class ImportRepository:
    def __init__(self, session: AsyncSession, customer_id: str) -> None:
        self._s = session
        self._customer = customer_id

    async def add(self, **fields) -> ImportRecord:
        rec = ImportRecord(id=str(uuid.uuid4()), customer_id=self._customer, **fields)
        self._s.add(rec)
        await self._s.flush()
        return rec

    async def list(self) -> list[ImportRecord]:
        q = select(ImportRecord).where(ImportRecord.customer_id == self._customer).order_by(ImportRecord.created_at.desc())
        return list((await self._s.scalars(q)).all())

    async def get(self, import_id: str) -> ImportRecord | None:
        q = select(ImportRecord).where(ImportRecord.id == import_id, ImportRecord.customer_id == self._customer)
        return await self._s.scalar(q)

    async def update_model(self, import_id: str, model: dict) -> ImportRecord | None:
        """Replace the stored model (a user edit); the error and warning counters follow it."""
        rec = await self.get(import_id)
        if rec is None:
            return None
        sev = [i["severity"] for i in model["issues"]]
        rec.model, rec.errors, rec.warnings = model, sev.count("error"), sev.count("warning")
        rec.updated_at = datetime.now(timezone.utc)
        await self._s.flush()
        return rec

    async def delete(self, import_id: str) -> bool:
        r = await self._s.execute(delete(ImportRecord).where(ImportRecord.id == import_id, ImportRecord.customer_id == self._customer))
        return r.rowcount > 0
