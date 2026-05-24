from __future__ import annotations

from cls_cli.cli import app


def test_root_help_lists_resource_command_groups(runner):
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in [
        "profile",
        "logset",
        "topic",
        "machine-group",
        "config",
        "index",
        "log",
        "alarm",
        "ai",
    ]:
        assert command in result.stdout


def test_resource_help_is_available(runner):
    for command in ["logset", "topic", "machine-group", "config", "index", "log", "alarm", "ai"]:
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0, result.stdout
