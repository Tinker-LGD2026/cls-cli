from __future__ import annotations

from typing import Any


def select_by_name(items: list[dict[str, Any]], *, name: str, id_key: str) -> dict[str, Any]:
    matches = [item for item in items if _item_name(item) == name]
    return discovery_result("", matches, id_key)


def discovery_result(
    resource: str,
    matches: list[dict[str, Any]],
    id_key: str,
    *,
    request_ids: list[str] | None = None,
) -> dict[str, Any]:
    ambiguous = len(matches) > 1
    selected = matches[0] if len(matches) == 1 else None
    return {
        "resource": resource,
        "match_count": len(matches),
        "ambiguous": ambiguous,
        "selected": selected,
        "matches": [] if selected else matches,
        "request_ids": request_ids or [],
    }


def filter_by_name(items: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    return [item for item in items if _item_name(item) == name]


def _item_name(item: dict[str, Any]) -> str | None:
    value = item.get("Name") or item.get("AlarmName") or item.get("NoticeName")
    return str(value) if value is not None else None
