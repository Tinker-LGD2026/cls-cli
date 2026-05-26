from __future__ import annotations

import json
from pathlib import Path

import typer

from cls_cli.core.alarm_bundle_apply import apply_alarm_bundle, rollback_alarm_bundle
from cls_cli.core.alarm_bundle_dry_run import dry_run_alarm_bundle
from cls_cli.core.alarm_bundle_plan import plan_alarm_bundle
from cls_cli.core.alarm_integrations import sanitize_sensitive
from cls_cli.core.config import store_from_obj
from cls_cli.core.errors import CliError
from cls_cli.core.execution import _client, _obj, _resolve_region
from cls_cli.core.input import load_json_payload
from cls_cli.core.output import emit_data, emit_error

app = typer.Typer(no_args_is_help=True, help="Plan and apply composed alarm resources.")


@app.command("plan")
def plan_bundle(
    bundle: str = typer.Option(..., "--bundle"),
    output: str = typer.Option("json", "--output"),
) -> None:
    try:
        result = plan_alarm_bundle(load_json_payload(bundle))
        emit_data(result, output)
        if not result["valid"]:
            raise typer.Exit(1)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("dry-run")
def dry_run_bundle(
    bundle: str = typer.Option(..., "--bundle"),
    region: str | None = typer.Option(None, "--region"),
    output: str = typer.Option("json", "--output"),
) -> None:
    try:
        body = load_json_payload(bundle)
        result = dry_run_alarm_bundle(body, region=region)
        emit_data(sanitize_sensitive(result), output)
        if not result["valid"]:
            raise typer.Exit(1)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("apply")
def apply_bundle(
    ctx: typer.Context,
    bundle: str = typer.Option(..., "--bundle"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    confirm_real_write: bool = typer.Option(False, "--confirm-real-write"),
    confirmation_text: str | None = typer.Option(None, "--confirmation-text"),
    manifest_out: str | None = typer.Option(None, "--manifest-out"),
    output: str = typer.Option("json", "--output"),
) -> None:
    try:
        store = store_from_obj(_obj(ctx))
        profile_obj = store.get_profile(profile)
        body = load_json_payload(bundle)
        selected_region = _resolve_region(region or body.get("region"), profile_obj)
        result = apply_alarm_bundle(
            _client(ctx, profile_obj),
            body,
            selected_region,
            confirm_real_write=confirm_real_write,
            confirmation_text=confirmation_text,
        )
        if manifest_out and isinstance(result.get("manifest"), dict):
            _write_json_file(manifest_out, result["manifest"])
        emit_data(sanitize_sensitive(result), output)
        if result.get("status") == "FAIL":
            raise typer.Exit(1)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


def _write_json_file(path: str, data: dict[str, object]) -> None:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


@app.command("rollback")
def rollback_bundle(
    ctx: typer.Context,
    manifest: str = typer.Option(..., "--manifest"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    force: bool = typer.Option(False, "--force"),
    confirmation_text: str | None = typer.Option(None, "--confirmation-text"),
    output: str = typer.Option("json", "--output"),
) -> None:
    try:
        store = store_from_obj(_obj(ctx))
        profile_obj = store.get_profile(profile)
        body = load_json_payload(manifest)
        selected_region = _resolve_region(region or body.get("region"), profile_obj)
        result = rollback_alarm_bundle(
            _client(ctx, profile_obj),
            body,
            selected_region,
            force=force,
            confirmation_text=confirmation_text,
        )
        emit_data(sanitize_sensitive(result), output)
        if result.get("status") == "PARTIAL":
            raise typer.Exit(1)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("status")
def status_bundle(
    manifest: str = typer.Option(..., "--manifest"),
    output: str = typer.Option("json", "--output"),
) -> None:
    try:
        body = load_json_payload(manifest)
        resources = body.get("resources") if isinstance(body, dict) else None
        status = {"valid": isinstance(resources, dict), "resources": resources or {}}
        emit_data(sanitize_sensitive(status), output)
        if not isinstance(resources, dict):
            raise typer.Exit(1)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc
