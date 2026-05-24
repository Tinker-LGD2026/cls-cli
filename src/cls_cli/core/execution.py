from __future__ import annotations

from typing import Any

import typer

from cls_cli.api.actions import get_spec
from cls_cli.core.alarm_action_policies import sanitize_action_payload, validate_action_payload
from cls_cli.core.client import ClsClient
from cls_cli.core.config import Profile, store_from_obj
from cls_cli.core.errors import CliError, ConfigError, ConfirmationRequired
from cls_cli.core.input import compact_payload, load_json_payload
from cls_cli.core.output import emit_data, emit_error


def run_action(
    ctx: typer.Context,
    spec_key: str,
    *,
    explicit_payload: dict[str, Any] | None = None,
    payload: str | None = None,
    region: str | None = None,
    profile: str | None = None,
    output: str = "json",
    force: bool = False,
    dry_run: bool = False,
    skip_validation: bool = False,
) -> None:
    spec = get_spec(spec_key)
    try:
        store = store_from_obj(_obj(ctx))
        profile_obj = store.get_profile(profile)
        selected_region = _resolve_region(region, profile_obj)
        body = load_json_payload(payload)
        body.update(compact_payload(explicit_payload or {}))
        body = _normalize_action_payload(spec_key, body)
        validate_action_payload(spec_key, body, skip_validation=skip_validation)
        if spec.destructive and not force and not dry_run:
            raise ConfirmationRequired(
                f"{spec.action} is destructive; pass --force or use --dry-run"
            )
        if dry_run:
            emit_data(
                {
                    "dry_run": True,
                    "action": spec.action,
                    "region": selected_region,
                    "payload": sanitize_action_payload(spec_key, body),
                },
                output,
            )
            return
        client = _client(ctx, profile_obj)
        result = client.invoke(spec.action, body, selected_region)
        emit_data(sanitize_action_payload(spec_key, result), output)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


def _normalize_action_payload(spec_key: str, body: dict[str, Any]) -> dict[str, Any]:
    if spec_key != "alarm.policy.list":
        return body
    filters = body.get("Filters")
    if not isinstance(filters, list):
        return body
    normalized_filters: list[Any] = []
    changed = False
    for item in filters:
        if isinstance(item, dict) and "Key" not in item and "Name" in item:
            normalized = dict(item)
            normalized["Key"] = normalized.pop("Name")
            normalized_filters.append(normalized)
            changed = True
        else:
            normalized_filters.append(item)
    if not changed:
        return body
    normalized_body = dict(body)
    normalized_body["Filters"] = normalized_filters
    return normalized_body


def _obj(ctx: typer.Context) -> dict[str, Any] | None:
    return ctx.obj if isinstance(ctx.obj, dict) else None


def _client(ctx: typer.Context, profile: Profile | None) -> Any:
    obj = _obj(ctx)
    if obj and obj.get("client") is not None:
        return obj["client"]
    return ClsClient(profile)


def _resolve_region(region: str | None, profile: Profile | None) -> str:
    selected = region or (profile.region if profile else None)
    if not selected:
        raise ConfigError("region is required; pass --region or configure a profile")
    return selected
