from __future__ import annotations

import os
from typing import Any

import typer

from cls_cli.api.actions import get_spec
from cls_cli.core.alarm_action_policies import validate_action_payload
from cls_cli.core.alarm_integrations import (
    build_integration_payload,
    sanitize_sensitive,
    validate_integration_payload,
)
from cls_cli.core.config import store_from_obj
from cls_cli.core.errors import CliError, ConfirmationRequired
from cls_cli.core.execution import _client, _obj, _resolve_region
from cls_cli.core.input import load_json_payload
from cls_cli.core.output import emit_data, emit_error

app = typer.Typer(
    no_args_is_help=True,
    help="Manage console integration configurations backed by WebCallback APIs.",
)


@app.command("list")
def list_integrations(
    ctx: typer.Context,
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    try:
        _run_sanitized_action(
            ctx,
            "alarm.integration.list",
            {},
            region=region,
            profile=profile,
            output=output,
        )
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("scaffold")
def scaffold_integration(
    name: str = typer.Option(..., "--name"),
    integration_type: str = typer.Option(..., "--type"),
    webhook_env: str = typer.Option(..., "--webhook-env"),
    key_env: str | None = typer.Option(None, "--key-env"),
    method: str | None = typer.Option(None, "--method"),
    output: str = typer.Option("json", "--output"),
) -> None:
    try:
        payload = build_integration_payload(
            name=name,
            integration_type=integration_type,
            webhook_env=webhook_env,
            key_env=key_env,
            method=method,
            env_getter=os.environ.get,
        )
        emit_data({"payload": sanitize_sensitive(payload)}, output)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("validate")
def validate_integration(
    payload: str = typer.Option(..., "--payload"),
    output: str = typer.Option("json", "--output"),
) -> None:
    body = load_json_payload(payload)
    issues = validate_integration_payload(body)
    emit_data({"valid": not issues, "issues": issues}, output)
    if issues:
        raise typer.Exit(1)


@app.command("create")
def create_integration(
    ctx: typer.Context,
    payload: str | None = typer.Option(None, "--payload"),
    name: str | None = typer.Option(None, "--name"),
    integration_type: str | None = typer.Option(None, "--type"),
    webhook_env: str | None = typer.Option(None, "--webhook-env"),
    key_env: str | None = typer.Option(None, "--key-env"),
    method: str | None = typer.Option(None, "--method"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    skip_validation: bool = typer.Option(False, "--skip-validation"),
) -> None:
    try:
        body = load_json_payload(payload) if payload else build_integration_payload(
            name=name or "",
            integration_type=integration_type or "",
            webhook_env=webhook_env,
            key_env=key_env,
            method=method,
            env_getter=os.environ.get,
        )
        validate_action_payload(
            "alarm.integration.create", body, skip_validation=skip_validation
        )
        _run_sanitized_action(
            ctx,
            "alarm.integration.create",
            body,
            region=region,
            profile=profile,
            output=output,
            dry_run=dry_run,
        )
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("update")
def update_integration(
    ctx: typer.Context,
    integration_id: str = typer.Option(..., "--integration-id"),
    payload: str | None = typer.Option(None, "--payload"),
    name: str | None = typer.Option(None, "--name"),
    integration_type: str | None = typer.Option(None, "--type"),
    webhook_env: str | None = typer.Option(None, "--webhook-env"),
    key_env: str | None = typer.Option(None, "--key-env"),
    method: str | None = typer.Option(None, "--method"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    skip_validation: bool = typer.Option(False, "--skip-validation"),
) -> None:
    try:
        body = load_json_payload(payload) if payload else build_integration_payload(
            name=name or "",
            integration_type=integration_type or "",
            webhook_env=webhook_env,
            key_env=key_env,
            method=method,
            env_getter=os.environ.get,
        )
        body["WebCallbackId"] = integration_id
        validate_action_payload(
            "alarm.integration.update", body, skip_validation=skip_validation
        )
        _run_sanitized_action(
            ctx,
            "alarm.integration.update",
            body,
            region=region,
            profile=profile,
            output=output,
            dry_run=dry_run,
        )
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("delete")
def delete_integration(
    ctx: typer.Context,
    integration_id: str = typer.Option(..., "--integration-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    try:
        _run_sanitized_action(
            ctx,
            "alarm.integration.delete",
            {"WebCallbackId": integration_id},
            region=region,
            profile=profile,
            output=output,
            dry_run=dry_run,
            force=force,
        )
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


def _run_sanitized_action(
    ctx: typer.Context,
    spec_key: str,
    body: dict[str, Any],
    *,
    region: str | None,
    profile: str | None,
    output: str,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    spec = get_spec(spec_key)
    store = store_from_obj(_obj(ctx))
    profile_obj = store.get_profile(profile)
    selected_region = _resolve_region(region, profile_obj)
    if spec.destructive and not force and not dry_run:
        raise ConfirmationRequired(f"{spec.action} is destructive; pass --force or use --dry-run")
    if dry_run:
        emit_data(
            {
                "dry_run": True,
                "action": spec.action,
                "region": selected_region,
                "payload": sanitize_sensitive(body),
            },
            output,
        )
        return
    result = _client(ctx, profile_obj).invoke(spec.action, body, selected_region)
    emit_data(sanitize_sensitive(result), output)
