from __future__ import annotations

import typer

from cls_cli.core.execution import run_action
from cls_cli.core.input import load_jsonl, parse_timestamp_ms

app = typer.Typer(no_args_is_help=True, help="Search, upload, and export CLS logs.")


@app.command("search")
def search(
    ctx: typer.Context,
    topic_id: str | None = typer.Option(None, "--topic-id"),
    query: str | None = typer.Option(None, "--query"),
    start_time: str | None = typer.Option(None, "--start-time"),
    end_time: str | None = typer.Option(None, "--end-time"),
    limit: int | None = typer.Option(None, "--limit"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "log.search",
        explicit_payload={
            "TopicId": topic_id,
            "QueryString": query,
            "From": parse_timestamp_ms(start_time, "start-time"),
            "To": parse_timestamp_ms(end_time, "end-time"),
            "Limit": limit,
        },
        payload=payload,
        region=region,
        profile=profile,
        output=output,
    )


@app.command("histogram")
def histogram(
    ctx: typer.Context,
    topic_id: str | None = typer.Option(None, "--topic-id"),
    query: str | None = typer.Option(None, "--query"),
    start_time: str | None = typer.Option(None, "--start-time"),
    end_time: str | None = typer.Option(None, "--end-time"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "log.histogram",
        explicit_payload={
            "TopicId": topic_id,
            "Query": query,
            "From": parse_timestamp_ms(start_time, "start-time"),
            "To": parse_timestamp_ms(end_time, "end-time"),
        },
        payload=payload,
        region=region,
        profile=profile,
        output=output,
    )


@app.command("context")
def context(
    ctx: typer.Context,
    topic_id: str = typer.Option(..., "--topic-id"),
    package_id: str | None = typer.Option(None, "--package-id"),
    package_log_id: str | None = typer.Option(None, "--package-log-id"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "log.context",
        explicit_payload={
            "TopicId": topic_id,
            "PackageId": package_id,
            "PackageLogId": package_log_id,
        },
        payload=payload,
        region=region,
        profile=profile,
        output=output,
    )


@app.command("upload")
def upload(
    ctx: typer.Context,
    topic_id: str = typer.Option(..., "--topic-id"),
    jsonl: str | None = typer.Option(None, "--jsonl"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    explicit: dict[str, object] = {"TopicId": topic_id}
    if jsonl is not None:
        explicit["Logs"] = load_jsonl(jsonl)
    run_action(
        ctx,
        "log.upload",
        explicit_payload=explicit,
        payload=payload,
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("export-create")
def export_create(
    ctx: typer.Context,
    topic_id: str | None = typer.Option(None, "--topic-id"),
    start_time: str | None = typer.Option(None, "--start-time"),
    end_time: str | None = typer.Option(None, "--end-time"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "log.export_create",
        explicit_payload={
            "TopicId": topic_id,
            "From": parse_timestamp_ms(start_time, "start-time"),
            "To": parse_timestamp_ms(end_time, "end-time"),
        },
        payload=payload,
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("export-list")
def export_list(
    ctx: typer.Context,
    topic_id: str | None = typer.Option(None, "--topic-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "log.export_list",
        explicit_payload={"TopicId": topic_id},
        region=region,
        profile=profile,
        output=output,
    )


@app.command("export-delete")
def export_delete(
    ctx: typer.Context,
    export_id: str = typer.Option(..., "--export-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "log.export_delete",
        explicit_payload={"ExportId": export_id},
        region=region,
        profile=profile,
        output=output,
        force=force,
        dry_run=dry_run,
    )
