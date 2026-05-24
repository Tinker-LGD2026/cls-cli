from __future__ import annotations

import typer

from cls_cli.core.alarm_integrations import (
    scaffold_advanced_notice_payload,
    scaffold_notice_payload,
    validate_notice_payload,
)
from cls_cli.core.errors import CliError
from cls_cli.core.input import load_json_payload
from cls_cli.core.output import emit_data, emit_error

app = typer.Typer(no_args_is_help=True, help="Manage alarm notices.")
RECEIVER_ID_OPTION = typer.Option(None, "--receiver-id")
RECEIVER_CHANNEL_OPTION = typer.Option(None, "--receiver-channel")
RULE_NOTIFY_TYPE_OPTION = typer.Option(None, "--rule-notify-type")
RULE_LEVEL_OPTION = typer.Option(None, "--rule-level")
RULE_LABEL_IN_OPTION = typer.Option(None, "--rule-label-in")
RULE_LABEL_REGEX_OPTION = typer.Option(None, "--rule-label-regex")


@app.command("scaffold")
def scaffold_notice(
    name: str = typer.Option(..., "--name"),
    callback_type: str = typer.Option(..., "--callback-type"),
    integration_id: str = typer.Option(..., "--integration-id"),
    content_id: str = typer.Option(..., "--content-id"),
    method: str | None = typer.Option(None, "--method"),
    notice_type: str = typer.Option("All", "--notice-type"),
    advanced_rule: bool = typer.Option(False, "--advanced-rule"),
    rule: str | None = typer.Option(None, "--rule"),
    rule_notify_types: list[int] | None = RULE_NOTIFY_TYPE_OPTION,
    rule_levels: list[int] | None = RULE_LEVEL_OPTION,
    rule_notify_time_between: str | None = typer.Option(None, "--rule-notify-time-between"),
    rule_duration_gt: int | None = typer.Option(None, "--rule-duration-gt"),
    rule_alarm_name_regex: str | None = typer.Option(None, "--rule-alarm-name-regex"),
    rule_label_in: list[str] | None = RULE_LABEL_IN_OPTION,
    rule_label_regex: list[str] | None = RULE_LABEL_REGEX_OPTION,
    receiver_ids: list[int] | None = RECEIVER_ID_OPTION,
    receiver_channels: list[str] | None = RECEIVER_CHANNEL_OPTION,
    receiver_type: str = typer.Option("Uin", "--receiver-type"),
    receiver_start_time: str = typer.Option("00:00:00", "--receiver-start-time"),
    receiver_end_time: str = typer.Option("23:59:59", "--receiver-end-time"),
    receiver_index: int = typer.Option(1, "--receiver-index"),
    receiver_content_id: str = typer.Option("", "--receiver-content-id"),
    escalate: bool = typer.Option(False, "--escalate"),
    escalate_interval: int | None = typer.Option(None, "--escalate-interval"),
    escalate_type: int | None = typer.Option(None, "--escalate-type"),
    escalate_callback_type: str | None = typer.Option(None, "--escalate-callback-type"),
    escalate_integration_id: str | None = typer.Option(None, "--escalate-integration-id"),
    escalate_content_id: str | None = typer.Option(None, "--escalate-content-id"),
    escalate_method: str | None = typer.Option(None, "--escalate-method"),
    callback_prioritize: bool = typer.Option(False, "--callback-prioritize"),
    output: str = typer.Option("json", "--output"),
) -> None:
    try:
        if advanced_rule:
            payload = scaffold_advanced_notice_payload(
                name=name,
                callback_type=callback_type,
                integration_id=integration_id,
                notice_content_id=content_id,
                method=method,
                rule=rule,
                rule_notify_types=rule_notify_types,
                rule_levels=rule_levels,
                rule_notify_time_between=rule_notify_time_between,
                rule_duration_gt=rule_duration_gt,
                rule_alarm_name_regex=rule_alarm_name_regex,
                rule_label_in=rule_label_in,
                rule_label_regex=rule_label_regex,
                receiver_ids=receiver_ids,
                receiver_channels=receiver_channels,
                receiver_type=receiver_type,
                receiver_start_time=receiver_start_time,
                receiver_end_time=receiver_end_time,
                receiver_index=receiver_index,
                receiver_notice_content_id=receiver_content_id,
                escalate=escalate,
                escalate_interval=escalate_interval,
                escalate_type=escalate_type,
                escalate_callback_type=escalate_callback_type,
                escalate_integration_id=escalate_integration_id,
                escalate_notice_content_id=escalate_content_id,
                escalate_method=escalate_method,
                callback_prioritize=callback_prioritize,
            )
        else:
            payload = scaffold_notice_payload(
                name=name,
                callback_type=callback_type,
                integration_id=integration_id,
                notice_content_id=content_id,
                method=method,
                notice_type=notice_type,
            )
        emit_data({"payload": payload}, output)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("validate")
def validate_notice(
    payload: str = typer.Option(..., "--payload"),
    output: str = typer.Option("json", "--output"),
) -> None:
    body = load_json_payload(payload)
    issues = validate_notice_payload(body)
    emit_data({"valid": not issues, "issues": issues}, output)
    if issues:
        raise typer.Exit(1)
