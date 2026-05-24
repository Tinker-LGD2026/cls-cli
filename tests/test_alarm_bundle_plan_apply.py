from __future__ import annotations

import json

from cls_cli.cli import app
from tests.conftest import json_output


def test_alarm_bundle_plan_supports_existing_integration_and_created_children(runner, tmp_path):
    bundle = tmp_path / "bundle.json"
    bundle.write_text(
        json.dumps(
            {
                "name": "payment-5xx",
                "region": "ap-shanghai",
                "topic": {
                    "mode": "existing",
                    "logset_id": "logset-123",
                    "topic_id": "topic-123",
                },
                "integration": {"mode": "existing", "web_callback_id": "callback-123"},
                "notice_content": {
                    "mode": "create",
                    "payload": {"Name": "content", "NoticeContents": []},
                },
                "notice": {
                    "mode": "create",
                    "payload": {"Name": "notice", "Type": "All", "WebCallbacks": []},
                },
                "policy": {
                    "mode": "create",
                    "payload": {
                        "Name": "policy",
                        "AlarmTargets": [
                            {"Query": "* | select count(*) as error_count", "Number": 1}
                        ],
                        "Condition": "$1.error_count > 0",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["alarm", "bundle", "plan", "--bundle", f"@{bundle}"])

    assert result.exit_code == 0, result.stdout
    data = json_output(result)["data"]
    assert data["valid"] is True
    assert [step["resource"] for step in data["steps"]] == [
        "topic",
        "integration",
        "notice_content",
        "notice",
        "policy",
    ]
    assert [step["mode"] for step in data["steps"]] == [
        "existing",
        "existing",
        "create",
        "create",
        "create",
    ]


def test_alarm_bundle_plan_maps_topic_create_to_create_topic(runner, tmp_path):
    bundle = tmp_path / "bundle.json"
    bundle.write_text(
        json.dumps(
            {
                "topic": {
                    "mode": "create",
                    "payload": {"LogsetId": "logset-123", "TopicName": "demo"},
                }
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["alarm", "bundle", "plan", "--bundle", f"@{bundle}"])

    assert result.exit_code == 0, result.stdout
    data = json_output(result)["data"]
    assert data["steps"] == [
        {"resource": "topic", "mode": "create", "action": "CreateTopic"}
    ]



def test_alarm_bundle_apply_injects_ids_and_returns_manifest(
    runner, cli_obj, fake_client, tmp_path
):
    fake_client.responses = {
        "CreateNoticeContent": {
            "Response": {"NoticeContentId": "content-123", "RequestId": "req-content"}
        },
        "CreateAlarmNotice": {
            "Response": {"AlarmNoticeId": "notice-123", "RequestId": "req-notice"}
        },
        "CreateAlarm": {"Response": {"AlarmId": "alarm-123", "RequestId": "req-alarm"}},
    }
    bundle = tmp_path / "bundle.json"
    bundle.write_text(
        json.dumps(
            {
                "name": "payment-5xx",
                "region": "ap-shanghai",
                "topic": {
                    "mode": "existing",
                    "logset_id": "logset-123",
                    "topic_id": "topic-123",
                },
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
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["alarm", "bundle", "apply", "--bundle", f"@{bundle}", "--confirm-real-write"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    data = json_output(result)["data"]
    assert data["status"] == "PASS"
    assert data["manifest"]["resources"]["notice_content"]["notice_content_id"] == "content-123"
    assert data["manifest"]["resources"]["notice"]["alarm_notice_id"] == "notice-123"
    assert data["manifest"]["resources"]["policy"]["alarm_id"] == "alarm-123"
    notice_payload = fake_client.calls[1][1]
    policy_payload = fake_client.calls[2][1]
    assert notice_payload["WebCallbacks"][0]["WebCallbackId"] == "callback-123"
    assert notice_payload["WebCallbacks"][0]["NoticeContentId"] == "content-123"
    assert policy_payload["AlarmNoticeIds"] == ["notice-123"]
    assert policy_payload["AlarmTargets"][0]["TopicId"] == "topic-123"


def test_alarm_bundle_apply_can_create_topic_and_inject_topic_id(
    runner, cli_obj, fake_client, tmp_path
):
    fake_client.responses = {
        "CreateTopic": {"Response": {"TopicId": "topic-created", "RequestId": "req-topic"}},
        "CreateAlarm": {"Response": {"AlarmId": "alarm-created", "RequestId": "req-alarm"}},
    }
    bundle = tmp_path / "bundle.json"
    bundle.write_text(
        json.dumps(
            {
                "region": "ap-shanghai",
                "topic": {
                    "mode": "create",
                    "payload": {"LogsetId": "logset-123", "TopicName": "demo"},
                },
                "policy": {
                    "mode": "create",
                    "payload": {
                        "Name": "policy",
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
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["alarm", "bundle", "apply", "--bundle", f"@{bundle}", "--confirm-real-write"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert [call[0] for call in fake_client.calls] == ["CreateTopic", "CreateAlarm"]
    assert fake_client.calls[1][1]["AlarmTargets"][0]["TopicId"] == "topic-created"
    topic_manifest = json_output(result)["data"]["manifest"]["resources"]["topic"]
    assert topic_manifest["topic_id"] == "topic-created"


def test_alarm_bundle_apply_failure_rolls_back_created_resources(
    runner, cli_obj, fake_client, tmp_path
):
    fake_client.responses = {
        "CreateNoticeContent": {
            "Response": {"NoticeContentId": "content-123", "RequestId": "req-content"}
        },
        "CreateAlarmNotice": {
            "Response": {"AlarmNoticeId": "notice-123", "RequestId": "req-notice"}
        },
    }

    def failing_invoke(action, payload, region):
        fake_client.calls.append((action, payload, region))
        if action == "CreateAlarm":
            raise RuntimeError("create alarm failed")
        return fake_client.responses.get(action, {"Response": {"RequestId": f"req-{action}"}})

    fake_client.invoke = failing_invoke
    bundle = tmp_path / "bundle.json"
    bundle.write_text(
        json.dumps(
            {
                "region": "ap-shanghai",
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
                                "CallbackType": "Http",
                                "Url": "https://example.com/hook",
                                "NoticeContentId": "${notice_content.notice_content_id}",
                                "Method": "POST",
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
                            {"Query": "* | select count(*) as error_count", "Number": 1}
                        ],
                        "Condition": "$1.error_count > 0",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["alarm", "bundle", "apply", "--bundle", f"@{bundle}", "--confirm-real-write"],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    assert [call[0] for call in fake_client.calls] == [
        "CreateNoticeContent",
        "CreateAlarmNotice",
        "CreateAlarm",
        "DeleteAlarmNotice",
        "DeleteNoticeContent",
    ]
    assert json_output(result)["data"]["status"] == "FAIL"


def test_alarm_bundle_status_reports_manifest_resources(runner, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"resources": {"policy": {"mode": "create", "alarm_id": "alarm-123"}}}),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["alarm", "bundle", "status", "--manifest", f"@{manifest}"])

    assert result.exit_code == 0, result.stdout
    data = json_output(result)["data"]
    assert data["valid"] is True
    assert data["resources"] == {"policy": {"mode": "create", "alarm_id": "alarm-123"}}


def test_alarm_bundle_rollback_reports_missing_created_resource_id(runner, cli_obj, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"resources": {"policy": {"mode": "create"}}}),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "alarm",
            "bundle",
            "rollback",
            "--manifest",
            f"@{manifest}",
            "--region",
            "ap-shanghai",
            "--force",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    assert json_output(result)["data"]["status"] == "PARTIAL"
    assert json_output(result)["data"]["rollback"] == [
        {"resource": "policy", "id": None, "status": "failed", "error": "missing alarm_id"}
    ]


def test_alarm_bundle_rollback_deletes_created_resources_in_reverse_order(
    runner, cli_obj, fake_client, tmp_path
):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "resources": {
                    "integration": {"mode": "existing", "web_callback_id": "callback-123"},
                    "notice_content": {"mode": "create", "notice_content_id": "content-123"},
                    "notice": {"mode": "create", "alarm_notice_id": "notice-123"},
                    "policy": {"mode": "create", "alarm_id": "alarm-123"},
                }
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "alarm",
            "bundle",
            "rollback",
            "--manifest",
            f"@{manifest}",
            "--region",
            "ap-shanghai",
            "--force",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert [call[0] for call in fake_client.calls] == [
        "DeleteAlarm",
        "DeleteAlarmNotice",
        "DeleteNoticeContent",
    ]
    assert fake_client.calls[0][1] == {"AlarmId": "alarm-123"}
    assert fake_client.calls[1][1] == {"AlarmNoticeId": "notice-123"}
    assert fake_client.calls[2][1] == {"NoticeContentId": "content-123"}


def test_alarm_bundle_apply_does_not_expose_integration_secrets_in_manifest(
    runner, cli_obj, fake_client, tmp_path
):
    bundle = tmp_path / "bundle.json"
    bundle.write_text(
        json.dumps(
            {
                "region": "ap-shanghai",
                "integration": {
                    "mode": "update",
                    "web_callback_id": "callback-123",
                    "payload": {
                        "Name": "hook",
                        "Type": "Http",
                        "Webhook": "https://callback.example.com/hook",
                        "Key": "test-signing-key",
                        "Method": "POST",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["alarm", "bundle", "apply", "--bundle", f"@{bundle}", "--confirm-real-write"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    raw = result.stdout
    assert "private-token" not in raw
    assert "test-signing-key" not in raw
    integration = json_output(result)["data"]["manifest"]["resources"]["integration"]
    assert "payload" not in integration
    assert integration == {"mode": "update", "web_callback_id": "callback-123"}


def test_alarm_bundle_status_redacts_sensitive_manifest_payload(runner, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "resources": {
                    "integration": {
                        "mode": "update",
                        "web_callback_id": "callback-123",
                        "payload": {
                            "Webhook": "https://callback.example.com/hook",
                            "Key": "test-signing-key",
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["alarm", "bundle", "status", "--manifest", f"@{manifest}"])

    assert result.exit_code == 0, result.stdout
    raw = result.stdout
    assert "private-token" not in raw
    assert "test-signing-key" not in raw


def test_alarm_bundle_apply_preflights_unresolved_tokens_before_cloud_writes(
    runner, cli_obj, fake_client, tmp_path
):
    bundle = tmp_path / "bundle.json"
    bundle.write_text(
        json.dumps(
            {
                "region": "ap-shanghai",
                "notice_content": {
                    "mode": "create",
                    "payload": {"Name": "content", "NoticeContents": []},
                },
                "notice": {"mode": "skip"},
                "policy": {
                    "mode": "create",
                    "payload": {
                        "Name": "policy",
                        "AlarmNoticeIds": ["${notice.alarm_notice_id}"],
                        "AlarmTargets": [
                            {"Query": "* | select count(*) as error_count", "Number": 1}
                        ],
                        "Condition": "$1.error_count > 0",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["alarm", "bundle", "apply", "--bundle", f"@{bundle}", "--confirm-real-write"],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    assert "unresolved bundle token: ${notice.alarm_notice_id}" in result.stdout
    assert fake_client.calls == []


def test_alarm_bundle_plan_rejects_invalid_mode(runner, tmp_path):
    bundle = tmp_path / "bundle.json"
    bundle.write_text('{"policy":{"mode":"replace","payload":{}}}', encoding="utf-8")

    result = runner.invoke(app, ["alarm", "bundle", "plan", "--bundle", f"@{bundle}"])

    assert result.exit_code == 1
    assert "bundle_mode_invalid" in json_output(result)["data"]["issues"][0]["code"]
