from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from cls_cli.core.alarm_policy import extract_query_aliases

KNOWN_VARIABLES = {
    "RecordId",
    "RecordGroupId",
    "UIN",
    "Nickname",
    "Region",
    "Alarm",
    "AlarmID",
    "Topic",
    "TopicId",
    "Logset",
    "LogsetId",
    "QueryParams",
    "Condition",
    "ConditionGroup",
    "Level",
    "Level_zh",
    "HappenThreshold",
    "AlertThreshold",
    "Label",
    "StartTime",
    "StartTimeUnix",
    "NotifyTime",
    "NotifyTimeUnix",
    "NotifyType",
    "ConsecutiveAlertNums",
    "Duration",
    "DetailUrl",
    "QueryUrl",
    "SilentUrl",
    "CanSilent",
    "Message",
    "TriggerParams",
    "QueryResult",
    "TriggerResult",
    "QueryLog",
    "AnalysisResult",
    "AnalysisResultFormat",
    "AnalysisResultFormat_zh",
}

VARIABLE_SUGGESTIONS = {"AlarmName": "Alarm"}
RESULT_FIELD_RE = re.compile(
    r"\.(?:QueryResult|TriggerResult)\[\d+]\[\d+]\.([A-Za-z_][A-Za-z0-9_]*)"
)
QUERY_LOG_FIELD_RE = re.compile(r"\.QueryLog\[\d+]\[\d+]\.([A-Za-z_][A-Za-z0-9_]*)")
VARIABLE_RE = re.compile(r"\.([A-Za-z_][A-Za-z0-9_]*)")
DIRECT_VARIABLE_TAG_RE = re.compile(r"{{-?\s*\.([A-Za-z_][A-Za-z0-9_]*)\s*-?}}")
SAFE_UNESCAPED_CHANNEL_VARIABLES = {
    "Level",
    "Level_zh",
    "UIN",
    "Region",
    "StartTime",
    "StartTimeUnix",
    "NotifyTime",
    "NotifyTimeUnix",
    "ConsecutiveAlertNums",
    "Duration",
    "HappenThreshold",
    "AlertThreshold",
    "CanSilent",
    "DetailUrl",
    "QueryUrl",
    "SilentUrl",
    "AnalysisResultFormat",
    "AnalysisResultFormat_zh",
}


@dataclass(frozen=True)
class TemplateIssue:
    code: str
    message: str
    path: str
    suggestion: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "suggestion": self.suggestion,
        }


def validate_notice_template(
    payload: dict[str, Any], policy_payload: dict[str, Any] | None = None
) -> list[TemplateIssue]:
    issues: list[TemplateIssue] = []
    text_parts = list(_template_strings(payload))
    aliases = _policy_aliases(policy_payload) if policy_payload is not None else set()
    for path, value in text_parts:
        query_log_fields = set(QUERY_LOG_FIELD_RE.findall(value))
        for variable in VARIABLE_RE.findall(value):
            if (
                variable not in KNOWN_VARIABLES
                and variable not in aliases
                and variable not in query_log_fields
            ):
                suggestion = VARIABLE_SUGGESTIONS.get(variable)
                issues.append(
                    TemplateIssue(
                        "unknown_variable",
                        f"unknown CLS alarm variable: {variable}",
                        path,
                        f"{{{{.{suggestion}}}}}" if suggestion else None,
                    )
                )
    issues.extend(_channel_escape_issues(payload))
    if policy_payload is not None:
        referenced = {
            field for _, value in text_parts for field in RESULT_FIELD_RE.findall(value)
        }
        for field in sorted(referenced - aliases):
            issues.append(
                TemplateIssue(
                    "missing_query_alias",
                    "template references QueryResult field "
                    f"`{field}` but policy query does not select it",
                    "policy.AlarmTargets[].Query",
                    f"add `{field}` to SELECT or use `as {field}`",
                )
            )
    return issues


def _channel_escape_issues(payload: dict[str, Any]) -> list[TemplateIssue]:
    issues: list[TemplateIssue] = []
    notice_contents = payload.get("NoticeContents")
    if not isinstance(notice_contents, list):
        return issues
    for index, item in enumerate(notice_contents):
        if not isinstance(item, dict):
            continue
        channel_type = str(item.get("Type") or "")
        required_escape = _required_escape_function(channel_type)
        if required_escape is None:
            continue
        for content_key in ("TriggerContent", "RecoveryContent"):
            content = item.get(content_key)
            if not isinstance(content, dict):
                continue
            value = content.get("Content")
            if not isinstance(value, str):
                continue
            path = f"NoticeContents[{index}].{content_key}.Content"
            for variable in DIRECT_VARIABLE_TAG_RE.findall(value):
                if variable in SAFE_UNESCAPED_CHANNEL_VARIABLES:
                    continue
                issues.append(
                    TemplateIssue(
                        "channel_escape_missing",
                        f"{channel_type} content should escape string variable `{variable}`",
                        path,
                        f"use {{{{{required_escape} .{variable}}}}}",
                    )
                )
    return issues


def _required_escape_function(channel_type: str) -> str | None:
    normalized = channel_type.lower()
    if normalized == "http":
        return "escape"
    if normalized in {"wecom", "dingtalk"}:
        return "escape_markdown"
    if normalized == "lark":
        return "escape_markdown_html"
    return None


def _template_strings(payload: dict[str, Any]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, str):
            result.append((path, value))
            return
        if isinstance(value, dict):
            for key, item in value.items():
                visit(item, f"{path}.{key}" if path else key)
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")

    visit(payload, "")
    return result


def _policy_aliases(policy_payload: dict[str, Any]) -> set[str]:
    aliases: set[str] = set()
    targets = policy_payload.get("AlarmTargets")
    if not isinstance(targets, list):
        return aliases
    for target in targets:
        if not isinstance(target, dict):
            continue
        query = target.get("Query")
        if not isinstance(query, str):
            continue
        aliases.update(extract_query_aliases(query))
    return aliases
