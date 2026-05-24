from __future__ import annotations

from cls_cli.cli import app
from cls_cli.core.errors import ClsApiError
from tests.conftest import json_output


def test_api_error_is_rendered_as_stable_json(runner, cli_obj, fake_client):
    fake_client.error = ClsApiError(
        code="AuthFailure.SecretIdNotFound",
        message="secret id not found",
        request_id="req-error",
        action="DescribeLogsets",
        region="ap-guangzhou",
        retryable=False,
    )

    result = runner.invoke(app, ["logset", "list", "--region", "ap-guangzhou"], obj=cli_obj)

    assert result.exit_code == 2
    assert json_output(result) == {
        "error": {
            "code": "AuthFailure.SecretIdNotFound",
            "message": "secret id not found",
            "request_id": "req-error",
            "action": "DescribeLogsets",
            "region": "ap-guangzhou",
            "retryable": False,
        }
    }


def test_table_output_contains_action_for_humans(runner, cli_obj):
    result = runner.invoke(
        app,
        ["logset", "list", "--region", "ap-guangzhou", "--output", "table"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert "DescribeLogsets" in result.stdout
