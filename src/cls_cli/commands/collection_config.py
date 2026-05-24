from __future__ import annotations

import typer

from cls_cli.core.execution import run_action

app = typer.Typer(no_args_is_help=True, help="Manage CLS collection configs and bindings.")


@app.command("list")
def list_configs(
    ctx: typer.Context,
    topic_id: str | None = typer.Option(None, "--topic-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "config.list",
        explicit_payload={"TopicId": topic_id},
        region=region,
        profile=profile,
        output=output,
    )


@app.command("get")
def get_config(
    ctx: typer.Context,
    config_id: str = typer.Option(..., "--config-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "config.get",
        explicit_payload={"ConfigId": config_id},
        region=region,
        profile=profile,
        output=output,
    )


@app.command("create")
def create_config(
    ctx: typer.Context,
    config_name: str | None = typer.Option(None, "--config-name"),
    topic_id: str | None = typer.Option(None, "--topic-id"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "config.create",
        explicit_payload={"Name": config_name, "Output": topic_id},
        payload=payload,
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("update")
def update_config(
    ctx: typer.Context,
    config_id: str = typer.Option(..., "--config-id"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "config.update",
        explicit_payload={"ConfigId": config_id},
        payload=payload,
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("delete")
def delete_config(
    ctx: typer.Context,
    config_id: str = typer.Option(..., "--config-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "config.delete",
        explicit_payload={"ConfigId": config_id},
        region=region,
        profile=profile,
        output=output,
        force=force,
        dry_run=dry_run,
    )


@app.command("apply")
def apply_config(
    ctx: typer.Context,
    config_id: str = typer.Option(..., "--config-id"),
    group_id: str = typer.Option(..., "--group-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "config.apply",
        explicit_payload={"ConfigId": config_id, "GroupId": group_id},
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("remove")
def remove_config(
    ctx: typer.Context,
    config_id: str = typer.Option(..., "--config-id"),
    group_id: str = typer.Option(..., "--group-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "config.remove",
        explicit_payload={"ConfigId": config_id, "GroupId": group_id},
        region=region,
        profile=profile,
        output=output,
        force=force,
        dry_run=dry_run,
    )


@app.command("bound-groups")
def bound_groups(
    ctx: typer.Context,
    config_id: str = typer.Option(..., "--config-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "config.bound_groups",
        explicit_payload={"ConfigId": config_id},
        region=region,
        profile=profile,
        output=output,
    )


@app.command("bound-configs")
def bound_configs(
    ctx: typer.Context,
    group_id: str = typer.Option(..., "--group-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "config.bound_configs",
        explicit_payload={"GroupId": group_id},
        region=region,
        profile=profile,
        output=output,
    )
