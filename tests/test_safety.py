from __future__ import annotations

from cls_cli.cli import app
from tests.conftest import json_output


def test_dry_run_returns_payload_without_calling_cloud(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        [
            "topic",
            "delete",
            "--region",
            "ap-guangzhou",
            "--topic-id",
            "topic-123",
            "--force",
            "--dry-run",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == []
    assert json_output(result)["data"] == {
        "dry_run": True,
        "action": "DeleteTopic",
        "region": "ap-guangzhou",
        "payload": {"TopicId": "topic-123"},
    }
