from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from cls_cli.core.alarm_notice_advanced import validate_advanced_notice_fields
from cls_cli.core.errors import InputError

CALLBACK_TYPE_ALIASES = {
    "wecom": "WeCom",
    "wechatwork": "WeCom",
    "wework": "WeCom",
    "dingtalk": "DingTalk",
    "dingding": "DingTalk",
    "feishu": "Lark",
    "lark": "Lark",
    "http": "Http",
    "webhook": "Http",
}
CALLBACK_TYPES = {"WeCom", "DingTalk", "Lark", "Http"}
METHODS = {"POST", "PUT"}
REDACTED = "***REDACTED***"
SENSITIVE_FIELDS = {"Webhook", "Key", "Secret", "SecretText", "Authorization"}


def normalize_callback_type(value: str) -> str:
    if value in CALLBACK_TYPES:
        return value
    normalized = value.replace("-", "").replace("_", "").lower()
    if normalized not in CALLBACK_TYPE_ALIASES:
        raise InputError(f"unsupported integration type: {value}")
    return CALLBACK_TYPE_ALIASES[normalized]


def build_integration_payload(
    *,
    name: str,
    integration_type: str,
    webhook_env: str | None = None,
    key_env: str | None = None,
    method: str | None = None,
    env_getter: Callable[[str], str | None],
) -> dict[str, Any]:
    callback_type = normalize_callback_type(integration_type)
    webhook = _required_env(webhook_env, "webhook", env_getter)
    key = _optional_env(key_env, env_getter)
    payload: dict[str, Any] = {"Name": name, "Type": callback_type, "Webhook": webhook}
    if method:
        payload["Method"] = method.upper()
    if key:
        payload["Key"] = key
    issues = validate_integration_payload(payload)
    if issues:
        raise InputError(str(issues[0]["message"] or "invalid integration payload"))
    return payload


def validate_integration_payload(payload: dict[str, Any]) -> list[dict[str, str | None]]:
    issues: list[dict[str, str | None]] = []
    name = payload.get("Name")
    if not isinstance(name, str) or not name.strip():
        issues.append(_issue("name_required", "Name is required", "Name"))
    elif len(name.encode("utf-8")) > 255:
        issues.append(_issue("name_too_long", "Name must be <= 255 bytes", "Name"))

    raw_type = payload.get("Type")
    callback_type = ""
    if not isinstance(raw_type, str) or not raw_type.strip():
        issues.append(_issue("type_required", "Type is required", "Type"))
    else:
        try:
            callback_type = normalize_callback_type(raw_type)
        except InputError:
            issues.append(
                _issue(
                    "type_invalid",
                    "Type must be one of WeCom, DingTalk, Lark, Http",
                    "Type",
                )
            )

    webhook = payload.get("Webhook")
    if not isinstance(webhook, str) or not webhook.strip():
        issues.append(_issue("webhook_required", "Webhook is required", "Webhook"))

    method = payload.get("Method")
    if callback_type == "Http" and not method:
        issues.append(_issue("method_required", "Method is required when Type is Http", "Method"))
    if method and str(method).upper() not in METHODS:
        issues.append(_issue("method_invalid", "Method must be POST or PUT", "Method"))
    return issues


def scaffold_notice_payload(
    *,
    name: str,
    callback_type: str,
    integration_id: str,
    notice_content_id: str,
    method: str | None = None,
    notice_type: str = "All",
) -> dict[str, Any]:
    callback = _notice_callback(
        callback_type=callback_type,
        integration_id=integration_id,
        notice_content_id=notice_content_id,
        method=method,
    )
    payload = {
        "Name": name,
        "Type": notice_type,
        "WebCallbacks": [callback],
        "AlarmShieldStatus": 1,
    }
    issues = validate_notice_payload(payload)
    if issues:
        raise InputError(str(issues[0]["message"] or "invalid notice payload"))
    return payload


def scaffold_advanced_notice_payload(
    *,
    name: str,
    callback_type: str,
    integration_id: str,
    notice_content_id: str,
    method: str | None = None,
    rule: str | None = None,
    rule_notify_types: list[int] | None = None,
    rule_levels: list[int] | None = None,
    rule_notify_time_between: str | None = None,
    rule_duration_gt: int | None = None,
    rule_alarm_name_regex: str | None = None,
    rule_label_in: list[str] | None = None,
    rule_label_regex: list[str] | None = None,
    receiver_ids: list[int] | None = None,
    receiver_channels: list[str] | None = None,
    receiver_type: str = "Uin",
    receiver_start_time: str = "00:00:00",
    receiver_end_time: str = "23:59:59",
    receiver_index: int = 1,
    receiver_notice_content_id: str = "",
    escalate: bool = False,
    escalate_interval: int | None = None,
    escalate_type: int | None = None,
    escalate_callback_type: str | None = None,
    escalate_integration_id: str | None = None,
    escalate_notice_content_id: str | None = None,
    escalate_method: str | None = None,
    callback_prioritize: bool = False,
) -> dict[str, Any]:
    notice_rule: dict[str, Any] = {
        "NoticeReceivers": _notice_receivers(
            receiver_ids=receiver_ids,
            receiver_channels=receiver_channels,
            receiver_type=receiver_type,
            start_time=receiver_start_time,
            end_time=receiver_end_time,
            index=receiver_index,
            notice_content_id=receiver_notice_content_id,
        ),
        "WebCallbacks": [
            _notice_callback(
                callback_type=callback_type,
                integration_id=integration_id,
                notice_content_id=notice_content_id,
                method=method,
            )
        ],
        "Escalate": escalate,
    }
    rule_expression = _notice_rule_expression(
        raw_rule=rule,
        notify_types=rule_notify_types,
        levels=rule_levels,
        notify_time_between=rule_notify_time_between,
        duration_gt=rule_duration_gt,
        alarm_name_regex=rule_alarm_name_regex,
        label_in=rule_label_in,
        label_regex=rule_label_regex,
    )
    if rule_expression is not None:
        notice_rule["Rule"] = rule_expression
    if escalate_interval is not None:
        notice_rule["Interval"] = escalate_interval
    if escalate_type is not None:
        notice_rule["Type"] = escalate_type
    if escalate_callback_type or escalate_integration_id or escalate_notice_content_id:
        if not (escalate_callback_type and escalate_integration_id and escalate_notice_content_id):
            raise InputError("escalation callback requires type, integration id, and content id")
        notice_rule["EscalateNotice"] = {
            "WebCallbacks": [
                _notice_callback(
                    callback_type=escalate_callback_type,
                    integration_id=escalate_integration_id,
                    notice_content_id=escalate_notice_content_id,
                    method=escalate_method,
                )
            ]
        }

    payload = {
        "Name": name,
        "Type": "",
        "NoticeReceivers": [],
        "WebCallbacks": [],
        "NoticeRules": [notice_rule],
        "AlarmShieldStatus": 2,
        "CallbackPrioritize": callback_prioritize,
    }
    issues = validate_notice_payload(payload)
    if issues:
        raise InputError(str(issues[0]["message"] or "invalid advanced notice payload"))
    return payload


def validate_notice_payload(payload: dict[str, Any]) -> list[dict[str, str | None]]:
    issues: list[dict[str, str | None]] = []
    if payload.get("NoticeRules") and (
        payload.get("Type") or payload.get("NoticeReceivers") or payload.get("WebCallbacks")
    ):
        issues.append(
            _issue(
                "notice_mode_conflict",
                "NoticeRules is mutually exclusive with Type/NoticeReceivers/WebCallbacks",
                "NoticeRules",
            )
        )
    notice_rules = payload.get("NoticeRules")
    if notice_rules is not None:
        return issues + validate_advanced_notice_fields(payload)

    if not any((payload.get("NoticeReceivers"), payload.get("WebCallbacks"))):
        issues.append(
            _issue(
                "notice_target_required",
                "Notice payload must configure NoticeReceivers, WebCallbacks, or NoticeRules",
                "WebCallbacks",
            )
        )

    callbacks = payload.get("WebCallbacks") or []
    if not isinstance(callbacks, list):
        return [_issue("callbacks_invalid", "WebCallbacks must be a list", "WebCallbacks")]
    for index, callback in enumerate(callbacks):
        if not isinstance(callback, dict):
            issues.append(
                _issue(
                    "callback_invalid",
                    "WebCallbacks item must be an object",
                    f"WebCallbacks[{index}]",
                )
            )
            continue
        path = f"WebCallbacks[{index}]"
        raw_type = callback.get("CallbackType")
        callback_type = ""
        if not isinstance(raw_type, str) or not raw_type.strip():
            issues.append(_issue("callback_type_required", "CallbackType is required", path))
        else:
            try:
                callback_type = normalize_callback_type(raw_type)
            except InputError:
                issues.append(
                    _issue(
                        "callback_type_invalid",
                        "CallbackType is invalid",
                        f"{path}.CallbackType",
                    )
                )
        if not callback.get("NoticeContentId"):
            issues.append(
                _issue(
                    "notice_content_required",
                    "NoticeContentId is required",
                    f"{path}.NoticeContentId",
                )
            )
        if callback.get("WebCallbackId"):
            if callback.get("Url") not in ("", None):
                issues.append(
                    _issue(
                        "url_must_be_empty_for_integration",
                        "Url must be empty when WebCallbackId references integration configuration",
                        f"{path}.Url",
                    )
                )
        elif not callback.get("Url"):
            issues.append(
                _issue(
                    "url_or_integration_required",
                    "Url or WebCallbackId is required",
                    path,
                )
            )
        method = callback.get("Method")
        if callback_type == "Http" and not method:
            issues.append(
                _issue("method_required", "Method is required for Http callbacks", f"{path}.Method")
            )
        if method and str(method).upper() not in METHODS:
            issues.append(_issue("method_invalid", "Method must be POST or PUT", f"{path}.Method"))
    return issues


def _notice_callback(
    *,
    callback_type: str,
    integration_id: str,
    notice_content_id: str,
    method: str | None = None,
) -> dict[str, Any]:
    callback: dict[str, Any] = {
        "CallbackType": normalize_callback_type(callback_type),
        "Url": "",
        "WebCallbackId": integration_id,
        "NoticeContentId": notice_content_id,
    }
    if method:
        callback["Method"] = method.upper()
    return callback


def _notice_receivers(
    *,
    receiver_ids: list[int] | None,
    receiver_channels: list[str] | None,
    receiver_type: str,
    start_time: str,
    end_time: str,
    index: int,
    notice_content_id: str,
) -> list[dict[str, Any]]:
    if not receiver_ids and not receiver_channels:
        return []
    if not receiver_ids or not receiver_channels:
        raise InputError("receiver ids and receiver channels must be provided together")
    return [
        {
            "ReceiverType": receiver_type,
            "ReceiverIds": receiver_ids,
            "ReceiverChannels": receiver_channels,
            "StartTime": start_time,
            "EndTime": end_time,
            "Index": index,
            "NoticeContentId": notice_content_id,
        }
    ]


def _notice_rule_expression(
    *,
    raw_rule: str | None,
    notify_types: list[int] | None,
    levels: list[int] | None,
    notify_time_between: str | None,
    duration_gt: int | None,
    alarm_name_regex: str | None,
    label_in: list[str] | None,
    label_regex: list[str] | None,
) -> str | None:
    generated_inputs = any(
        [
            notify_types,
            levels,
            notify_time_between,
            duration_gt is not None,
            alarm_name_regex,
            label_in,
            label_regex,
        ]
    )
    if raw_rule is not None and generated_inputs:
        raise InputError("--rule conflicts with rule builder options")
    if raw_rule is not None:
        return _normalize_rule_json_string(raw_rule)
    children: list[dict[str, Any]] = []
    if notify_types:
        children.append(
            _rule_condition(
                "NotifyType", [_rule_compare("In"), _rule_value(_json_compact(notify_types))]
            )
        )
    if levels:
        children.append(
            _rule_condition("Level", [_rule_compare("In"), _rule_value(_json_compact(levels))])
        )
    if notify_time_between:
        start, end = _split_range(notify_time_between, "rule-notify-time-between")
        children.append(
            _rule_condition(
                "NotifyTime", [_rule_compare("Between"), _rule_value(_json_compact([start, end]))]
            )
        )
    if duration_gt is not None:
        children.append(_rule_condition("Duration", [_rule_compare(">"), _rule_value(duration_gt)]))
    if alarm_name_regex:
        children.append(
            _rule_condition("AlarmName", [_rule_compare("=~"), _rule_value(alarm_name_regex)])
        )
    for item in label_in or []:
        key, value = _split_key_value(item, "rule-label-in")
        values = [part.strip() for part in value.split(",") if part.strip()]
        children.append(
            _rule_condition(
                "Label", [_rule_key(key), _rule_compare("In"), _rule_value(_json_compact(values))]
            )
        )
    for item in label_regex or []:
        key, value = _split_key_value(item, "rule-label-regex")
        children.append(
            _rule_condition("Label", [_rule_key(key), _rule_compare("=~"), _rule_value(value)])
        )
    if not children:
        return None
    return _json_compact({"Value": "AND", "Type": "Operation", "Children": children})


def _rule_condition(value: str, children: list[dict[str, Any]]) -> dict[str, Any]:
    return {"Type": "Condition", "Value": value, "Children": children}


def _rule_compare(value: str) -> dict[str, str]:
    return {"Value": value, "Type": "Compare"}


def _rule_value(value: Any) -> dict[str, Any]:
    return {"Value": value, "Type": "Value"}


def _rule_key(value: str) -> dict[str, str]:
    return {"Value": value, "Type": "Key"}


def _split_range(value: str, option_name: str) -> tuple[str, str]:
    if "-" not in value:
        raise InputError(f"--{option_name} must use start-end format")
    start, end = value.split("-", 1)
    start = start.strip()
    end = end.strip()
    if not start or not end:
        raise InputError(f"--{option_name} must use non-empty start-end")
    return start, end


def _split_key_value(value: str, option_name: str) -> tuple[str, str]:
    if "=" not in value:
        raise InputError(f"--{option_name} must use key=value format")
    key, item_value = value.split("=", 1)
    key = key.strip()
    item_value = item_value.strip()
    if not key or not item_value:
        raise InputError(f"--{option_name} must use non-empty key=value")
    return key, item_value


def _json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _normalize_rule_json_string(value: str) -> str:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise InputError("--rule must be a JSON object string") from exc
    return _json_compact(parsed)


def sanitize_sensitive(value: Any, key: str | None = None) -> Any:
    if key in SENSITIVE_FIELDS:
        return REDACTED
    if isinstance(value, dict):
        return {
            item_key: sanitize_sensitive(item_value, item_key)
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [sanitize_sensitive(item) for item in value]
    return value


def _required_env(env_name: str | None, label: str, env_getter: Callable[[str], str | None]) -> str:
    if not env_name:
        raise InputError(f"--{label}-env is required")
    value = _optional_env(env_name, env_getter)
    if not value:
        raise InputError(f"environment variable `{env_name}` is required")
    return value


def _optional_env(env_name: str | None, env_getter: Callable[[str], str | None]) -> str | None:
    if not env_name:
        return None
    return env_getter(env_name)


def _issue(
    code: str, message: str, path: str, suggestion: str | None = None
) -> dict[str, str | None]:
    return {"code": code, "message": message, "path": path, "suggestion": suggestion}
