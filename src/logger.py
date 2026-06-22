from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class JsonlLogger:
    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def market_snapshot(self, payload: Any) -> None:
        self._write("market_snapshots.jsonl", payload)

    def signal(self, payload: Any) -> None:
        self._write("signals.jsonl", payload)

    def unmatched_market(self, payload: Any) -> None:
        self._write("unmatched_markets.jsonl", payload)

    def error(self, payload: Any) -> None:
        self._write("errors.jsonl", payload)

    def _write(self, filename: str, payload: Any) -> None:
        encoded = json.dumps(_jsonable(payload), ensure_ascii=False, sort_keys=True)
        with (self.data_dir / filename).open("a", encoding="utf-8") as handle:
            handle.write(encoded + "\n")


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value
