from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from cls_cli.core.errors import InputError


def load_json_payload(payload: str | None) -> dict[str, Any]:
    if payload is None:
        return {}
    if payload == "-":
        raw = sys.stdin.read()
    elif payload.startswith("@"):
        raw = Path(payload[1:]).read_text(encoding="utf-8")
    else:
        raw = payload
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON payload: {exc.msg}") from exc
    if not isinstance(loaded, dict):
        raise InputError("payload must be a JSON object")
    return loaded


def load_jsonl(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise InputError(f"invalid JSONL at line {line_number}: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise InputError(f"JSONL line {line_number} must be an object")
        rows.append(row)
    return rows


def split_csv(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_int(value: str | int | None, name: str) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise InputError(f"{name} must be a Unix timestamp integer") from exc


def parse_timestamp_ms(value: str | int | None, name: str) -> int | None:
    parsed = parse_int(value, name)
    if parsed is None:
        return None
    if parsed < 10_000_000_000:
        return parsed * 1000
    return parsed


def compact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}
