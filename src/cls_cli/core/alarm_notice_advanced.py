from __future__ import annotations

import json
from typing import Any

Issue = dict[str, str | None]


def validate_advanced_notice_fields(payload: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    callback_prioritize = payload.get("CallbackPrioritize")
    if callback_prioritize is not None and not isinstance(callback_prioritize, bool):
        issues.append(
            _issue(
                "callback_prioritize_invalid",
                "CallbackPrioritize must be a boolean",
                "CallbackPrioritize",
            )
        )

    notice_rules = payload.get("NoticeRules")
    if notice_rules is None:
        return issues
    if not isinstance(notice_rules, list):
        return issues + [
            _issue("notice_rules_invalid", "NoticeRules must be a list", "NoticeRules")
        ]
    for index, rule in enumerate(notice_rules):
        path = f"NoticeRules[{index}]"
        if not isinstance(rule, dict):
            issues.append(_issue("notice_rule_invalid", "NoticeRules item must be an object", path))
            continue
        issues.extend(_validate_rule(rule, path))
        issues.extend(_validate_time_windows(rule, path))
    return issues


def _validate_rule(rule: dict[str, Any], path: str) -> list[Issue]:
    issues: list[Issue] = []
    rule_expr = rule.get("Rule")
    if rule_expr is not None and (not isinstance(rule_expr, str) or not _is_json_string(rule_expr)):
        issues.append(
            _issue(
                "notice_rule_expr_invalid",
                "NoticeRules[].Rule must be a JSON string",
                f"{path}.Rule",
            )
        )

    receivers = rule.get("NoticeReceivers")
    callbacks = rule.get("WebCallbacks")
    escalate_notice = rule.get("EscalateNotice")
    if not any((receivers, callbacks, escalate_notice)):
        issues.append(
            _issue(
                "notice_rule_target_required",
                "NoticeRules item must configure at least one notification target",
                path,
            )
        )

    issues.extend(_validate_receivers(receivers, f"{path}.NoticeReceivers", "notice"))
    issues.extend(_validate_webcallbacks(callbacks, f"{path}.WebCallbacks", "notice"))

    escalate = rule.get("Escalate")
    if escalate is not None and not isinstance(escalate, bool):
        issues.append(
            _issue(
                "notice_escalate_invalid",
                "NoticeRules[].Escalate must be a boolean",
                f"{path}.Escalate",
            )
        )
    interval = rule.get("Interval")
    if interval is not None and not _is_int(interval):
        issues.append(
            _issue(
                "notice_interval_invalid",
                "NoticeRules[].Interval must be an integer",
                f"{path}.Interval",
            )
        )
    escalate_type = rule.get("Type")
    if escalate_type is not None and not _is_int(escalate_type):
        issues.append(
            _issue(
                "notice_type_invalid",
                "NoticeRules[].Type must be an integer",
                f"{path}.Type",
            )
        )
    issues.extend(_validate_escalate_notice(escalate_notice, f"{path}.EscalateNotice"))
    return issues


def _validate_escalate_notice(value: Any, path: str) -> list[Issue]:
    if value is None:
        return []
    if not isinstance(value, dict):
        return [_issue("escalate_notice_invalid", "EscalateNotice must be an object", path)]
    issues: list[Issue] = []
    issues.extend(
        _validate_receivers(
            value.get("NoticeReceivers"), f"{path}.NoticeReceivers", "escalate_notice"
        )
    )
    issues.extend(
        _validate_webcallbacks(
            value.get("WebCallbacks"), f"{path}.WebCallbacks", "escalate_notice"
        )
    )
    escalate = value.get("Escalate")
    if escalate is not None and not isinstance(escalate, bool):
        issues.append(
            _issue(
                "escalate_notice_escalate_invalid",
                "EscalateNotice.Escalate must be a boolean",
                f"{path}.Escalate",
            )
        )
    interval = value.get("Interval")
    if interval is not None and not _is_int(interval):
        issues.append(
            _issue(
                "escalate_notice_interval_invalid",
                "EscalateNotice.Interval must be an integer",
                f"{path}.Interval",
            )
        )
    escalate_type = value.get("Type")
    if escalate_type is not None and not _is_int(escalate_type):
        issues.append(
            _issue(
                "escalate_notice_type_invalid",
                "EscalateNotice.Type must be an integer",
                f"{path}.Type",
            )
        )
    nested = value.get("EscalateNotice")
    if nested is not None:
        issues.extend(_validate_escalate_notice(nested, f"{path}.EscalateNotice"))
    return issues


def _validate_receivers(value: Any, path: str, prefix: str) -> list[Issue]:
    if value is None:
        return []
    if not isinstance(value, list):
        return [_issue(f"{prefix}_receivers_invalid", "NoticeReceivers must be a list", path)]
    issues: list[Issue] = []
    for index, receiver in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(receiver, dict):
            issues.append(
                _issue(
                    f"{prefix}_receiver_item_invalid",
                    "NoticeReceivers item must be an object",
                    item_path,
                )
            )
            continue
        receiver_type = receiver.get("ReceiverType")
        if receiver_type is not None and not isinstance(receiver_type, str):
            issues.append(
                _issue(
                    f"{prefix}_receiver_type_invalid",
                    "ReceiverType must be a string",
                    f"{item_path}.ReceiverType",
                )
            )
        receiver_ids = receiver.get("ReceiverIds")
        if receiver_ids is not None and not isinstance(receiver_ids, list):
            issues.append(
                _issue(
                    f"{prefix}_receiver_ids_invalid",
                    "ReceiverIds must be a list",
                    f"{item_path}.ReceiverIds",
                )
            )
        channels = receiver.get("ReceiverChannels")
        if channels is not None and not isinstance(channels, list):
            issues.append(
                _issue(
                    f"{prefix}_receiver_channels_invalid",
                    "ReceiverChannels must be a list",
                    f"{item_path}.ReceiverChannels",
                )
            )
        start_time = receiver.get("StartTime")
        if start_time is not None and not isinstance(start_time, str):
            issues.append(
                _issue(
                    f"{prefix}_receiver_start_time_invalid",
                    "StartTime must be a string",
                    f"{item_path}.StartTime",
                )
            )
        end_time = receiver.get("EndTime")
        if end_time is not None and not isinstance(end_time, str):
            issues.append(
                _issue(
                    f"{prefix}_receiver_end_time_invalid",
                    "EndTime must be a string",
                    f"{item_path}.EndTime",
                )
            )
        receiver_index = receiver.get("Index")
        if receiver_index is not None and not _is_int(receiver_index):
            issues.append(
                _issue(
                    f"{prefix}_receiver_index_invalid",
                    "Index must be an integer",
                    f"{item_path}.Index",
                )
            )
        content_id = receiver.get("NoticeContentId")
        if content_id is not None and not isinstance(content_id, str):
            issues.append(
                _issue(
                    f"{prefix}_receiver_content_id_invalid",
                    "NoticeContentId must be a string",
                    f"{item_path}.NoticeContentId",
                )
            )
    return issues


def _validate_webcallbacks(value: Any, path: str, prefix: str) -> list[Issue]:
    if value is None:
        return []
    if not isinstance(value, list):
        return [_issue(f"{prefix}_webcallbacks_invalid", "WebCallbacks must be a list", path)]
    issues: list[Issue] = []
    for index, callback in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(callback, dict):
            issues.append(
                _issue(
                    f"{prefix}_webcallback_item_invalid",
                    "WebCallbacks item must be an object",
                    item_path,
                )
            )
            continue
        for key in ("CallbackType", "WebCallbackId", "NoticeContentId", "Url", "Method"):
            field_value = callback.get(key)
            if field_value is not None and not isinstance(field_value, str):
                issues.append(
                    _issue(
                        f"{prefix}_webcallback_{key.lower()}_invalid",
                        f"{key} must be a string",
                        f"{item_path}.{key}",
                    )
                )
    return issues


def _validate_time_windows(rule: dict[str, Any], path: str) -> list[Issue]:
    issues: list[Issue] = []
    for key, value in rule.items():
        normalized = key.lower()
        if "time" not in normalized and "period" not in normalized:
            continue
        if value is None:
            continue
        if not isinstance(value, str | list | dict):
            issues.append(
                _issue(
                    "notice_time_window_invalid",
                    f"{key} must be string, array, or object",
                    f"{path}.{key}",
                )
            )
    return issues


def _is_json_string(value: str) -> bool:
    if not value.strip():
        return False
    try:
        json.loads(value)
    except json.JSONDecodeError:
        return False
    return True


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _issue(code: str, message: str, path: str) -> Issue:
    return {"code": code, "message": message, "path": path, "suggestion": None}
