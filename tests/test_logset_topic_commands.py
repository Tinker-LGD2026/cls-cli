from __future__ import annotations

from cls_cli.cli import app
from tests.conftest import json_output


def test_logset_list_invokes_describe_logsets(runner, cli_obj, fake_client):
    result = runner.invoke(app, ["logset", "list", "--region", "ap-guangzhou"], obj=cli_obj)

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [("DescribeLogsets", {}, "ap-guangzhou")]
    assert json_output(result)["data"]["Response"]["Action"] == "DescribeLogsets"


def test_logset_get_filters_by_logset_id(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        ["logset", "get", "--region", "ap-guangzhou", "--logset-id", "logset-123"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "DescribeLogsets",
            {"Filters": [{"Key": "logsetId", "Values": ["logset-123"]}]},
            "ap-guangzhou",
        )
    ]


def test_topic_list_filters_by_logset_id(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        ["topic", "list", "--region", "ap-guangzhou", "--logset-id", "logset-123"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "DescribeTopics",
            {"Filters": [{"Key": "logsetId", "Values": ["logset-123"]}]},
            "ap-guangzhou",
        )
    ]


def test_topic_get_filters_by_topic_id(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        ["topic", "get", "--region", "ap-guangzhou", "--topic-id", "topic-123"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "DescribeTopics",
            {"Filters": [{"Key": "topicId", "Values": ["topic-123"]}]},
            "ap-guangzhou",
        )
    ]


def test_topic_create_merges_payload_file_and_explicit_logset_id(
    runner, cli_obj, fake_client, tmp_path
):
    payload = tmp_path / "topic.json"
    payload.write_text('{"TopicName":"app","PartitionCount":1}', encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "topic",
            "create",
            "--region",
            "ap-guangzhou",
            "--logset-id",
            "logset-123",
            "--payload",
            f"@{payload}",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "CreateTopic",
            {"TopicName": "app", "PartitionCount": 1, "LogsetId": "logset-123"},
            "ap-guangzhou",
        )
    ]


def test_logset_delete_requires_force(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        ["logset", "delete", "--region", "ap-guangzhou", "--logset-id", "logset-123"],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    assert fake_client.calls == []
    error = json_output(result)["error"]
    assert error["code"] == "CONFIRMATION_REQUIRED"


def test_logset_delete_with_force_invokes_delete(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        [
            "logset",
            "delete",
            "--region",
            "ap-guangzhou",
            "--logset-id",
            "logset-123",
            "--force",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [("DeleteLogset", {"LogsetId": "logset-123"}, "ap-guangzhou")]
