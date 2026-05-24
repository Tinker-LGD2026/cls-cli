from __future__ import annotations

from cls_cli.cli import app


def test_alarm_policy_list_accepts_payload_filters(runner, cli_obj, fake_client, tmp_path):
    payload = tmp_path / "filters.json"
    payload.write_text(
        '{"Filters":[{"Name":"topicId","Values":["topic-123"]}],"Offset":0,"Limit":20}',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["alarm", "policy", "list", "--region", "ap-shanghai", "--payload", f"@{payload}"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "DescribeAlarms",
            {"Filters": [{"Name": "topicId", "Values": ["topic-123"]}], "Offset": 0, "Limit": 20},
            "ap-shanghai",
        )
    ]


def test_alarm_notice_list_accepts_payload_filters(runner, cli_obj, fake_client, tmp_path):
    payload = tmp_path / "filters.json"
    payload.write_text('{"Offset":0,"Limit":50}', encoding="utf-8")

    result = runner.invoke(
        app,
        ["alarm", "notice", "list", "--region", "ap-shanghai", "--payload", f"@{payload}"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        ("DescribeAlarmNotices", {"Offset": 0, "Limit": 50}, "ap-shanghai")
    ]


def test_alarm_policy_get_filters_by_alarm_id(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        ["alarm", "policy", "get", "--region", "ap-shanghai", "--alarm-id", "alarm-123"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "DescribeAlarms",
            {"Filters": [{"Name": "alarmId", "Values": ["alarm-123"]}], "Offset": 0, "Limit": 1},
            "ap-shanghai",
        )
    ]
