"""Customer registry (config/customers.json): which plugins each customer may use."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, model_validator


class CustomerConfig(BaseModel):
    label: str
    plugins: list[str] = []


class CustomersConfig(BaseModel):
    customers: dict[str, CustomerConfig]

    @model_validator(mode="after")
    def _not_empty(self) -> "CustomersConfig":
        if not self.customers:
            raise ValueError("at least one customer is required")
        return self


def load_customers(path: Path) -> CustomersConfig:
    return CustomersConfig.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
