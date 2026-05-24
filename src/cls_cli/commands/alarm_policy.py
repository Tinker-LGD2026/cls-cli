from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from cls_cli.core.alarm_debug import (
    debug_window as _debug_window,
)
from cls_cli.core.alarm_debug import (
    test_policy_queries as _test_policy_queries,
)
from cls_cli.core.alarm_policy import (
    has_blocking_policy_issues,
    scaffold_policy_payload,
    validate_policy_payload,
)
from cls_cli.core.alarm_templates import scaffold_alarm_policy, split_fields
from cls_cli.core.config import store_from_obj
from cls_cli.core.errors import CliError, InputError
from cls_cli.core.execution import _client, _obj, _resolve_region
from cls_cli.core.input import load_json_payload
from cls_cli.core.output import emit_data, emit_error

app = typer.Typer(no_args_is_help=True, help="Manage alarm policies.")
NOTICE_ID_OPTION = typer.Option(None, "--notice-id")
MULTI_CONDITION_EXPR_OPTION = typer.Option(None, "--multi-condition-expr")
MULTI_CONDITION_LEVEL_OPTION = typer.Option(None, "--multi-condition-level")
CALLBACK_HEADER_OPTION = typer.Option(None, "--callback-header")
CLASSIFICATION_OPTION = typer.Option(None, "--classification")
ANALYSIS_QUERY_OPTION = typer.Option(None, "--analysis-query")


@app.command("validate")
def validate_policy(
    payload: str = typer.Option(..., "--payload"),
    output: str = typer.Option("json", "--output"),
) -> None:
    body = load_json_payload(payload)
    issues = validate_policy_payload(body)
    emit_data(
        {
            "valid": not has_blocking_policy_issues(issues),
            "issues": [issue.to_dict() for issue in issues],
        },
        output,
    )
    if has_blocking_policy_issues(issues):
        raise typer.Exit(1)


@app.command("test-query")
def test_policy_query(
    ctx: typer.Context,
    payload: str = typer.Option(..., "--payload"),
    from_time: str | None = typer.Option(None, "--from"),
    to_time: str | None = typer.Option(None, "--to"),
    limit: int = typer.Option(100, "--limit"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    try:
        store = store_from_obj(_obj(ctx))
        profile_obj = store.get_profile(profile)
        selected_region = _resolve_region(region, profile_obj)
        client = _client(ctx, profile_obj)
        policy = load_json_payload(payload)
        from_ms, to_ms = _debug_window(from_time, to_time, 2)
        result = _test_policy_queries(client, policy, selected_region, from_ms, to_ms, limit)
        emit_data(result, output)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("scaffold")
def scaffold_policy(
    scenario: str = typer.Option("http-5xx", "--scenario"),
    name: str = typer.Option(..., "--name"),
    logset_id: str = typer.Option(..., "--logset-id"),
    topic_id: str = typer.Option(..., "--topic-id"),
    threshold: int = typer.Option(1, "--threshold"),
    window_minutes: int = typer.Option(5, "--window-minutes"),
    fields: str | None = typer.Option(None, "--fields"),
    query: str | None = typer.Option(None, "--query"),
    condition: str | None = typer.Option(None, "--condition"),
    start_time_offset: int = typer.Option(-5, "--start-time-offset"),
    end_time_offset: int = typer.Option(0, "--end-time-offset"),
    monitor_period: int = typer.Option(5, "--monitor-period"),
    monitor_type: str = typer.Option("Period", "--monitor-type"),
    cron_expression: str | None = typer.Option(None, "--cron-expression"),
    trigger_count: int = typer.Option(1, "--trigger-count"),
    alarm_period: int = typer.Option(15, "--alarm-period"),
    alarm_level: int = typer.Option(0, "--alarm-level"),
    multi_condition: str | None = typer.Option(None, "--multi-condition"),
    multi_condition_expr: list[str] | None = MULTI_CONDITION_EXPR_OPTION,
    multi_condition_level: list[int] | None = MULTI_CONDITION_LEVEL_OPTION,
    group_trigger_status: str | None = typer.Option(None, "--group-trigger-status"),
    group_trigger_condition: str | None = typer.Option(None, "--group-trigger-condition"),
    group_by: str | None = typer.Option(None, "--group-by"),
    analysis: str | None = typer.Option(None, "--analysis"),
    analysis_query: list[str] | None = ANALYSIS_QUERY_OPTION,
    analysis_original_fields: str | None = typer.Option(None, "--analysis-original-fields"),
    classifications: str | None = typer.Option(None, "--classifications"),
    classification: list[str] | None = CLASSIFICATION_OPTION,
    message_template: str | None = typer.Option(None, "--message-template"),
    callback: str | None = typer.Option(None, "--callback"),
    callback_body: str | None = typer.Option(None, "--callback-body"),
    callback_header: list[str] | None = CALLBACK_HEADER_OPTION,
    notice_ids: list[str] | None = NOTICE_ID_OPTION,
    output: str = typer.Option("json", "--output"),
) -> None:
    try:
        if (query is None) != (condition is None):
            raise InputError("--query and --condition must be provided together")
        if query is not None and condition is not None:
            multi_conditions = _advanced_multi_conditions(
                multi_condition, multi_condition_expr, multi_condition_level
            )
            group_fields = _advanced_group_trigger_condition(group_trigger_condition, group_by)
            parsed_group_status = _parse_optional_bool(group_trigger_status)
            if group_fields is not None and parsed_group_status is None:
                parsed_group_status = True
            payload = scaffold_policy_payload(
                name=name,
                logset_id=logset_id,
                topic_id=topic_id,
                query=query,
                condition=condition,
                notice_ids=notice_ids,
                start_time_offset=start_time_offset,
                end_time_offset=end_time_offset,
                monitor_period=monitor_period,
                monitor_type=_normalize_monitor_type(monitor_type),
                cron_expression=cron_expression,
                trigger_count=trigger_count,
                alarm_period=alarm_period,
                alarm_level=alarm_level,
                multi_conditions=multi_conditions,
                group_trigger_status=parsed_group_status,
                group_trigger_condition=group_fields,
                analysis=_advanced_analysis(analysis, analysis_query, analysis_original_fields),
                classifications=_advanced_classifications(classifications, classification),
                message_template=message_template,
                callback=_advanced_callback(callback, callback_body, callback_header),
            )
        else:
            payload = scaffold_alarm_policy(
                scenario=scenario,
                name=name,
                logset_id=logset_id,
                topic_id=topic_id,
                threshold=threshold,
                window_minutes=window_minutes,
                fields=split_fields(fields, ["request_uri", "status"]),
                notice_ids=notice_ids,
            )
        emit_data({"payload": payload}, output)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


def _load_json_value(value: str | None) -> Any:
    if value is None:
        return None
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text(encoding="utf-8"))
    return json.loads(value)


def cast_list(value: Any, option_name: str) -> list[Any] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise InputError(f"--{option_name} must be a JSON array")
    return value


def cast_dict(value: Any, option_name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise InputError(f"--{option_name} must be a JSON object")
    return value


def cast_str_list(value: Any, option_name: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise InputError(f"--{option_name} must be a JSON string array")
    return value


def _advanced_multi_conditions(
    raw_json: str | None,
    expressions: list[str] | None,
    levels: list[int] | None,
) -> list[Any] | None:
    if raw_json is not None and expressions:
        raise InputError("--multi-condition conflicts with --multi-condition-expr")
    if raw_json is not None:
        return cast_list(_load_json_value(raw_json), "multi-condition")
    if not expressions:
        if levels:
            raise InputError("--multi-condition-level requires --multi-condition-expr")
        return None
    if levels and len(levels) != len(expressions):
        raise InputError("--multi-condition-level count must match --multi-condition-expr count")
    effective_levels = levels or [0] * len(expressions)
    return [
        {"Condition": expression, "AlarmLevel": level}
        for expression, level in zip(expressions, effective_levels, strict=True)
    ]


def _advanced_group_trigger_condition(
    raw_json: str | None, group_by: str | None
) -> list[str] | None:
    if raw_json is not None and group_by is not None:
        raise InputError("--group-trigger-condition conflicts with --group-by")
    if raw_json is not None:
        return cast_str_list(_load_json_value(raw_json), "group-trigger-condition")
    if group_by is None:
        return None
    return split_fields(group_by, [])


def _normalize_monitor_type(value: str) -> str:
    normalized = value.strip().lower()
    mapping = {"period": "Period", "fixed": "Fixed", "cron": "Cron"}
    if normalized not in mapping:
        raise InputError("--monitor-type must be period, fixed, or cron")
    return mapping[normalized]


def _advanced_analysis(
    raw_json: str | None,
    query_items: list[str] | None,
    original_fields: str | None,
) -> list[Any] | None:
    if raw_json is not None and (query_items or original_fields):
        raise InputError("--analysis conflicts with --analysis-query/--analysis-original-fields")
    if raw_json is not None:
        return cast_list(_load_json_value(raw_json), "analysis")
    result: list[Any] = []
    for item in query_items or []:
        name, query = _split_key_value(item, "analysis-query")
        result.append(
            {
                "Name": name,
                "Type": "query",
                "Content": query,
                "ConfigInfo": [{"Key": "SyntaxRule", "Value": "1"}],
            }
        )
    if original_fields:
        result.append(
            {
                "Name": "original logs",
                "Type": "original",
                "Content": "raw logs",
                "ConfigInfo": [
                    {"Key": "Fields", "Value": original_fields},
                    {"Key": "QueryIndex", "Value": "1"},
                    {"Key": "Format", "Value": "2"},
                    {"Key": "Limit", "Value": "5"},
                    {"Key": "SyntaxRule", "Value": "1"},
                ],
            }
        )
    return result or None


def _advanced_classifications(
    raw_json: str | None, items: list[str] | None
) -> list[Any] | None:
    if raw_json is not None and items:
        raise InputError("--classifications conflicts with --classification")
    if raw_json is not None:
        return cast_list(_load_json_value(raw_json), "classifications")
    if not items:
        return None
    return [
        {"Key": key, "Value": value}
        for key, value in (_split_key_value(item, "classification") for item in items)
    ]


def _split_key_value(value: str, option_name: str) -> tuple[str, str]:
    if "=" not in value:
        raise InputError(f"--{option_name} must use key=value format")
    key, item_value = value.split("=", 1)
    key = key.strip()
    item_value = item_value.strip()
    if not key or not item_value:
        raise InputError(f"--{option_name} must use non-empty key=value")
    return key, item_value


def _advanced_callback(
    raw_json: str | None,
    body: str | None,
    headers: list[str] | None,
) -> dict[str, Any] | None:
    if raw_json is not None and (body is not None or headers):
        raise InputError("--callback conflicts with --callback-body/--callback-header")
    if raw_json is not None:
        return cast_dict(_load_json_value(raw_json), "callback")
    if body is None and not headers:
        return None
    callback: dict[str, Any] = {}
    if body is not None:
        callback["Body"] = body
    if headers:
        callback["Headers"] = headers
    return callback


def _parse_optional_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise InputError("--group-trigger-status must be true or false")
