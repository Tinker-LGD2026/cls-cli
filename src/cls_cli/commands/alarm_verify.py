from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from cls_cli.commands.alarm_template import send_robot_message
from cls_cli.core.alarm_cleanup import AlarmCleanupOptions, parse_older_than, run_alarm_cleanup
from cls_cli.core.alarm_e2e import AlarmE2EOptions, plan_alarm_e2e, run_alarm_e2e
from cls_cli.core.alarm_webhook_matrix import (
    WebhookMatrixOptions,
    plan_webhook_function_matrix,
    run_webhook_function_matrix,
)
from cls_cli.core.config import store_from_obj
from cls_cli.core.errors import CliError, ConfirmationRequired
from cls_cli.core.execution import _client, _obj, _resolve_region
from cls_cli.core.output import emit_data, emit_error

app = typer.Typer(no_args_is_help=True, help="Run alarm verification workflows.")
WEBHOOK_CASE_ID_OPTION = typer.Option(None, "--case-id")
DEFAULT_WEBHOOK_MATRIX_OUTPUT_DIR = Path(".tmp/alarm-webhook-matrix")


@app.command("e2e")
def verify_e2e(
    ctx: typer.Context,
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    confirm_real_write: bool = typer.Option(False, "--confirm-real-write"),
    keep_resources: bool = typer.Option(False, "--keep-resources"),
    run_id: str | None = typer.Option(None, "--run-id"),
    poll_seconds: int = typer.Option(600, "--poll-seconds"),
    poll_interval_seconds: int = typer.Option(30, "--poll-interval-seconds"),
    advanced: bool = typer.Option(
        False,
        "--advanced",
        help="Use advanced MultiConditions and NoticeRules payloads in the real E2E flow.",
    ),
    send_robot_smoke_test: bool = typer.Option(
        False,
        "--send-robot-smoke-test",
        help=(
            "Also send rendered templates directly to robot webhooks; "
            "not used as CLS E2E pass evidence."
        ),
    ),
    skip_robot_send: bool = typer.Option(
        False,
        "--skip-robot-send",
        help="Deprecated compatibility flag; direct robot smoke test is off by default.",
    ),
) -> None:
    try:
        store = store_from_obj(_obj(ctx))
        profile_obj = store.get_profile(profile)
        selected_region = _resolve_region(region, profile_obj)
        options = AlarmE2EOptions(
            confirm_real_write=confirm_real_write,
            run_id=run_id,
            poll_seconds=poll_seconds,
            poll_interval_seconds=poll_interval_seconds,
            cleanup=not keep_resources,
            advanced=advanced,
            send_wecom=send_robot_smoke_test and not skip_robot_send,
            send_feishu=send_robot_smoke_test and not skip_robot_send,
        )
        if dry_run:
            emit_data(plan_alarm_e2e(selected_region, options), output)
            return
        if not confirm_real_write:
            raise ConfirmationRequired(
                "pass --confirm-real-write to create temporary CLS resources"
            )
        client = _client(ctx, profile_obj)
        result = run_alarm_e2e(
            client,
            selected_region,
            options,
            robot_sender=send_robot_message,
        )
        emit_data(result, output)
        if result.get("status") == "FAIL":
            raise typer.Exit(1)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("webhook-functions")
def verify_webhook_functions(
    ctx: typer.Context,
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    confirm_real_write: bool = typer.Option(False, "--confirm-real-write"),
    keep_resources: bool = typer.Option(False, "--keep-resources"),
    run_id: str | None = typer.Option(None, "--run-id"),
    case_ids: list[str] | None = WEBHOOK_CASE_ID_OPTION,
    public_webhook_url: str | None = typer.Option(None, "--public-webhook-url"),
    external_receiver_result_url: str | None = typer.Option(
        None,
        "--external-receiver-result-url",
        help=(
            "Optional query endpoint exposed by the test receiver; "
            "not required for customer platforms."
        ),
    ),
    receiver_host: str = typer.Option("127.0.0.1", "--receiver-host"),
    receiver_port: int = typer.Option(8765, "--receiver-port"),
    poll_seconds: int = typer.Option(600, "--poll-seconds"),
    poll_interval_seconds: int = typer.Option(30, "--poll-interval-seconds"),
    external_receiver: bool = typer.Option(False, "--external-receiver"),
    output_dir: Annotated[Path, typer.Option("--output-dir")] = DEFAULT_WEBHOOK_MATRIX_OUTPUT_DIR,
) -> None:
    try:
        store = store_from_obj(_obj(ctx))
        profile_obj = store.get_profile(profile)
        selected_region = _resolve_region(region, profile_obj)
        options = WebhookMatrixOptions(
            confirm_real_write=confirm_real_write,
            region=selected_region,
            run_id=run_id,
            case_ids=case_ids,
            receiver_host=receiver_host,
            receiver_port=receiver_port,
            public_webhook_url=public_webhook_url,
            external_receiver_result_url=external_receiver_result_url,
            poll_seconds=poll_seconds,
            poll_interval_seconds=poll_interval_seconds,
            cleanup=not keep_resources,
            output_dir=output_dir,
            external_receiver=external_receiver,
            start_receiver=not external_receiver,
        )
        if dry_run:
            emit_data(plan_webhook_function_matrix(options), output)
            return
        if not confirm_real_write:
            raise ConfirmationRequired(
                "pass --confirm-real-write to create temporary CLS resources"
            )
        result = run_webhook_function_matrix(_client(ctx, profile_obj), options)
        emit_data(result, output)
        if result.get("status") == "FAIL":
            raise typer.Exit(1)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("cleanup")
def verify_cleanup(
    ctx: typer.Context,
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    prefix: str = typer.Option(..., "--prefix"),
    older_than: str | None = typer.Option(None, "--older-than"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    try:
        store = store_from_obj(_obj(ctx))
        profile_obj = store.get_profile(profile)
        selected_region = _resolve_region(region, profile_obj)
        options = AlarmCleanupOptions(
            prefix=prefix,
            force=force,
            dry_run=dry_run,
            older_than_seconds=parse_older_than(older_than),
        )
        if not dry_run and not force:
            raise ConfirmationRequired(
                "cleanup deletes CLS resources; pass --force or use --dry-run"
            )
        result = run_alarm_cleanup(_client(ctx, profile_obj), selected_region, options)
        emit_data(result, output)
        if result.get("status") == "PARTIAL":
            raise typer.Exit(1)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc
