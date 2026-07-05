from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


class JsonlLogger:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def market_snapshot(self, payload: dict[str, Any]) -> None:
        self._write("market_snapshots.jsonl", payload)

    def signal(self, payload: Any) -> None:
        self._write("signals.jsonl", payload)

    def unmatched(self, payload: dict[str, Any]) -> None:
        self._write("unmatched_markets.jsonl", payload)

    def error(self, payload: dict[str, Any]) -> None:
        self._write("errors.jsonl", payload)

    def _write(self, name: str, payload: Any) -> None:
        path = self.data_dir / name
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(to_jsonable(payload), ensure_ascii=False, separators=(",", ":")) + "\n")


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(v) for v in value]
    return value
