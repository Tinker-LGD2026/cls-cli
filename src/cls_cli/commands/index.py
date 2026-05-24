from __future__ import annotations

import typer

from cls_cli.core.execution import run_action
from cls_cli.core.input import parse_int

app = typer.Typer(no_args_is_help=True, help="Manage CLS indexes and rebuild tasks.")


@app.command("get")
def get_index(
    ctx: typer.Context,
    topic_id: str = typer.Option(..., "--topic-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "index.get",
        explicit_payload={"TopicId": topic_id},
        region=region,
        profile=profile,
        output=output,
    )


@app.command("create")
def create_index(
    ctx: typer.Context,
    topic_id: str = typer.Option(..., "--topic-id"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "index.create",
        explicit_payload={"TopicId": topic_id},
        payload=payload,
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("update")
def update_index(
    ctx: typer.Context,
    topic_id: str = typer.Option(..., "--topic-id"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "index.update",
        explicit_payload={"TopicId": topic_id},
        payload=payload,
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("delete")
def delete_index(
    ctx: typer.Context,
    topic_id: str = typer.Option(..., "--topic-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "index.delete",
        explicit_payload={"TopicId": topic_id},
        region=region,
        profile=profile,
        output=output,
        force=force,
        dry_run=dry_run,
    )


@app.command("rebuild-estimate")
def rebuild_estimate(
    ctx: typer.Context,
    topic_id: str = typer.Option(..., "--topic-id"),
    start_time: str = typer.Option(..., "--start-time"),
    end_time: str = typer.Option(..., "--end-time"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "index.rebuild_estimate",
        explicit_payload={
            "TopicId": topic_id,
            "StartTime": parse_int(start_time, "start-time"),
            "EndTime": parse_int(end_time, "end-time"),
        },
        region=region,
        profile=profile,
        output=output,
    )


@app.command("rebuild-create")
def rebuild_create(
    ctx: typer.Context,
    topic_id: str = typer.Option(..., "--topic-id"),
    start_time: str = typer.Option(..., "--start-time"),
    end_time: str = typer.Option(..., "--end-time"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "index.rebuild_create",
        explicit_payload={
            "TopicId": topic_id,
            "StartTime": parse_int(start_time, "start-time"),
            "EndTime": parse_int(end_time, "end-time"),
        },
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("rebuild-list")
def rebuild_list(
    ctx: typer.Context,
    topic_id: str | None = typer.Option(None, "--topic-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "index.rebuild_list",
        explicit_payload={"TopicId": topic_id},
        region=region,
        profile=profile,
        output=output,
    )


@app.command("rebuild-cancel")
def rebuild_cancel(
    ctx: typer.Context,
    task_id: str = typer.Option(..., "--task-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "index.rebuild_cancel",
        explicit_payload={"TaskId": task_id},
        region=region,
        profile=profile,
        output=output,
        force=force,
        dry_run=dry_run,
    )
