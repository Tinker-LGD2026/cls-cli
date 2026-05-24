from __future__ import annotations

import typer

from cls_cli.core.config import Profile, store_from_obj
from cls_cli.core.errors import CliError
from cls_cli.core.output import emit_data, emit_error

app = typer.Typer(no_args_is_help=True, help="Manage CLI profiles.")


@app.command("list")
def list_profiles(ctx: typer.Context, output: str = typer.Option("json", "--output")) -> None:
    try:
        store = store_from_obj(ctx.obj if isinstance(ctx.obj, dict) else None)
        emit_data([profile.public_dict() for profile in store.list_profiles()], output)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("show")
def show_profile(
    ctx: typer.Context, name: str, output: str = typer.Option("json", "--output")
) -> None:
    try:
        store = store_from_obj(ctx.obj if isinstance(ctx.obj, dict) else None)
        profile = store.get_profile(name)
        emit_data(profile.public_dict() if profile else {}, output)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("set")
def set_profile(
    ctx: typer.Context,
    name: str,
    region: str | None = typer.Option(None, "--region"),
    output: str | None = typer.Option(None, "--output-format"),
    secret_id_env: str | None = typer.Option(None, "--secret-id-env"),
    secret_key_env: str | None = typer.Option(None, "--secret-key-env"),
) -> None:
    try:
        store = store_from_obj(ctx.obj if isinstance(ctx.obj, dict) else None)
        profile = Profile(
            name=name,
            region=region,
            output=output,
            secret_id_env=secret_id_env,
            secret_key_env=secret_key_env,
        )
        store.set_profile(profile)
        emit_data({"saved": True, "profile": profile.public_dict()})
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("use")
def use_profile(ctx: typer.Context, name: str) -> None:
    try:
        store = store_from_obj(ctx.obj if isinstance(ctx.obj, dict) else None)
        store.get_profile(name)
        data = store.load()
        data["current_profile"] = name
        store.save(data)
        emit_data({"current_profile": name})
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("delete")
def delete_profile(
    ctx: typer.Context, name: str, force: bool = typer.Option(False, "--force")
) -> None:
    try:
        if not force:
            from cls_cli.core.errors import ConfirmationRequired

            raise ConfirmationRequired("delete profile requires --force")
        store = store_from_obj(ctx.obj if isinstance(ctx.obj, dict) else None)
        store.delete_profile(name)
        emit_data({"deleted": True, "profile": name})
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc
