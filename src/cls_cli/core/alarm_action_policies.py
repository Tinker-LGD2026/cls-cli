from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from cls_cli.core.alarm_integrations import (
    sanitize_sensitive,
    validate_integration_payload,
    validate_notice_payload,
)
from cls_cli.core.alarm_policy import validate_policy_payload
from cls_cli.core.errors import InputError

Validator = Callable[[dict[str, Any]], list[dict[str, Any]]]


def _policy_validator(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        issue.to_dict()
        for issue in validate_policy_payload(payload)
        if issue.severity == "error"
    ]


def _notice_validator(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(issue) for issue in validate_notice_payload(payload)]


def _integration_validator(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(issue) for issue in validate_integration_payload(payload)]


VALIDATORS: dict[str, Validator] = {
    "alarm.policy.create": _policy_validator,
    "alarm.policy.update": _policy_validator,
    "alarm.notice.create": _notice_validator,
    "alarm.notice.update": _notice_validator,
    "alarm.integration.create": _integration_validator,
    "alarm.integration.update": _integration_validator,
    "alarm.callback.create": _integration_validator,
    "alarm.callback.update": _integration_validator,
}

SENSITIVE_ACTION_PREFIXES = (
    "alarm.callback.",
    "alarm.integration.",
)


def validate_action_payload(
    spec_key: str, payload: dict[str, Any], *, skip_validation: bool
) -> None:
    if skip_validation:
        return
    validator = VALIDATORS.get(spec_key)
    if validator is None:
        return
    issues = validator(payload)
    if not issues:
        return
    codes = ", ".join(str(issue.get("code")) for issue in issues if issue.get("code"))
    raise InputError(
        "payload validation failed: "
        f"{codes}; issues={json.dumps(issues, ensure_ascii=False)}"
    )


def sanitize_action_payload(spec_key: str, value: Any) -> Any:
    if spec_key.startswith(SENSITIVE_ACTION_PREFIXES):
        return sanitize_sensitive(value)
    return value
