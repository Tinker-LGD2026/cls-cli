from __future__ import annotations

import typer

from cls_cli.core.alarm_debug import (
    alarm_log_query as _alarm_log_query,
)
from cls_cli.core.alarm_debug import (
    debug_window as _debug_window,
)
from cls_cli.core.alarm_debug import (
    explain_debug as _explain_debug,
)
from cls_cli.core.alarm_debug import (
    filters as _filters,
)
from cls_cli.core.config import store_from_obj
from cls_cli.core.errors import CliError
from cls_cli.core.execution import _client, _obj, _resolve_region
from cls_cli.core.output import emit_data, emit_error

app = typer.Typer(no_args_is_help=True, help="Diagnose alarm execution issues.")


@app.command("explain")
def debug_explain(
    ctx: typer.Context,
    alarm_id: str = typer.Option(..., "--alarm-id"),
    topic_id: str | None = typer.Option(None, "--topic-id"),
    from_time: str | None = typer.Option(None, "--from"),
    to_time: str | None = typer.Option(None, "--to"),
    hours: int = typer.Option(2, "--hours"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    try:
        store = store_from_obj(_obj(ctx))
        profile_obj = store.get_profile(profile)
        selected_region = _resolve_region(region, profile_obj)
        client = _client(ctx, profile_obj)
        from_ms, to_ms = _debug_window(from_time, to_time, hours)
        policy = client.invoke(
            "DescribeAlarms",
            {
                "Filters": [{"Name": "alarmId", "Values": [alarm_id]}],
                "Offset": 0,
                "Limit": 1,
            },
            selected_region,
        )
        history_payload = {
            "From": from_ms,
            "To": to_ms,
            "Offset": 0,
            "Limit": 20,
            "Filters": _filters({"alertId": alarm_id, "topicId": topic_id}) or None,
        }
        history = client.invoke("DescribeAlertRecordHistory", history_payload, selected_region)
        log_payload = {
            "From": from_ms,
            "To": to_ms,
            "Query": _alarm_log_query(alarm_id, topic_id),
            "Limit": 20,
            "UseNewAnalysis": True,
        }
        execution_log = client.invoke("GetAlarmLog", log_payload, selected_region)
        emit_data(_explain_debug(policy, history, execution_log), output)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc
