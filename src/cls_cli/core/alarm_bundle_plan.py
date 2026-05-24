from __future__ import annotations

from typing import Any

RESOURCE_ORDER = ["topic", "integration", "notice_content", "notice", "policy"]
ALLOWED_MODES = {"existing", "create", "update", "skip"}

ID_KEYS = {
    "topic": ["logset_id", "topic_id"],
    "integration": ["web_callback_id"],
    "notice_content": ["notice_content_id"],
    "notice": ["alarm_notice_id"],
    "policy": ["alarm_id"],
}


def plan_alarm_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, str | None]] = []
    steps: list[dict[str, Any]] = []
    for resource in RESOURCE_ORDER:
        config = bundle.get(resource)
        if config is None:
            continue
        if not isinstance(config, dict):
            issues.append(
                _issue("bundle_resource_invalid", f"{resource} must be an object", resource)
            )
            continue
        mode = str(config.get("mode") or "skip")
        if mode not in ALLOWED_MODES:
            issues.append(
                _issue(
                    "bundle_mode_invalid",
                    f"{resource}.mode must be one of {sorted(ALLOWED_MODES)}",
                    f"{resource}.mode",
                )
            )
            continue
        step = {"resource": resource, "mode": mode, "action": _action_for(resource, mode)}
        missing = _missing_required_ids(resource, mode, config)
        if missing:
            issues.append(
                _issue(
                    "bundle_id_required",
                    f"{resource} {mode} requires {', '.join(missing)}",
                    resource,
                )
            )
        if mode in {"create", "update"} and not isinstance(config.get("payload"), dict):
            issues.append(
                _issue(
                    "bundle_payload_required",
                    f"{resource} {mode} requires payload object",
                    f"{resource}.payload",
                )
            )
        steps.append(step)
    return {
        "valid": not issues,
        "issues": issues,
        "steps": steps,
        "name": bundle.get("name"),
        "region": bundle.get("region"),
    }


def _action_for(resource: str, mode: str) -> str:
    if mode in {"existing", "skip"}:
        return "none"
    actions = {
        ("topic", "create"): "CreateTopic",
        ("topic", "update"): "ModifyTopic",
        ("notice_content", "create"): "CreateNoticeContent",
        ("notice_content", "update"): "ModifyNoticeContent",
        ("notice", "create"): "CreateAlarmNotice",
        ("notice", "update"): "ModifyAlarmNotice",
        ("policy", "create"): "CreateAlarm",
        ("policy", "update"): "ModifyAlarm",
        ("integration", "create"): "CreateWebCallback",
        ("integration", "update"): "ModifyWebCallback",
    }
    return actions.get((resource, mode), "none")


def _missing_required_ids(resource: str, mode: str, config: dict[str, Any]) -> list[str]:
    if mode == "existing":
        return [key for key in ID_KEYS.get(resource, []) if not config.get(key)]
    if mode == "update":
        return [key for key in ID_KEYS.get(resource, []) if not config.get(key)]
    return []


def _issue(code: str, message: str, path: str) -> dict[str, str | None]:
    return {"code": code, "message": message, "path": path, "suggestion": None, "severity": "error"}
