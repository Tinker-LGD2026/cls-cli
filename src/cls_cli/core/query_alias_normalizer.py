from __future__ import annotations

import re
from dataclasses import dataclass

STRICT_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
AS_ALIAS_RE = re.compile(r"(?i)\bas\s+([^\s,]+)")


@dataclass(frozen=True)
class AliasNormalizationResult:
    query: str
    alias_map: dict[str, str]
    condition_hints: list[str]


def normalize_query_aliases(query: str) -> AliasNormalizationResult:
    alias_map: dict[str, str] = {}
    normalized_parts: list[str] = []
    used: set[str] = set()
    condition_hints: list[str] = []
    cursor = 0

    for match in AS_ALIAS_RE.finditer(query):
        token = match.group(1)
        raw = token.strip('"`')
        normalized_parts.append(query[cursor : match.start(1)])
        if STRICT_IDENTIFIER_RE.match(raw):
            used.add(raw)
            normalized_parts.append(token)
        else:
            replacement = _suggest_alias(raw, used)
            used.add(replacement)
            alias_map[raw] = replacement
            condition_hints.append(f"$1.{replacement} > 0")
            normalized_parts.append(replacement)
        cursor = match.end(1)

    normalized_parts.append(query[cursor:])
    normalized = "".join(normalized_parts)
    for raw, replacement in alias_map.items():
        normalized = normalized.replace(f'"{raw}"', replacement).replace(f"`{raw}`", replacement)
    return AliasNormalizationResult(normalized, alias_map, condition_hints)


def _suggest_alias(raw: str, used: set[str]) -> str:
    lowered = raw.lower()
    if "p95" in lowered or "95" in raw:
        base = "p95_value"
    elif "错误" in raw or "error" in lowered or "5xx" in lowered:
        base = "error_count"
    elif "次数" in raw or "count" in lowered or "数量" in raw:
        base = "event_count"
    else:
        base = "value"
    if base not in used:
        return base
    index = 2
    while f"{base}_{index}" in used:
        index += 1
    return f"{base}_{index}"
