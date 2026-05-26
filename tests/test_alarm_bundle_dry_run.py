from __future__ import annotations

import json

from cls_cli.cli import app
from tests.conftest import json_output


def _write_bundle(tmp_path, data):
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps(data), encoding="utf-8")
    return bundle


def _valid_bundle():
    return {
        "name": "payment-5xx",
        "region": "ap-shanghai",
        "topic": {"mode": "existing", "logset_id": "logset-123", "topic_id": "topic-123"},
        "integration": {"mode": "existing", "web_callback_id": "callback-123"},
        "notice_content": {
            "mode": "create",
            "payload": {"Name": "content", "NoticeContents": []},
        },
        "notice": {
            "mode": "create",
            "payload": {
                "Name": "notice",
                "Type": "All",
                "WebCallbacks": [
                    {
                        "CallbackType": "WeCom",
                        "Url": "",
                        "WebCallbackId": "${integration.web_callback_id}",
                        "NoticeContentId": "${notice_content.notice_content_id}",
                    }
                ],
            },
        },
        "policy": {
            "mode": "create",
            "payload": {
                "Name": "policy",
                "AlarmNoticeIds": ["${notice.alarm_notice_id}"],
                "AlarmTargets": [
                    {
                        "LogsetId": "${topic.logset_id}",
                        "TopicId": "${topic.topic_id}",
                        "Query": "* | select count(*) as error_count",
                        "Number": 1,
                    }
                ],
                "Condition": "$1.error_count > 0",
            },
        },
    }


def test_alarm_bundle_dry_run_resolves_tokens_without_cloud_writes(
    runner, cli_obj, fake_client, tmp_path
):
    bundle = _write_bundle(tmp_path, _valid_bundle())

    result = runner.invoke(
        app, ["alarm", "bundle", "dry-run", "--bundle", f"@{bundle}"], obj=cli_obj
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == []
    data = json_output(result)["data"]
    assert data["valid"] is True
    assert data["steps"][0]["action"] == "CreateNoticeContent"
    assert data["steps"][-1]["payload"]["AlarmNoticeIds"] == ["<alarm_notice_id>"]
    assert data["steps"][-1]["payload"]["AlarmTargets"][0]["TopicId"] == "topic-123"
    assert data["rollback_preview"] == [
        {"resource": "policy", "action": "DeleteAlarm", "id": "<alarm_id>"},
        {"resource": "notice", "action": "DeleteAlarmNotice", "id": "<alarm_notice_id>"},
        {
            "resource": "notice_content",
            "action": "DeleteNoticeContent",
            "id": "<notice_content_id>",
        },
    ]


def test_alarm_bundle_dry_run_reports_unresolved_token(runner, tmp_path):
    data = _valid_bundle()
    data["notice"] = {"mode": "skip"}
    bundle = _write_bundle(tmp_path, data)

    result = runner.invoke(app, ["alarm", "bundle", "dry-run", "--bundle", f"@{bundle}"])

    assert result.exit_code == 1
    payload = json_output(result)["data"]
    assert payload["valid"] is False
    assert "unresolved bundle token: ${notice.alarm_notice_id}" in payload["issues"][0]["message"]


def test_alarm_bundle_dry_run_reports_invalid_payload(runner, tmp_path):
    data = _valid_bundle()
    del data["policy"]["payload"]["AlarmTargets"]
    bundle = _write_bundle(tmp_path, data)

    result = runner.invoke(app, ["alarm", "bundle", "dry-run", "--bundle", f"@{bundle}"])

    assert result.exit_code == 1
    payload = json_output(result)["data"]
    assert payload["valid"] is False
    assert payload["steps"][-1]["valid"] is False
    assert "payload validation failed" in payload["issues"][-1]["message"]
