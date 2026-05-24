from __future__ import annotations

import typer

from cls_cli.core.alarm_bundle import validate_alarm_bundle
from cls_cli.core.errors import CliError
from cls_cli.core.input import load_json_payload
from cls_cli.core.output import emit_data, emit_error

app = typer.Typer(no_args_is_help=True, help="Validate composed alarm resources.")


@app.command("bundle")
def validate_bundle(
    policy: str | None = typer.Option(None, "--policy"),
    notice_content: str | None = typer.Option(None, "--notice-content"),
    notice: str | None = typer.Option(None, "--notice"),
    integration: str | None = typer.Option(None, "--integration"),
    output: str = typer.Option("json", "--output"),
) -> None:
    try:
        result = validate_alarm_bundle(
            policy=load_json_payload(policy) if policy else None,
            notice_content=load_json_payload(notice_content) if notice_content else None,
            notice=load_json_payload(notice) if notice else None,
            integration=load_json_payload(integration) if integration else None,
        )
        emit_data(result, output)
        if not result["valid"]:
            raise typer.Exit(1)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc
