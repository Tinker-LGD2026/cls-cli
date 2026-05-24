from __future__ import annotations

import typer

from cls_cli import __version__
from cls_cli.commands import (
    ai,
    alarm,
    collection_config,
    index,
    log,
    logset,
    machine_group,
    profile,
    topic,
)

app = typer.Typer(
    name="cls",
    no_args_is_help=True,
    help="Agent-friendly command line tool for Tencent Cloud CLS.",
    add_completion=False,
    pretty_exceptions_enable=False,
)

app.add_typer(profile.app, name="profile")
app.add_typer(logset.app, name="logset")
app.add_typer(topic.app, name="topic")
app.add_typer(machine_group.app, name="machine-group")
app.add_typer(collection_config.app, name="config")
app.add_typer(index.app, name="index")
app.add_typer(log.app, name="log")
app.add_typer(alarm.app, name="alarm")
app.add_typer(ai.app, name="ai")


@app.callback()
def callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
) -> None:
    ctx.ensure_object(dict)
    if version:
        typer.echo(__version__)
        raise typer.Exit()


def main() -> None:
    app()
