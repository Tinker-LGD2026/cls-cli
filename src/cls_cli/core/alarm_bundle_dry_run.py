from __future__ import annotations

import copy
from typing import Any

from cls_cli.core.alarm_action_policies import sanitize_action_payload, validate_action_payload
from cls_cli.core.alarm_bundle_apply import (
    DELETE_ACTIONS,
    WRITE_ACTIONS,
    _initial_context,
    _merge_resource_context,
    _resolve_tokens,
)
from cls_cli.core.alarm_bundle_plan import plan_alarm_bundle
from cls_cli.core.errors import InputError


def dry_run_alarm_bundle(bundle: dict[str, Any], region: str | None = None) -> dict[str, Any]:
    plan = plan_alarm_bundle(bundle)
    if not plan["valid"]:
        return {
            "valid": False,
            "issues": plan["issues"],
            "steps": [],
            "rollback_preview": [],
            "name": bundle.get("name"),
            "region": region or bundle.get("region"),
        }

    context = _initial_context(bundle)
    issues: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    created: list[tuple[str, str]] = []

    for step in plan["steps"]:
        resource = step["resource"]
        mode = step["mode"]
        if mode in {"existing", "skip"}:
            continue
        spec_key, action, response_id_key, context_id_key = WRITE_ACTIONS[(resource, mode)]
        step_result: dict[str, Any] = {
            "resource": resource,
            "mode": mode,
            "action": action,
            "spec_key": spec_key,
            "valid": True,
        }
        try:
            payload = _resolve_tokens(bundle[resource]["payload"], context)
            if mode == "update":
                resource_id = str(bundle[resource].get(context_id_key) or "")
                if not resource_id:
                    raise InputError(f"{resource} update requires {context_id_key}")
                payload[response_id_key] = resource_id
            validate_action_payload(spec_key, payload, skip_validation=False)
        except InputError as exc:
            issue = _issue(exc.code, exc.message, resource)
            issues.append(issue)
            step_result["valid"] = False
            step_result["issue"] = issue
            steps.append(step_result)
            continue

        step_result["payload"] = sanitize_action_payload(spec_key, copy.deepcopy(payload))
        steps.append(step_result)
        context.setdefault(resource, {})["mode"] = mode
        _merge_resource_context(context[resource], resource, payload)
        if mode == "create":
            synthetic_id = f"<{context_id_key}>"
            context[resource][context_id_key] = synthetic_id
            created.append((resource, synthetic_id))
        elif mode == "update":
            context[resource][context_id_key] = str(bundle[resource][context_id_key])

    return {
        "valid": not issues,
        "issues": issues,
        "steps": steps,
        "rollback_preview": _rollback_preview(created),
        "name": bundle.get("name"),
        "region": region or bundle.get("region"),
    }


def _rollback_preview(created: list[tuple[str, str]]) -> list[dict[str, str]]:
    preview: list[dict[str, str]] = []
    for resource, resource_id in reversed(created):
        action, _, _ = DELETE_ACTIONS[resource]
        preview.append({"resource": resource, "action": action, "id": resource_id})
    return preview


def _issue(code: str, message: str, path: str) -> dict[str, str]:
    return {"code": code, "message": message, "path": path, "severity": "error"}
