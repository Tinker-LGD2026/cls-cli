from __future__ import annotations

from typing import Any

from cls_cli.core.alarm_integrations import validate_integration_payload, validate_notice_payload
from cls_cli.core.alarm_policy import validate_policy_payload
from cls_cli.core.alarm_templates import validate_notice_template


def validate_alarm_bundle(
    *,
    policy: dict[str, Any] | None,
    notice_content: dict[str, Any] | None,
    notice: dict[str, Any] | None,
    integration: dict[str, Any] | None,
) -> dict[str, Any]:
    issues: list[dict[str, str | None]] = []
    summary = {
        "policy": policy is not None,
        "notice_content": notice_content is not None,
        "notice": notice is not None,
        "integration": integration is not None,
    }

    if policy is not None:
        issues.extend(
            _prefix_issues(
                "policy", (issue.to_dict() for issue in validate_policy_payload(policy))
            )
        )
    if notice_content is not None:
        issues.extend(
            _prefix_issues(
                "notice_content",
                (issue.to_dict() for issue in validate_notice_template(notice_content, policy)),
            )
        )
    if notice is not None:
        issues.extend(_prefix_issues("notice", validate_notice_payload(notice)))
    if integration is not None:
        issues.extend(_prefix_issues("integration", validate_integration_payload(integration)))

    issues.extend(_cross_resource_issues(policy, notice_content, notice, integration))
    blocking = [issue for issue in issues if issue.get("severity", "error") == "error"]
    return {"valid": not blocking, "issues": issues, "summary": summary}


def _cross_resource_issues(
    policy: dict[str, Any] | None,
    notice_content: dict[str, Any] | None,
    notice: dict[str, Any] | None,
    integration: dict[str, Any] | None,
) -> list[dict[str, str | None]]:
    issues: list[dict[str, str | None]] = []
    if policy is not None and not policy.get("AlarmNoticeIds"):
        issues.append(
            _issue(
                "policy_notice_missing",
                "Policy should bind at least one AlarmNoticeId",
                "policy.AlarmNoticeIds",
            )
        )
    if policy is not None and notice is not None:
        notice_id = _text(notice.get("AlarmNoticeId"))
        bound_ids = policy.get("AlarmNoticeIds")
        bound_id_texts = [str(item) for item in bound_ids] if isinstance(bound_ids, list) else []
        if notice_id and bound_id_texts and notice_id not in bound_id_texts:
            issues.append(
                _issue(
                    "policy_notice_mismatch",
                    "Policy AlarmNoticeIds does not include notice AlarmNoticeId",
                    "policy.AlarmNoticeIds",
                )
            )
    if notice is not None and notice_content is not None:
        content_id = _text(notice_content.get("NoticeContentId"))
        notice_content_ids = _notice_content_ids(notice)
        if content_id and notice_content_ids and content_id not in notice_content_ids:
            issues.append(
                _issue(
                    "notice_content_mismatch",
                    "Notice WebCallbacks do not reference the provided NoticeContentId",
                    "notice.WebCallbacks[].NoticeContentId",
                )
            )
    if notice is not None and integration is not None:
        integration_id = _text(integration.get("WebCallbackId"))
        callback_ids = _notice_callback_ids(notice)
        if integration_id and callback_ids and integration_id not in callback_ids:
            issues.append(
                _issue(
                    "integration_mismatch",
                    "Notice WebCallbacks do not reference the provided WebCallbackId",
                    "notice.WebCallbacks[].WebCallbackId",
                )
            )
    return issues


def _prefix_issues(
    prefix: str, issues: Any
) -> list[dict[str, str | None]]:
    result: list[dict[str, str | None]] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        path = str(issue.get("path") or "")
        item = dict(issue)
        item["path"] = f"{prefix}.{path}" if path else prefix
        item.setdefault("severity", "error")
        result.append(item)
    return result


def _notice_content_ids(notice: dict[str, Any]) -> set[str]:
    return {
        str(callback.get("NoticeContentId"))
        for callback in _notice_callbacks(notice)
        if callback.get("NoticeContentId")
    }


def _notice_callback_ids(notice: dict[str, Any]) -> set[str]:
    return {
        str(callback.get("WebCallbackId"))
        for callback in _notice_callbacks(notice)
        if callback.get("WebCallbackId")
    }


def _notice_callbacks(notice: dict[str, Any]) -> list[dict[str, Any]]:
    callbacks: list[dict[str, Any]] = []
    callbacks.extend(_callback_items(notice.get("WebCallbacks")))
    rules = notice.get("NoticeRules")
    if isinstance(rules, list):
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            callbacks.extend(_callback_items(rule.get("WebCallbacks")))
            callbacks.extend(_escalate_notice_callbacks(rule.get("EscalateNotice")))
    return callbacks


def _escalate_notice_callbacks(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    callbacks = _callback_items(value.get("WebCallbacks"))
    callbacks.extend(_escalate_notice_callbacks(value.get("EscalateNotice")))
    return callbacks


def _callback_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _text(value: Any) -> str:
    return str(value) if value else ""


def _issue(code: str, message: str, path: str) -> dict[str, str | None]:
    return {"code": code, "message": message, "path": path, "suggestion": None, "severity": "error"}
