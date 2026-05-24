from __future__ import annotations

import typer

from cls_cli.core.alarm_debug import (
    alarm_log_query as _alarm_log_query,
)
from cls_cli.core.alarm_debug import (
    filters as _filters,
)
from cls_cli.core.alarm_debug import (
    sanitize_sensitive as _sanitize_sensitive,
)
from cls_cli.core.config import store_from_obj
from cls_cli.core.errors import CliError
from cls_cli.core.execution import _client, _obj, _resolve_region, run_action
from cls_cli.core.input import load_json_payload, parse_timestamp_ms
from cls_cli.core.output import emit_data, emit_error


def register(app: typer.Typer) -> None:
    @app.command("history")
    def history(
        ctx: typer.Context,
        alarm_id: str | None = typer.Option(None, "--alarm-id"),
        topic_id: str | None = typer.Option(None, "--topic-id"),
        status: str | None = typer.Option(None, "--status"),
        alarm_level: str | None = typer.Option(None, "--alarm-level"),
        from_time: str | None = typer.Option(None, "--from"),
        to_time: str | None = typer.Option(None, "--to"),
        offset: int | None = typer.Option(None, "--offset"),
        limit: int | None = typer.Option(None, "--limit"),
        payload: str | None = typer.Option(None, "--payload"),
        region: str | None = typer.Option(None, "--region"),
        profile: str | None = typer.Option(None, "--profile"),
        output: str = typer.Option("json", "--output"),
    ) -> None:
        filters = _filters(
            {"alertId": alarm_id, "topicId": topic_id, "status": status, "alarmLevel": alarm_level}
        )
        run_action(
            ctx,
            "alarm.history",
            explicit_payload={
                "From": parse_timestamp_ms(from_time, "from"),
                "To": parse_timestamp_ms(to_time, "to"),
                "Offset": offset,
                "Limit": limit,
                "Filters": filters or None,
            },
            payload=payload,
            region=region,
            profile=profile,
            output=output,
        )

    @app.command("log")
    def alarm_log(
        ctx: typer.Context,
        alarm_id: str | None = typer.Option(None, "--alarm-id"),
        topic_id: str | None = typer.Option(None, "--topic-id"),
        query: str | None = typer.Option(None, "--query"),
        from_time: str | None = typer.Option(None, "--from"),
        to_time: str | None = typer.Option(None, "--to"),
        limit: int | None = typer.Option(None, "--limit"),
        context: str | None = typer.Option(None, "--context"),
        sort: str | None = typer.Option(None, "--sort"),
        use_new_analysis: bool = typer.Option(False, "--use-new-analysis"),
        payload: str | None = typer.Option(None, "--payload"),
        region: str | None = typer.Option(None, "--region"),
        profile: str | None = typer.Option(None, "--profile"),
        output: str = typer.Option("json", "--output"),
    ) -> None:
        try:
            store = store_from_obj(_obj(ctx))
            profile_obj = store.get_profile(profile)
            selected_region = _resolve_region(region, profile_obj)
            body = load_json_payload(payload)
            body.update(
                {
                    key: value
                    for key, value in {
                        "From": parse_timestamp_ms(from_time, "from"),
                        "To": parse_timestamp_ms(to_time, "to"),
                        "Query": query or _alarm_log_query(alarm_id, topic_id),
                        "Limit": limit,
                        "Context": context,
                        "Sort": sort,
                        "UseNewAnalysis": True if use_new_analysis else None,
                    }.items()
                    if value is not None
                }
            )
            result = _client(ctx, profile_obj).invoke("GetAlarmLog", body, selected_region)
            emit_data(_sanitize_sensitive(result), output)
        except CliError as exc:
            emit_error(exc)
            raise typer.Exit(exc.exit_code) from exc
