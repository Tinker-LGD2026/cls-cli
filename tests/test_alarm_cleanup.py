from __future__ import annotations

from cls_cli.cli import app
from cls_cli.core.alarm_cleanup import AlarmCleanupOptions, run_alarm_cleanup
from tests.conftest import FakeClsClient, json_output


def _cleanup_responses() -> dict[str, dict[str, object]]:
    return {
        "DescribeAlarms": {
            "Response": {
                "Alarms": [
                    {"AlarmId": "alarm-1", "Name": "cls-cli-case-alarm", "CreateTime": 1000},
                    {"AlarmId": "alarm-prod", "Name": "prod-alarm", "CreateTime": 1000},
                ]
            }
        },
        "DescribeAlarmNotices": {
            "Response": {
                "AlarmNotices": [
                    {
                        "AlarmNoticeId": "notice-1",
                        "Name": "cls-cli-case-notice",
                        "CreateTime": 1000,
                    }
                ]
            }
        },
        "DescribeWebCallbacks": {
            "Response": {
                "WebCallbacks": [
                    {
                        "WebCallbackId": "callback-1",
                        "Name": "cls-cli-case-callback",
                        "CreateTime": 1000,
                    }
                ]
            }
        },
        "DescribeNoticeContents": {
            "Response": {
                "NoticeContents": [
                    {
                        "NoticeContentId": "content-1",
                        "Name": "cls-cli-case-content",
                        "CreateTime": 1000,
                    }
                ]
            }
        },
        "DescribeLogsets": {
            "Response": {
                "Logsets": [
                    {"LogsetId": "logset-1", "LogsetName": "cls-cli-case", "CreateTime": 1000}
                ]
            }
        },
        "DescribeTopics": {
            "Response": {
                "Topics": [
                    {"TopicId": "topic-1", "TopicName": "cls-cli-case", "CreateTime": 1000}
                ]
            }
        },
    }


def test_alarm_cleanup_dry_run_discovers_prefixed_resources_without_deleting():
    client = FakeClsClient(responses=_cleanup_responses())

    result = run_alarm_cleanup(
        client,
        "ap-shanghai",
        AlarmCleanupOptions(prefix="cls-cli-", dry_run=True),
    )

    assert result["status"] == "DRY_RUN"
    assert [item["type"] for item in result["resources"]] == [
        "alarm",
        "alarm_notice",
        "web_callback",
        "notice_content",
        "index",
        "topic",
        "logset",
    ]
    assert [call[0] for call in client.calls] == [
        "DescribeAlarms",
        "DescribeAlarmNotices",
        "DescribeWebCallbacks",
        "DescribeNoticeContents",
        "DescribeLogsets",
        "DescribeTopics",
    ]
    assert result["summary"] == {"matched": 7, "deleted": 0, "failed": 0, "skipped": 0}


def test_alarm_cleanup_deletes_in_dependency_order():
    client = FakeClsClient(responses=_cleanup_responses())

    result = run_alarm_cleanup(
        client,
        "ap-shanghai",
        AlarmCleanupOptions(prefix="cls-cli-", force=True),
    )

    assert result["status"] == "PASS"
    delete_calls = [call for call in client.calls if call[0].startswith("Delete")]
    assert delete_calls == [
        ("DeleteAlarm", {"AlarmId": "alarm-1"}, "ap-shanghai"),
        ("DeleteAlarmNotice", {"AlarmNoticeId": "notice-1"}, "ap-shanghai"),
        ("DeleteWebCallback", {"WebCallbackId": "callback-1"}, "ap-shanghai"),
        ("DeleteNoticeContent", {"NoticeContentId": "content-1"}, "ap-shanghai"),
        ("DeleteIndex", {"TopicId": "topic-1"}, "ap-shanghai"),
        ("DeleteTopic", {"TopicId": "topic-1"}, "ap-shanghai"),
        ("DeleteLogset", {"LogsetId": "logset-1"}, "ap-shanghai"),
    ]
    assert result["summary"] == {"matched": 7, "deleted": 7, "failed": 0, "skipped": 0}


def test_alarm_cleanup_older_than_skips_fresh_resources():
    responses = _cleanup_responses()
    responses["DescribeAlarms"] = {
        "Response": {
            "Alarms": [
                {"AlarmId": "alarm-old", "Name": "cls-cli-old", "CreateTime": 1000},
                {"AlarmId": "alarm-fresh", "Name": "cls-cli-fresh", "CreateTime": 9500},
            ]
        }
    }
    client = FakeClsClient(responses=responses)

    result = run_alarm_cleanup(
        client,
        "ap-shanghai",
        AlarmCleanupOptions(prefix="cls-cli-", older_than_seconds=3600, dry_run=True),
        now=lambda: 10_000,
    )

    alarm_ids = [item["id"] for item in result["resources"] if item["type"] == "alarm"]
    assert alarm_ids == ["alarm-old"]
    assert result["summary"]["skipped"] == 1


def test_alarm_cleanup_cli_requires_force_without_dry_run(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        ["alarm", "verify", "cleanup", "--region", "ap-shanghai", "--prefix", "cls-cli-"],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    assert json_output(result)["error"]["code"] == "CONFIRMATION_REQUIRED"
    assert fake_client.calls == []


def test_alarm_cleanup_cli_dry_run_outputs_plan(runner, cli_obj, fake_client):
    fake_client.responses = _cleanup_responses()

    result = runner.invoke(
        app,
        [
            "alarm",
            "verify",
            "cleanup",
            "--region",
            "ap-shanghai",
            "--prefix",
            "cls-cli-",
            "--dry-run",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    data = json_output(result)["data"]
    assert data["status"] == "DRY_RUN"
    assert data["summary"]["matched"] == 7
    assert not any(call[0].startswith("Delete") for call in fake_client.calls)
