from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from cls_cli.core.errors import InputError

STRICT_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
FIELD_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.$-]{0,127}$")
CONDITION_REF_RE = re.compile(r"\$(\d+)\.([A-Za-z_][A-Za-z0-9_]*)")
AS_ALIAS_RE = re.compile(r"\bas\s+([^\s,]+(?:\s+[^\s,]+)*)", re.IGNORECASE)


@dataclass(frozen=True)
class PolicyIssue:
    code: str
    message: str
    path: str
    suggestion: str | None = None
    severity: str = "error"

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "suggestion": self.suggestion,
            "severity": self.severity,
        }


def has_blocking_policy_issues(issues: list[PolicyIssue]) -> bool:
    return any(issue.severity == "error" for issue in issues)


def scaffold_policy_payload(
    *,
    name: str,
    logset_id: str,
    topic_id: str,
    query: str,
    condition: str,
    notice_ids: list[str] | None,
    start_time_offset: int = -5,
    end_time_offset: int = 0,
    monitor_period: int = 1,
    monitor_type: str = "Period",
    cron_expression: str | None = None,
    trigger_count: int = 1,
    alarm_period: int = 15,
    alarm_level: int = 0,
    multi_conditions: list[Any] | None = None,
    group_trigger_status: bool | None = None,
    group_trigger_condition: list[str] | None = None,
    analysis: list[Any] | None = None,
    classifications: list[Any] | None = None,
    message_template: str | None = None,
    callback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not query.strip():
        raise InputError("query is required")
    if not condition.strip():
        raise InputError("condition is required")
    payload: dict[str, Any] = {
        "Name": name,
        "AlarmTargets": [
            {
                "Query": query,
                "Number": 1,
                "StartTimeOffset": start_time_offset,
                "EndTimeOffset": end_time_offset,
                "SyntaxRule": 1,
                "LogsetId": logset_id,
                "TopicId": topic_id,
            }
        ],
        "MonitorTime": _monitor_time_payload(monitor_type, monitor_period, cron_expression),
        "TriggerCount": trigger_count,
        "AlarmPeriod": alarm_period,
        "Status": True,
        "MonitorObjectType": 0,
    }
    if multi_conditions is None:
        payload["Condition"] = condition
        payload["AlarmLevel"] = alarm_level
    if notice_ids:
        payload["AlarmNoticeIds"] = notice_ids
    optional_values = {
        "MultiConditions": multi_conditions,
        "GroupTriggerStatus": group_trigger_status,
        "GroupTriggerCondition": group_trigger_condition,
        "Analysis": analysis,
        "Classifications": classifications,
        "MessageTemplate": message_template,
        "CallBack": callback,
    }
    for key, value in optional_values.items():
        if value is not None:
            payload[key] = value
    return payload


def _monitor_time_payload(
    monitor_type: str, monitor_period: int, cron_expression: str | None
) -> dict[str, Any]:
    normalized = monitor_type[0].upper() + monitor_type[1:] if monitor_type else "Period"
    if normalized == "Cron":
        payload: dict[str, Any] = {"Type": "Cron"}
        if cron_expression:
            payload["CronExpression"] = cron_expression
        return payload
    return {"Type": normalized, "Time": max(1, min(monitor_period, 1440))}


def validate_policy_payload(payload: dict[str, Any]) -> list[PolicyIssue]:
    from cls_cli.core.alarm_policy_advanced import validate_advanced_policy_fields

    issues: list[PolicyIssue] = []
    targets = payload.get("AlarmTargets")
    if not isinstance(targets, list) or not targets:
        return [
            PolicyIssue(
                "missing_alarm_targets",
                "AlarmTargets must contain at least one query target",
                "AlarmTargets",
            )
        ]

    aliases_by_number: dict[int, set[str]] = {}
    for index, target in enumerate(targets):
        path = f"AlarmTargets[{index}]"
        if not isinstance(target, dict):
            issues.append(
                PolicyIssue("invalid_alarm_target", "Alarm target must be an object", path)
            )
            continue
        query = target.get("Query")
        if not isinstance(query, str) or not query.strip():
            issues.append(
                PolicyIssue("missing_query", "Alarm target Query is required", f"{path}.Query")
            )
            continue
        number = _target_number(target, index)
        aliases_by_number[number] = extract_query_aliases(query)
        issues.extend(_invalid_alias_issues(query, f"{path}.Query"))
        issues.extend(_field_reference_warnings(query, f"{path}.Query"))

    condition = payload.get("Condition")
    if isinstance(condition, str) and condition.strip():
        issues.extend(_condition_reference_issues(condition, "Condition", aliases_by_number))
    multi_conditions = payload.get("MultiConditions")
    if isinstance(multi_conditions, list):
        for index, item in enumerate(multi_conditions):
            if not isinstance(item, dict):
                continue
            item_condition = item.get("Condition")
            if isinstance(item_condition, str) and item_condition.strip():
                issues.extend(
                    _condition_reference_issues(
                        item_condition,
                        f"MultiConditions[{index}].Condition",
                        aliases_by_number,
                    )
                )
    issues.extend(validate_advanced_policy_fields(payload))
    return issues


def _condition_reference_issues(
    condition: str, path: str, aliases_by_number: dict[int, set[str]]
) -> list[PolicyIssue]:
    issues: list[PolicyIssue] = []
    for number, field in sorted(extract_condition_refs(condition)):
        aliases = aliases_by_number.get(number, set())
        if field == "__QUERYCOUNT__":
            continue
        if field not in aliases:
            issues.append(
                PolicyIssue(
                    "missing_condition_alias",
                    f"Condition references ${number}.{field} but query {number} "
                    "does not select it",
                    path,
                    f"select an alias named `{field}` in AlarmTargets[{number - 1}].Query",
                )
            )
    return issues


def extract_query_aliases(query: str) -> set[str]:
    aliases: set[str] = set()
    for item in _select_items(query):
        alias = _alias_from_select_item(item)
        if alias and is_strict_identifier(alias):
            aliases.add(alias)
            continue
        bare = _bare_identifier_from_select_item(item)
        if bare:
            aliases.add(bare)
    return aliases


def extract_condition_refs(condition: str) -> set[tuple[int, str]]:
    return {(int(number), field) for number, field in CONDITION_REF_RE.findall(condition)}


def is_strict_identifier(value: str) -> bool:
    return bool(STRICT_IDENTIFIER_RE.match(value))


def is_safe_field_name(value: str) -> bool:
    return bool(FIELD_NAME_RE.match(value))


def validate_generated_field_names(fields: list[str], *, path: str) -> None:
    for field in fields:
        if not is_safe_field_name(field):
            raise InputError(
                f"invalid_field_name: {path} contains unsafe field name `{field}`; "
                "use names matching ^[A-Za-z_][A-Za-z0-9_.$-]{0,127}$"
            )


def _target_number(target: dict[str, Any], index: int) -> int:
    raw = target.get("Number")
    if isinstance(raw, int) and raw > 0:
        return raw
    return index + 1


def _invalid_alias_issues(query: str, path: str) -> list[PolicyIssue]:
    issues: list[PolicyIssue] = []
    for item in _select_items(query):
        raw_alias = _raw_alias_from_select_item(item)
        if raw_alias is None:
            continue
        alias = _strip_identifier_quotes(raw_alias)
        if not is_strict_identifier(alias):
            issues.append(
                PolicyIssue(
                    "invalid_alias_identifier",
                    f"Generated SQL alias `{raw_alias}` should match ^[A-Za-z_][A-Za-z0-9_]*$",
                    path,
                    "Use an ASCII alias such as error_count or p95_latency",
                )
            )
    return issues


def _field_reference_warnings(query: str, path: str) -> list[PolicyIssue]:
    warnings: list[PolicyIssue] = []
    for item in _select_items(query):
        bare = _bare_identifier_from_select_item(item)
        if bare and _suspicious_cls_field_name(bare):
            warnings.append(
                PolicyIssue(
                    "suspicious_field_reference",
                    "CLS docs do not publish a complete field-name grammar; "
                    "this field may need quoting or query adjustment",
                    path,
                    None,
                    "warning",
                )
            )
    return warnings


def _suspicious_cls_field_name(value: str) -> bool:
    return any(char.isspace() or ord(char) < 32 for char in value)


def _select_items(query: str) -> list[str]:
    select_part = _select_clause(query)
    if not select_part:
        return []
    return [item.strip() for item in _split_csv_sql(select_part) if item.strip()]


def _select_clause(query: str) -> str:
    lowered = query.lower()
    index = lowered.find("select")
    if index < 0:
        return ""
    select_part = query[index + len("select") :]
    lowered_part = select_part.lower()
    stop_positions = []
    for token in (" group by ", " order by ", " limit "):
        pos = lowered_part.find(token)
        if pos >= 0:
            stop_positions.append(pos)
    if stop_positions:
        select_part = select_part[: min(stop_positions)]
    return select_part


def _split_csv_sql(value: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    quote = ""
    for index, char in enumerate(value):
        if quote:
            if char == quote:
                quote = ""
            continue
        if char in {'"', "'", "`"}:
            quote = char
            continue
        if char == "(":
            depth += 1
            continue
        if char == ")" and depth > 0:
            depth -= 1
            continue
        if char == "," and depth == 0:
            parts.append(value[start:index])
            start = index + 1
    parts.append(value[start:])
    return parts


def _raw_alias_from_select_item(item: str) -> str | None:
    match = AS_ALIAS_RE.search(item)
    if not match:
        return None
    return match.group(1).strip()


def _alias_from_select_item(item: str) -> str | None:
    raw = _raw_alias_from_select_item(item)
    return _strip_identifier_quotes(raw) if raw else None


def _strip_identifier_quotes(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] in {'"', "'", "`"} and stripped[-1] == stripped[0]:
        return stripped[1:-1]
    return stripped


def _bare_identifier_from_select_item(item: str) -> str | None:
    candidate = item.strip()
    if not candidate or "(" in candidate or _raw_alias_from_select_item(candidate) is not None:
        return None
    candidate = _strip_identifier_quotes(candidate)
    return candidate if is_strict_identifier(candidate) else None
