from __future__ import annotations

import json
import re
from typing import Any

from cls_cli.core.alarm_policy import PolicyIssue

CLASSIFICATION_KEY_RE = re.compile(r"^[a-z]([a-z0-9_]{0,49})$")
ANALYSIS_TYPES = {"query", "field", "original"}
MONITOR_TYPES = {"Period", "Fixed", "Cron"}


def validate_advanced_policy_fields(payload: dict[str, Any]) -> list[PolicyIssue]:
    issues: list[PolicyIssue] = []
    issues.extend(_expect_list(payload, "MultiConditions", "multi_conditions_invalid"))
    issues.extend(_expect_bool(payload, "GroupTriggerStatus", "group_trigger_status_invalid"))
    issues.extend(_expect_list(payload, "GroupTriggerCondition", "group_trigger_condition_invalid"))
    issues.extend(_expect_list(payload, "Analysis", "analysis_invalid"))
    issues.extend(_expect_list(payload, "Classifications", "classifications_invalid"))
    issues.extend(_expect_str(payload, "MessageTemplate", "message_template_invalid"))
    issues.extend(_expect_dict(payload, "CallBack", "callback_invalid"))
    issues.extend(_validate_monitor_time(payload))
    issues.extend(_validate_multi_conditions(payload))
    issues.extend(_validate_analysis(payload))
    issues.extend(_validate_classifications(payload))
    issues.extend(_validate_callback(payload))
    return issues


def _expect_list(payload: dict[str, Any], field: str, code: str) -> list[PolicyIssue]:
    if field in payload and not isinstance(payload[field], list):
        return [PolicyIssue(code, f"{field} must be a JSON array", field)]
    return []


def _expect_bool(payload: dict[str, Any], field: str, code: str) -> list[PolicyIssue]:
    if field in payload and not isinstance(payload[field], bool):
        return [PolicyIssue(code, f"{field} must be a boolean", field)]
    return []


def _expect_dict(payload: dict[str, Any], field: str, code: str) -> list[PolicyIssue]:
    if field in payload and not isinstance(payload[field], dict):
        return [PolicyIssue(code, f"{field} must be a JSON object", field)]
    return []


def _expect_str(payload: dict[str, Any], field: str, code: str) -> list[PolicyIssue]:
    if field in payload and not isinstance(payload[field], str):
        return [PolicyIssue(code, f"{field} must be a string", field)]
    return []


def _validate_list_items(payload: dict[str, Any], field: str, code: str) -> list[PolicyIssue]:
    value = payload.get(field)
    if not isinstance(value, list):
        return []
    issues: list[PolicyIssue] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            issues.append(
                PolicyIssue(code, f"{field} item must be a JSON object", f"{field}[{index}]")
            )
    return issues


def _validate_monitor_time(payload: dict[str, Any]) -> list[PolicyIssue]:
    value = payload.get("MonitorTime")
    if value is None:
        return []
    if not isinstance(value, dict):
        return [
            PolicyIssue(
                "monitor_time_invalid",
                "MonitorTime must be a JSON object",
                "MonitorTime",
            )
        ]
    issues: list[PolicyIssue] = []
    monitor_type = value.get("Type")
    if monitor_type is not None and not isinstance(monitor_type, str):
        issues.append(
            PolicyIssue(
                "monitor_time_type_invalid",
                "MonitorTime.Type must be a string",
                "MonitorTime.Type",
            )
        )
    elif monitor_type is not None and monitor_type not in MONITOR_TYPES:
        issues.append(
            PolicyIssue(
                "monitor_time_type_value_invalid",
                "MonitorTime.Type must be Period, Fixed, or Cron",
                "MonitorTime.Type",
            )
        )
    monitor_time = value.get("Time")
    if monitor_time is not None and not _is_int(monitor_time):
        issues.append(
            PolicyIssue(
                "monitor_time_time_invalid",
                "MonitorTime.Time must be an integer",
                "MonitorTime.Time",
            )
        )
    cron_expression = value.get("CronExpression")
    if cron_expression is not None and not isinstance(cron_expression, str):
        issues.append(
            PolicyIssue(
                "monitor_time_cron_expression_invalid",
                "MonitorTime.CronExpression must be a string",
                "MonitorTime.CronExpression",
            )
        )
    return issues


def _validate_analysis(payload: dict[str, Any]) -> list[PolicyIssue]:
    value = payload.get("Analysis")
    if not isinstance(value, list):
        return []
    issues: list[PolicyIssue] = []
    for index, item in enumerate(value):
        path = f"Analysis[{index}]"
        if not isinstance(item, dict):
            issues.append(
                PolicyIssue("analysis_item_invalid", "Analysis item must be a JSON object", path)
            )
            continue
        name = item.get("Name")
        if name is not None and not isinstance(name, str):
            issues.append(
                PolicyIssue(
                    "analysis_name_invalid", "Analysis.Name must be a string", f"{path}.Name"
                )
            )
        analysis_type = item.get("Type")
        if analysis_type is not None and (
            not isinstance(analysis_type, str) or analysis_type not in ANALYSIS_TYPES
        ):
            issues.append(
                PolicyIssue(
                    "analysis_type_invalid",
                    "Analysis.Type must be query, field, or original",
                    f"{path}.Type",
                )
            )
        content = item.get("Content")
        if content is not None and not isinstance(content, str):
            issues.append(
                PolicyIssue(
                    "analysis_content_invalid",
                    "Analysis.Content must be a string",
                    f"{path}.Content",
                )
            )
        config_info = item.get("ConfigInfo")
        if config_info is not None:
            if not isinstance(config_info, list):
                issues.append(
                    PolicyIssue(
                        "analysis_config_invalid",
                        "Analysis.ConfigInfo must be a list",
                        f"{path}.ConfigInfo",
                    )
                )
            else:
                issues.extend(_validate_analysis_config(config_info, f"{path}.ConfigInfo"))
    return issues


def _validate_analysis_config(value: list[Any], path: str) -> list[PolicyIssue]:
    issues: list[PolicyIssue] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(item, dict):
            issues.append(
                PolicyIssue(
                    "analysis_config_item_invalid",
                    "Analysis.ConfigInfo item must be a JSON object",
                    item_path,
                )
            )
            continue
        key = item.get("Key")
        if key is not None and not isinstance(key, str):
            issues.append(
                PolicyIssue(
                    "analysis_config_key_invalid",
                    "Analysis.ConfigInfo.Key must be a string",
                    f"{item_path}.Key",
                )
            )
        config_value = item.get("Value")
        if config_value is not None and not isinstance(config_value, str):
            issues.append(
                PolicyIssue(
                    "analysis_config_value_invalid",
                    "Analysis.ConfigInfo.Value must be a string",
                    f"{item_path}.Value",
                )
            )
    return issues


def _validate_classifications(payload: dict[str, Any]) -> list[PolicyIssue]:
    value = payload.get("Classifications")
    if not isinstance(value, list):
        return []
    issues: list[PolicyIssue] = []
    seen: set[str] = set()
    if len(value) > 20:
        issues.append(
            PolicyIssue(
                "classifications_too_many",
                "Classifications supports at most 20 items",
                "Classifications",
            )
        )
    for index, item in enumerate(value):
        path = f"Classifications[{index}]"
        if not isinstance(item, dict):
            issues.append(
                PolicyIssue(
                    "classification_item_invalid",
                    "Classifications item must be a JSON object",
                    path,
                )
            )
            continue
        key = item.get("Key")
        if not isinstance(key, str) or not CLASSIFICATION_KEY_RE.match(key):
            issues.append(
                PolicyIssue(
                    "classification_key_invalid",
                    "Classifications.Key must match ^[a-z]([a-z0-9_]{0,49})$",
                    f"{path}.Key",
                )
            )
        elif key in seen:
            issues.append(
                PolicyIssue(
                    "classification_key_duplicate",
                    "Classifications.Key must be unique",
                    f"{path}.Key",
                )
            )
        else:
            seen.add(key)
        classification_value = item.get("Value")
        if not isinstance(classification_value, str) or len(classification_value) > 200:
            issues.append(
                PolicyIssue(
                    "classification_value_invalid",
                    "Classifications.Value must be a string with length <= 200",
                    f"{path}.Value",
                )
            )
    return issues


def _validate_callback(payload: dict[str, Any]) -> list[PolicyIssue]:
    callback = payload.get("CallBack")
    if not isinstance(callback, dict):
        return []
    issues: list[PolicyIssue] = []
    headers = callback.get("Headers")
    if headers is not None and not isinstance(headers, list):
        issues.append(
            PolicyIssue(
                "callback_headers_invalid",
                "CallBack.Headers must be a JSON array",
                "CallBack.Headers",
            )
        )
    body = callback.get("Body")
    if body is not None and not isinstance(body, str):
        issues.append(
            PolicyIssue(
                "callback_body_invalid",
                "CallBack.Body must be a string",
                "CallBack.Body",
            )
        )
    return issues


def _validate_multi_conditions(payload: dict[str, Any]) -> list[PolicyIssue]:
    value = payload.get("MultiConditions")
    if not isinstance(value, list):
        return []
    issues: list[PolicyIssue] = []
    for index, item in enumerate(value):
        path = f"MultiConditions[{index}]"
        if not isinstance(item, dict):
            issues.append(
                PolicyIssue(
                    "multi_condition_item_invalid",
                    "MultiConditions item must be a JSON object",
                    path,
                )
            )
            continue
        condition = item.get("Condition")
        if condition is not None and not isinstance(condition, str):
            issues.append(
                PolicyIssue(
                    "multi_condition_condition_invalid",
                    "MultiConditions[].Condition must be a string",
                    f"{path}.Condition",
                )
            )
        config = item.get("ConditionInteractiveConfig")
        if config is not None and (not isinstance(config, str) or not _is_json_string(config)):
            issues.append(
                PolicyIssue(
                    "multi_condition_config_invalid",
                    "MultiConditions[].ConditionInteractiveConfig must be a JSON string",
                    f"{path}.ConditionInteractiveConfig",
                )
            )
        alarm_level = item.get("AlarmLevel")
        if alarm_level is not None and not _is_int(alarm_level):
            issues.append(
                PolicyIssue(
                    "multi_condition_alarm_level_invalid",
                    "MultiConditions[].AlarmLevel must be an integer",
                    f"{path}.AlarmLevel",
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
