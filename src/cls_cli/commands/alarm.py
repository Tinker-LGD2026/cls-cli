from __future__ import annotations

import typer

from cls_cli.commands import alarm_bundle as alarm_bundle_commands
from cls_cli.commands import alarm_debug as alarm_debug_commands
from cls_cli.commands import alarm_discover as alarm_discover_commands
from cls_cli.commands import alarm_history as alarm_history_commands
from cls_cli.commands import alarm_integration as alarm_integration_commands
from cls_cli.commands import alarm_notice as alarm_notice_commands
from cls_cli.commands import alarm_policy as alarm_policy_commands
from cls_cli.commands import alarm_template as alarm_template_commands
from cls_cli.commands import alarm_validate as alarm_validate_commands
from cls_cli.commands import alarm_verify as alarm_verify_commands
from cls_cli.core.execution import run_action

app = typer.Typer(no_args_is_help=True, help="Manage CLS alarms.")
policy_app = alarm_policy_commands.app
notice_app = alarm_notice_commands.app
shield_app = typer.Typer(no_args_is_help=True, help="Manage alarm shields.")
content_app = typer.Typer(no_args_is_help=True, help="Manage notice content templates.")
callback_app = typer.Typer(no_args_is_help=True, help="Manage web callbacks.")
integration_app = alarm_integration_commands.app
discover_app = alarm_discover_commands.app
bundle_app = alarm_bundle_commands.app
template_app = alarm_template_commands.app
debug_app = alarm_debug_commands.app
verify_app = alarm_verify_commands.app
validate_app = alarm_validate_commands.app

app.add_typer(policy_app, name="policy")
app.add_typer(notice_app, name="notice")
app.add_typer(shield_app, name="shield")
app.add_typer(content_app, name="content")
app.add_typer(callback_app, name="callback")
app.add_typer(integration_app, name="integration")
app.add_typer(discover_app, name="discover")
app.add_typer(bundle_app, name="bundle")
app.add_typer(template_app, name="template")
app.add_typer(debug_app, name="debug")
app.add_typer(verify_app, name="verify")
app.add_typer(validate_app, name="validate")
alarm_history_commands.register(app)


def _crud(
    group: typer.Typer,
    key_prefix: str,
    id_field: str,
    id_option: str,
    *,
    id_filter_name: str | None = None,
) -> None:
    @group.command("list")
    def list_items(
        ctx: typer.Context,
        payload: str | None = typer.Option(None, "--payload"),
        region: str | None = typer.Option(None, "--region"),
        profile: str | None = typer.Option(None, "--profile"),
        output: str = typer.Option("json", "--output"),
    ) -> None:
        run_action(
            ctx,
            f"{key_prefix}.list",
            payload=payload,
            region=region,
            profile=profile,
            output=output,
        )

    if id_filter_name is not None:

        @group.command("get")
        def get_item(
            ctx: typer.Context,
            item_id: str = typer.Option(..., id_option),
            region: str | None = typer.Option(None, "--region"),
            profile: str | None = typer.Option(None, "--profile"),
            output: str = typer.Option("json", "--output"),
        ) -> None:
            run_action(
                ctx,
                f"{key_prefix}.list",
                explicit_payload={
                    "Filters": [{"Name": id_filter_name, "Values": [item_id]}],
                    "Offset": 0,
                    "Limit": 1,
                },
                region=region,
                profile=profile,
                output=output,
            )

    @group.command("create")
    def create_item(
        ctx: typer.Context,
        payload: str = typer.Option(..., "--payload"),
        region: str | None = typer.Option(None, "--region"),
        profile: str | None = typer.Option(None, "--profile"),
        output: str = typer.Option("json", "--output"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        skip_validation: bool = typer.Option(False, "--skip-validation"),
    ) -> None:
        run_action(
            ctx,
            f"{key_prefix}.create",
            payload=payload,
            region=region,
            profile=profile,
            output=output,
            dry_run=dry_run,
            skip_validation=skip_validation,
        )

    @group.command("update")
    def update_item(
        ctx: typer.Context,
        item_id: str = typer.Option(..., id_option),
        payload: str | None = typer.Option(None, "--payload"),
        region: str | None = typer.Option(None, "--region"),
        profile: str | None = typer.Option(None, "--profile"),
        output: str = typer.Option("json", "--output"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        skip_validation: bool = typer.Option(False, "--skip-validation"),
    ) -> None:
        run_action(
            ctx,
            f"{key_prefix}.update",
            explicit_payload={id_field: item_id},
            payload=payload,
            region=region,
            profile=profile,
            output=output,
            dry_run=dry_run,
            skip_validation=skip_validation,
        )

    @group.command("delete")
    def delete_item(
        ctx: typer.Context,
        item_id: str = typer.Option(..., id_option),
        region: str | None = typer.Option(None, "--region"),
        profile: str | None = typer.Option(None, "--profile"),
        output: str = typer.Option("json", "--output"),
        force: bool = typer.Option(False, "--force"),
        dry_run: bool = typer.Option(False, "--dry-run"),
    ) -> None:
        run_action(
            ctx,
            f"{key_prefix}.delete",
            explicit_payload={id_field: item_id},
            region=region,
            profile=profile,
            output=output,
            force=force,
            dry_run=dry_run,
        )


_crud(policy_app, "alarm.policy", "AlarmId", "--alarm-id", id_filter_name="alarmId")
_crud(notice_app, "alarm.notice", "AlarmNoticeId", "--notice-id")
_crud(shield_app, "alarm.shield", "TaskId", "--shield-id")
_crud(content_app, "alarm.content", "NoticeContentId", "--content-id")
_crud(callback_app, "alarm.callback", "WebCallbackId", "--callback-id")
