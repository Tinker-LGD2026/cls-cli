from __future__ import annotations

from cls_cli.cli import app
from tests.conftest import json_output


def test_profile_set_and_show_do_not_expose_secret(runner, cli_obj):
    set_result = runner.invoke(
        app,
        [
            "profile",
            "set",
            "dev",
            "--region",
            "ap-guangzhou",
            "--secret-id-env",
            "TENCENTCLOUD_SECRET_ID",
            "--secret-key-env",
            "TENCENTCLOUD_SECRET_KEY",
        ],
        obj=cli_obj,
    )
    assert set_result.exit_code == 0, set_result.stdout

    show_result = runner.invoke(app, ["profile", "show", "dev"], obj=cli_obj)

    assert show_result.exit_code == 0, show_result.stdout
    data = json_output(show_result)["data"]
    assert data["region"] == "ap-guangzhou"
    assert "AKID" not in show_result.stdout
    assert data["secret_id_env"] == "TENCENTCLOUD_SECRET_ID"


def test_command_uses_profile_region(runner, cli_obj, fake_client):
    runner.invoke(app, ["profile", "set", "dev", "--region", "ap-shanghai"], obj=cli_obj)

    result = runner.invoke(app, ["logset", "list", "--profile", "dev"], obj=cli_obj)

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [("DescribeLogsets", {}, "ap-shanghai")]
