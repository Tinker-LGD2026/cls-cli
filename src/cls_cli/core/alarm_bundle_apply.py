from __future__ import annotations

import copy
import json
import re
from typing import Any

from cls_cli.core.alarm_action_policies import validate_action_payload
from cls_cli.core.alarm_bundle_plan import plan_alarm_bundle
from cls_cli.core.errors import ConfirmationRequired, InputError

BUNDLE_TOKEN_RE = re.compile(r"\$\{([a-z_]+)\.([a-z_]+)\}")
EXACT_CONFIRMATION_TEXT = "同意执行"

WRITE_ACTIONS = {
    ("topic", "create"): ("topic.create", "CreateTopic", "TopicId", "topic_id"),
    ("topic", "update"): ("topic.update", "ModifyTopic", "TopicId", "topic_id"),
    ("integration", "create"): (
        "alarm.integration.create",
        "CreateWebCallback",
        "WebCallbackId",
        "web_callback_id",
    ),
    ("integration", "update"): (
        "alarm.integration.update",
        "ModifyWebCallback",
        "WebCallbackId",
        "web_callback_id",
    ),
    ("notice_content", "create"): (
        "alarm.content.create",
        "CreateNoticeContent",
        "NoticeContentId",
        "notice_content_id",
    ),
    ("notice_content", "update"): (
        "alarm.content.update",
        "ModifyNoticeContent",
        "NoticeContentId",
        "notice_content_id",
    ),
    ("notice", "create"): (
        "alarm.notice.create",
        "CreateAlarmNotice",
        "AlarmNoticeId",
        "alarm_notice_id",
    ),
    ("notice", "update"): (
        "alarm.notice.update",
        "ModifyAlarmNotice",
        "AlarmNoticeId",
        "alarm_notice_id",
    ),
    ("policy", "create"): ("alarm.policy.create", "CreateAlarm", "AlarmId", "alarm_id"),
    ("policy", "update"): ("alarm.policy.update", "ModifyAlarm", "AlarmId", "alarm_id"),
}

DELETE_ACTIONS = {
    "policy": ("DeleteAlarm", "AlarmId", "alarm_id"),
    "notice": ("DeleteAlarmNotice", "AlarmNoticeId", "alarm_notice_id"),
    "notice_content": ("DeleteNoticeContent", "NoticeContentId", "notice_content_id"),
    "integration": ("DeleteWebCallback", "WebCallbackId", "web_callback_id"),
    "topic": ("DeleteTopic", "TopicId", "topic_id"),
}


def apply_alarm_bundle(
    client: Any,
    bundle: dict[str, Any],
    region: str,
    *,
    confirm_real_write: bool,
    confirmation_text: str | None = None,
) -> dict[str, Any]:
    if not confirm_real_write:
        raise ConfirmationRequired(
            "pass --confirm-real-write to create or update alarm bundle resources"
        )
    if confirmation_text != EXACT_CONFIRMATION_TEXT:
        raise ConfirmationRequired(
            "exact confirmation text is required: 同意执行"
        )
    plan = plan_alarm_bundle(bundle)
    if not plan["valid"]:
        raise InputError(json.dumps(plan["issues"], ensure_ascii=False))
    context = _initial_context(bundle)
    _preflight_tokens(bundle, plan, context)
    manifest = {"name": bundle.get("name"), "region": region, "resources": copy.deepcopy(context)}
    completed: list[str] = []
    try:
        for step in plan["steps"]:
            resource = step["resource"]
            mode = step["mode"]
            if mode in {"existing", "skip"}:
                continue
            spec_key, action, response_id_key, context_id_key = WRITE_ACTIONS[(resource, mode)]
            payload = _resolve_tokens(bundle[resource]["payload"], context)
            if mode == "update":
                resource_id = str(bundle[resource].get(context_id_key) or "")
                if not resource_id:
                    raise InputError(f"{resource} update requires {context_id_key}")
                payload[response_id_key] = resource_id
            validate_action_payload(spec_key, payload, skip_validation=False)
            response = client.invoke(action, payload, region)
            if mode == "create":
                resource_id = str(response.get("Response", {}).get(response_id_key) or "")
                if not resource_id:
                    raise InputError(f"{action} response missing {response_id_key}")
            context.setdefault(resource, {})["mode"] = mode
            _merge_resource_context(context[resource], resource, payload)
            context[resource][context_id_key] = resource_id
            manifest["resources"] = copy.deepcopy(context)
            if mode == "create":
                completed.append(resource)
        return {"status": "PASS", "plan": plan, "manifest": manifest, "rollback": []}
    except Exception as exc:
        rollback = rollback_alarm_bundle(
            client,
            manifest,
            region,
            force=True,
            only_resources=completed,
            require_confirmation=False,
        )
        return {
            "status": "FAIL",
            "plan": plan,
            "manifest": manifest,
            "rollback": rollback["rollback"],
            "error": str(exc),
        }


def rollback_alarm_bundle(
    client: Any,
    manifest: dict[str, Any],
    region: str,
    *,
    force: bool,
    only_resources: list[str] | None = None,
    confirmation_text: str | None = None,
    require_confirmation: bool = True,
) -> dict[str, Any]:
    if not force:
        raise ConfirmationRequired("rollback deletes created resources; pass --force")
    if require_confirmation and confirmation_text != EXACT_CONFIRMATION_TEXT:
        raise ConfirmationRequired(
            "exact confirmation text is required for rollback: 同意执行"
        )
    resources = manifest.get("resources")
    if not isinstance(resources, dict):
        raise InputError("manifest.resources must be an object")
    allowed = set(only_resources) if only_resources is not None else None
    results: list[dict[str, Any]] = []
    for resource in ["policy", "notice", "notice_content", "integration", "topic"]:
        if allowed is not None and resource not in allowed:
            continue
        info = resources.get(resource)
        if not isinstance(info, dict) or info.get("mode") != "create":
            continue
        action, request_id_key, context_id_key = DELETE_ACTIONS[resource]
        resource_id = info.get(context_id_key)
        if not resource_id:
            results.append(
                {
                    "resource": resource,
                    "id": None,
                    "status": "failed",
                    "error": f"missing {context_id_key}",
                }
            )
            continue
        try:
            client.invoke(action, {request_id_key: resource_id}, region)
        except Exception as exc:  # noqa: BLE001 - rollback should report all failed deletes.
            results.append(
                {"resource": resource, "id": resource_id, "status": "failed", "error": str(exc)}
            )
        else:
            results.append({"resource": resource, "id": resource_id, "status": "deleted"})
    status = "PASS" if all(item["status"] == "deleted" for item in results) else "PARTIAL"
    return {"status": status, "rollback": results}


def _initial_context(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    context: dict[str, dict[str, Any]] = {}
    for resource in ["topic", "integration", "notice_content", "notice", "policy"]:
        config = bundle.get(resource)
        if isinstance(config, dict) and config.get("mode") in {"existing", "update", "skip"}:
            context[resource] = {
                key: value for key, value in config.items() if key not in {"payload"}
            }
    return context


def _preflight_tokens(
    bundle: dict[str, Any], plan: dict[str, Any], context: dict[str, dict[str, Any]]
) -> None:
    available = copy.deepcopy(context)
    for step in plan["steps"]:
        resource = step["resource"]
        mode = step["mode"]
        if mode in {"existing", "skip"}:
            continue
        _, _, _, context_id_key = WRITE_ACTIONS[(resource, mode)]
        payload = bundle[resource]["payload"]
        for token_resource, token_key in _tokens_in_value(payload):
            if token_resource not in available or token_key not in available[token_resource]:
                raise InputError(f"unresolved bundle token: ${{{token_resource}.{token_key}}}")
        available.setdefault(resource, {})["mode"] = mode
        _merge_resource_context(available[resource], resource, payload)
        available[resource][context_id_key] = f"<{context_id_key}>"


def _merge_resource_context(
    target: dict[str, Any], resource: str, payload: dict[str, Any]
) -> None:
    if resource == "topic" and payload.get("LogsetId"):
        target["logset_id"] = payload["LogsetId"]


def _tokens_in_value(value: Any) -> list[tuple[str, str]]:
    if isinstance(value, dict):
        return [token for item in value.values() for token in _tokens_in_value(item)]
    if isinstance(value, list):
        return [token for item in value for token in _tokens_in_value(item)]
    if isinstance(value, str):
        return [(match.group(1), match.group(2)) for match in BUNDLE_TOKEN_RE.finditer(value)]
    return []


def _resolve_tokens(value: Any, context: dict[str, dict[str, Any]]) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_tokens(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_tokens(item, context) for item in value]
    if isinstance(value, str):

        def replace(match: re.Match[str]) -> str:
            resource = match.group(1)
            key = match.group(2)
            if resource not in context or key not in context[resource]:
                raise InputError(f"unresolved bundle token: {match.group(0)}")
            return str(context[resource][key])

        return BUNDLE_TOKEN_RE.sub(replace, value)
    return value
