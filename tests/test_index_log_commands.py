from __future__ import annotations

from cls_cli.cli import app


def test_index_rebuild_create_invokes_create_rebuild_task(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        [
            "index",
            "rebuild-create",
            "--region",
            "ap-guangzhou",
            "--topic-id",
            "topic-123",
            "--start-time",
            "1710000000",
            "--end-time",
            "1710003600",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "CreateRebuildIndexTask",
            {"TopicId": "topic-123", "StartTime": 1710000000, "EndTime": 1710003600},
            "ap-guangzhou",
        )
    ]


def test_log_search_invokes_search_log_with_query_window(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        [
            "log",
            "search",
            "--region",
            "ap-guangzhou",
            "--topic-id",
            "topic-123",
            "--query",
            "status:500",
            "--start-time",
            "1710000000",
            "--end-time",
            "1710003600",
            "--limit",
            "20",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "SearchLog",
            {
                "TopicId": "topic-123",
                "QueryString": "status:500",
                "From": 1710000000000,
                "To": 1710003600000,
                "Limit": 20,
            },
            "ap-guangzhou",
        )
    ]


def test_log_histogram_uses_query_and_millisecond_window(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        [
            "log",
            "histogram",
            "--region",
            "ap-guangzhou",
            "--topic-id",
            "topic-123",
            "--query",
            "*",
            "--start-time",
            "1710000000",
            "--end-time",
            "1710003600",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "DescribeLogHistogram",
            {
                "TopicId": "topic-123",
                "Query": "*",
                "From": 1710000000000,
                "To": 1710003600000,
            },
            "ap-guangzhou",
        )
    ]


def test_log_upload_reads_jsonl(runner, cli_obj, fake_client, tmp_path):
    logs = tmp_path / "logs.jsonl"
    logs.write_text('{"level":"info","message":"ok"}\n', encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "log",
            "upload",
            "--region",
            "ap-guangzhou",
            "--topic-id",
            "topic-123",
            "--jsonl",
            str(logs),
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "UploadLog",
            {"TopicId": "topic-123", "Logs": [{"level": "info", "message": "ok"}]},
            "ap-guangzhou",
        )
    ]
