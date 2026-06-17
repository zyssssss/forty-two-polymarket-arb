from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


class EventLogger:
    TABLES = ("raw_market_snapshot", "signal_log", "order_log", "position_log", "error_log", "pnl_log")

    def __init__(self, database_path: str, jsonl_dir: str) -> None:
        self.database_path = Path(database_path)
        self.jsonl_dir = Path(jsonl_dir)
        self.jsonl_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def log(self, table: str, payload: Any) -> None:
        if table not in self.TABLES:
            raise ValueError(f"Unknown log table: {table}")
        encoded = json.dumps(_to_jsonable(payload), ensure_ascii=False, sort_keys=True)
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(f"INSERT INTO {table} (created_at, payload) VALUES (?, ?)", (datetime.utcnow().isoformat(), encoded))
        with (self.jsonl_dir / f"{table}.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(encoded + "\n")

    def _init_db(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            for table in self.TABLES:
                conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        payload TEXT NOT NULL
                    )
                    """
                )


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value
