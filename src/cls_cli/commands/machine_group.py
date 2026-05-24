from __future__ import annotations

import typer

from cls_cli.core.execution import run_action
from cls_cli.core.input import split_csv

app = typer.Typer(no_args_is_help=True, help="Manage CLS machine groups.")


@app.command("list")
def list_machine_groups(
    ctx: typer.Context,
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(ctx, "machine_group.list", region=region, profile=profile, output=output)


@app.command("get")
def get_machine_group(
    ctx: typer.Context,
    group_id: str = typer.Option(..., "--group-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "machine_group.get",
        explicit_payload={"GroupId": group_id},
        region=region,
        profile=profile,
        output=output,
    )


@app.command("create")
def create_machine_group(
    ctx: typer.Context,
    group_name: str | None = typer.Option(None, "--group-name"),
    machine_group_type: str | None = typer.Option(None, "--type"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "machine_group.create",
        explicit_payload={"GroupName": group_name, "MachineGroupType": machine_group_type},
        payload=payload,
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("update")
def update_machine_group(
    ctx: typer.Context,
    group_id: str = typer.Option(..., "--group-id"),
    group_name: str | None = typer.Option(None, "--group-name"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "machine_group.update",
        explicit_payload={"GroupId": group_id, "GroupName": group_name},
        payload=payload,
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("delete")
def delete_machine_group(
    ctx: typer.Context,
    group_id: str = typer.Option(..., "--group-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    run_action(
        ctx,
        "machine_group.delete",
        explicit_payload={"GroupId": group_id},
        region=region,
        profile=profile,
        output=output,
        force=force,
        dry_run=dry_run,
    )


@app.command("machines")
def machines(
    ctx: typer.Context,
    group_id: str = typer.Option(..., "--group-id"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    run_action(
        ctx,
        "machine_group.machines",
        explicit_payload={"GroupId": group_id},
        region=region,
        profile=profile,
        output=output,
    )


@app.command("add-info")
def add_info(
    ctx: typer.Context,
    group_id: str = typer.Option(..., "--group-id"),
    ips: str | None = typer.Option(None, "--ips"),
    labels: str | None = typer.Option(None, "--labels"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    explicit: dict[str, object] = {"GroupId": group_id}
    values = split_csv(ips) or split_csv(labels)
    if values is not None:
        explicit["MachineGroupType"] = {"Type": "ip" if ips else "label", "Values": values}
    run_action(
        ctx,
        "machine_group.add_info",
        explicit_payload=explicit,
        payload=payload,
        region=region,
        profile=profile,
        output=output,
        dry_run=dry_run,
    )


@app.command("delete-info")
def delete_info(
    ctx: typer.Context,
    group_id: str = typer.Option(..., "--group-id"),
    ips: str | None = typer.Option(None, "--ips"),
    labels: str | None = typer.Option(None, "--labels"),
    payload: str | None = typer.Option(None, "--payload"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    explicit: dict[str, object] = {"GroupId": group_id}
    values = split_csv(ips) or split_csv(labels)
    if values is not None:
        explicit["MachineGroupType"] = {"Type": "ip" if ips else "label", "Values": values}
    run_action(
        ctx,
        "machine_group.delete_info",
        explicit_payload=explicit,
        payload=payload,
        region=region,
        profile=profile,
        output=output,
        force=force,
        dry_run=dry_run,
    )
