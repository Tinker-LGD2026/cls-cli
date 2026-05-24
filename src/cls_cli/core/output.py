from __future__ import annotations

import json
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from cls_cli.core.errors import CliError

SENSITIVE_KEYS = {"secretid", "secretkey", "token", "authorization", "signature"}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower().replace("_", "") in SENSITIVE_KEYS:
                result[key] = "***REDACTED***"
            else:
                result[key] = redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def emit_data(data: Any, output: str = "json") -> None:
    safe_data = redact(data)
    if output == "table":
        emit_table(safe_data)
        return
    if output == "jsonl" and isinstance(safe_data, list):
        for row in safe_data:
            typer.echo(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
        return
    typer.echo(json.dumps({"data": safe_data}, ensure_ascii=False, separators=(",", ":")))


def emit_error(error: CliError) -> None:
    typer.echo(
        json.dumps({"error": redact(error.to_dict())}, ensure_ascii=False, separators=(",", ":"))
    )


def emit_table(data: Any) -> None:
    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("key")
    table.add_column("value")
    if isinstance(data, dict):
        flattened = _flatten(data)
        for key, value in flattened.items():
            table.add_row(key, str(value))
    else:
        table.add_row("value", str(data))
    console.print(table)


def _flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in data.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten(value, name))
        else:
            result[name] = value
    return result
