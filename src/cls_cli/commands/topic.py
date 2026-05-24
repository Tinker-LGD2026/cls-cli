from __future__ import annotations

import typer

from cls_cli.core.execution import run_action

app = typer.Typer(no_args_is_help=True, help="Manage CLS topics.")


@app.command("list")
def list_topics(
    ctx: typer.Context,
    logset_id: str | None = typer.Option(None, "--logset-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "topic.list",
        explicit_payload={
            "Filters": [{"Key": "logsetId", "Values": [logset_id]}] if logset_id else None
        },
        region=region,
        profile=profile,
        output=output,
    )


@app.command("get")
def get_topic(
    ctx: typer.Context,
    topic_id: str = typer.Option(..., "--topic-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "topic.get",
        explicit_payload={"Filters": [{"Key": "topicId", "Values": [topic_id]}]},
        region=region,
        profile=profile,
        output=output,
    )


@app.command("create")
def create_topic(
    ctx: typer.Context,
    logset_id: str | None = typer.Option(None, "--logset-id"),
    topic_name: str | None = typer.Option(None, "--topic-name"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "topic.create",
        explicit_payload={"LogsetId": logset_id, "TopicName": topic_name},
        payload=payload,
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("update")
def update_topic(
    ctx: typer.Context,
    topic_id: str = typer.Option(..., "--topic-id"),
    topic_name: str | None = typer.Option(None, "--topic-name"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "topic.update",
        explicit_payload={"TopicId": topic_id, "TopicName": topic_name},
        payload=payload,
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("delete")
def delete_topic(
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
        "topic.delete",
        explicit_payload={"TopicId": topic_id},
        region=region,
        profile=profile,
        output=output,
        force=force,
        dry_run=dry_run,
    )
