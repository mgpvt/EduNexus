"""Data source adapters.

Every adapter returns a raw pandas DataFrame using the *source* column names.
`repository.py` then maps them to the standard schema, so replacing Excel with
a database is a configuration change only.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from ..config import resolve_path


class DataSource(ABC):
    name: str = "base"

    @abstractmethod
    def read(self) -> pd.DataFrame: ...

    @abstractmethod
    def describe(self) -> str: ...

    def test_connection(self) -> tuple[bool, str]:
        try:
            df = self.read()
            return True, f"OK - {len(df):,} rows, {df.shape[1]} columns"
        except Exception as exc:  # noqa: BLE001
            return False, f"{type(exc).__name__}: {exc}"


class ExcelSource(DataSource):
    name = "excel"

    def __init__(self, path: str, sheet: Any = 0):
        self.path = resolve_path(path)
        self.sheet = sheet

    def read(self) -> pd.DataFrame:
        if not self.path.exists():
            raise FileNotFoundError(f"Excel file not found: {self.path}")
        if self.path.suffix.lower() == ".csv":
            return pd.read_csv(self.path, dtype=str)
        return pd.read_excel(self.path, sheet_name=self.sheet, dtype=str)

    def describe(self) -> str:
        return f"Excel workbook: {self.path.name} (sheet {self.sheet})"


class DatabaseSource(DataSource):
    """Any SQLAlchemy-supported database (PostgreSQL, SQL Server, Oracle, MySQL, SQLite)."""

    name = "database"

    def __init__(self, url: str = "", url_env: str = "EDUNEXUS_DB_URL",
                 table: str = "", query: str = ""):
        self.url = os.environ.get(url_env) or url
        self.table = table
        self.query = query

    def _sql(self) -> str:
        if self.query and self.query.strip():
            return self.query
        if not self.table:
            raise ValueError("Database source needs either `table` or `query`.")
        return f"SELECT * FROM {self.table}"

    def read(self) -> pd.DataFrame:
        if not self.url:
            raise ValueError("No database URL configured (set EDUNEXUS_DB_URL or data_source.database.url).")
        from sqlalchemy import create_engine, text

        engine = create_engine(self.url)
        with engine.connect() as conn:
            return pd.read_sql(text(self._sql()), conn)

    def describe(self) -> str:
        safe = self.url.split("@")[-1] if self.url else "(not configured)"
        return f"Database: {safe} - {self.table or 'custom query'}"


def build_source(settings: dict) -> DataSource:
    ds = settings.get("data_source", {})
    kind = (ds.get("type") or "excel").lower()
    if kind == "excel":
        x = ds.get("excel", {})
        return ExcelSource(x.get("path", "data/TestStudents.xlsx"), x.get("sheet", 0))
    if kind == "database":
        d = ds.get("database", {})
        return DatabaseSource(d.get("url", ""), d.get("url_env", "EDUNEXUS_DB_URL"),
                              d.get("table", ""), d.get("query", ""))
    raise ValueError(f"Unknown data source type: {kind}")
