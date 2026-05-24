from __future__ import annotations

import typer

from cls_cli.core.execution import run_action

app = typer.Typer(no_args_is_help=True, help="Manage CLS logsets.")


@app.command("list")
def list_logsets(
    ctx: typer.Context,
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(ctx, "logset.list", region=region, profile=profile, output=output)


@app.command("get")
def get_logset(
    ctx: typer.Context,
    logset_id: str = typer.Option(..., "--logset-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "logset.get",
        explicit_payload={"Filters": [{"Key": "logsetId", "Values": [logset_id]}]},
        region=region,
        profile=profile,
        output=output,
    )


@app.command("create")
def create_logset(
    ctx: typer.Context,
    logset_name: str | None = typer.Option(None, "--logset-name"),
    tags: str | None = typer.Option(None, "--tags"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "logset.create",
        explicit_payload={"LogsetName": logset_name, "Tags": tags},
        payload=payload,
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("update")
def update_logset(
    ctx: typer.Context,
    logset_id: str = typer.Option(..., "--logset-id"),
    logset_name: str | None = typer.Option(None, "--logset-name"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "logset.update",
        explicit_payload={"LogsetId": logset_id, "LogsetName": logset_name},
        payload=payload,
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("delete")
def delete_logset(
    ctx: typer.Context,
    logset_id: str = typer.Option(..., "--logset-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "logset.delete",
        explicit_payload={"LogsetId": logset_id},
        region=region,
        profile=profile,
        output=output,
        force=force,
        dry_run=dry_run,
    )
