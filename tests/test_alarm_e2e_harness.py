from __future__ import annotations

import json
from typing import Any

from cls_cli.cli import app
from cls_cli.core.alarm_e2e import AlarmE2EOptions, run_alarm_e2e
from tests.conftest import FakeClsClient, json_output


def _responses() -> dict[str, dict[str, Any]]:
    return {
        "CreateLogset": {"Response": {"LogsetId": "logset-e2e", "RequestId": "req-logset"}},
        "CreateTopic": {"Response": {"TopicId": "topic-e2e", "RequestId": "req-topic"}},
        "CreateIndex": {"Response": {"RequestId": "req-index"}},
        "UploadLog": {"Response": {"RequestId": "req-upload"}},
        "SearchLog": {
            "Response": {
                "AnalysisRecords": ['{"error_count":3,"request_uri":"/api/order"}'],
                "Results": [
                    {
                        "LogJson": (
                            '{"e2e_id":"fixed-run","status":"500",'
                            '"request_uri":"/api/order"}'
                        ),
                        "Time": 1710000000123,
                    }
                ],
                "RequestId": "req-search",
            }
        },
        "DescribeLogHistogram": {"Response": {"TotalCount": 4, "RequestId": "req-hist"}},
        "CreateNoticeContent": {
            "Response": {"NoticeContentId": "notice-content-e2e", "RequestId": "req-content"}
        },
        "CreateWebCallback": {
            "Response": {"WebCallbackId": "web-callback-e2e", "RequestId": "req-web-callback"}
        },
        "CreateAlarmNotice": {
            "Response": {"AlarmNoticeId": "alarm-notice-e2e", "RequestId": "req-notice"}
        },
        "CreateAlarm": {"Response": {"AlarmId": "alarm-e2e", "RequestId": "req-alarm"}},
        "DescribeAlertRecordHistory": {
            "Response": {"Records": [{"RecordId": "record-e2e"}], "RequestId": "req-history"}
        },
        "GetAlarmLog": {
            "Response": {
                "Results": [
                    {
                        "LogJson": '{"condition_evaluate_result":"Matched",'
                        '"notification_send_result":"SendSuccess"}'
                    }
                ],
                "RequestId": "req-log",
            }
        },
        "DeleteAlarm": {"Response": {"RequestId": "req-delete-alarm"}},
        "DeleteAlarmNotice": {"Response": {"RequestId": "req-delete-notice"}},
        "DeleteWebCallback": {"Response": {"RequestId": "req-delete-web-callback"}},
        "DeleteNoticeContent": {"Response": {"RequestId": "req-delete-content"}},
        "DeleteIndex": {"Response": {"RequestId": "req-delete-index"}},
        "DeleteTopic": {"Response": {"RequestId": "req-delete-topic"}},
        "DeleteLogset": {"Response": {"RequestId": "req-delete-logset"}},
    }


def test_alarm_e2e_dry_run_cli_makes_no_cloud_calls(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        ["alarm", "verify", "e2e", "--region", "ap-shanghai", "--dry-run"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    data = json_output(result)["data"]
    assert data["dry_run"] is True
    assert "CreateMachineGroup" not in data["planned_actions"]
    assert "CreateConfig" not in data["planned_actions"]
    assert data["planned_actions"][:4] == [
        "CreateLogset",
        "CreateTopic",
        "CreateIndex",
        "UploadLog",
    ]
    assert fake_client.calls == []


def test_alarm_e2e_cli_requires_explicit_real_write_confirmation(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        ["alarm", "verify", "e2e", "--region", "ap-shanghai"],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    assert json_output(result)["error"]["code"] == "CONFIRMATION_REQUIRED"
    assert fake_client.calls == []


def test_alarm_e2e_cli_exits_non_zero_when_verification_fails(runner, cli_obj, fake_client):
    fake_client.error = RuntimeError("create failed")

    result = runner.invoke(
        app,
        [
            "alarm",
            "verify",
            "e2e",
            "--region",
            "ap-shanghai",
            "--confirm-real-write",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    data = json_output(result)["data"]
    assert data["status"] == "FAIL"
    assert data["findings"][0]["message"] == "create failed"


def test_alarm_e2e_runs_alarm_only_flow_and_cleans_up(monkeypatch):
    client = FakeClsClient(responses=_responses())
    sent: list[tuple[str, str]] = []
    monkeypatch.setenv("CLS_ALARM_TEST_WEBHOOK_URL", "https://example.com/wecom/private-token")
    monkeypatch.setenv("CLS_ALARM_TEST_FEISHU_WEBHOOK_URL", "https://example.com/feishu/secret")

    result = run_alarm_e2e(
        client,
        "ap-shanghai",
        AlarmE2EOptions(
            confirm_real_write=True,
            run_id="fixed-run",
            poll_seconds=0,
            poll_interval_seconds=0,
        ),
        robot_sender=lambda rendered, robot, env, timeout: sent.append((robot, env))
        or {"errcode": 0},
    )

    assert result["status"] == "PASS"
    actions = [call[0] for call in client.calls]
    assert actions == [
        "CreateLogset",
        "CreateTopic",
        "CreateIndex",
        "UploadLog",
        "SearchLog",
        "DescribeLogHistogram",
        "SearchLog",
        "CreateNoticeContent",
        "CreateNoticeContent",
        "CreateNoticeContent",
        "CreateWebCallback",
        "CreateWebCallback",
        "CreateAlarmNotice",
        "CreateAlarm",
        "DescribeAlertRecordHistory",
        "GetAlarmLog",
        "DeleteAlarm",
        "DeleteAlarmNotice",
        "DeleteWebCallback",
        "DeleteWebCallback",
        "DeleteNoticeContent",
        "DeleteNoticeContent",
        "DeleteNoticeContent",
        "DeleteIndex",
        "DeleteTopic",
        "DeleteLogset",
    ]
    notice_payload = next(
        payload for action, payload, _ in client.calls if action == "CreateAlarmNotice"
    )
    assert notice_payload["WebCallbacks"] == [
        {
            "CallbackType": "WeCom",
            "Url": "",
            "WebCallbackId": "web-callback-e2e",
            "NoticeContentId": "notice-content-e2e",
        },
        {
            "CallbackType": "Lark",
            "Url": "",
            "WebCallbackId": "web-callback-e2e",
            "NoticeContentId": "notice-content-e2e",
        },
    ]
    assert "CreateMachineGroup" not in actions
    assert "CreateConfig" not in actions
    assert sent == []
    phases = {item["phase"] for item in result["assertions"]}
    assert "robot_send_wecom" not in phases
    assert "robot_send_feishu" not in phases
    assert "template_variant_trigger_result_fields" in phases
    assert "template_variant_query_log_content" in phases
    assert "template_variant_trigger_params" in phases
    assert "template_variant_unknown_variable_negative" in phases
    assert "template_variant_missing_alias_negative" in phases
    assert "template_variant_channel_escape_negative" in phases
    assert all("secret" not in str(item).lower() for item in result["assertions"])


def test_alarm_e2e_advanced_mode_uses_multi_conditions_and_notice_rules(monkeypatch):
    client = FakeClsClient(responses=_responses())
    monkeypatch.setenv("CLS_ALARM_TEST_WEBHOOK_URL", "https://example.com/wecom/private-token")

    result = run_alarm_e2e(
        client,
        "ap-shanghai",
        AlarmE2EOptions(
            confirm_real_write=True,
            run_id="fixed-run",
            poll_seconds=0,
            poll_interval_seconds=0,
            advanced=True,
        ),
    )

    assert result["status"] == "PASS"
    notice_payload = next(
        payload for action, payload, _ in client.calls if action == "CreateAlarmNotice"
    )
    assert notice_payload["Type"] == ""
    assert notice_payload["NoticeReceivers"] == []
    assert notice_payload["WebCallbacks"] == []
    assert notice_payload["CallbackPrioritize"] is False
    assert json.loads(notice_payload["NoticeRules"][0]["Rule"])["Value"] == "AND"
    assert notice_payload["NoticeRules"][0]["WebCallbacks"] == [
        {
            "CallbackType": "WeCom",
            "Url": "",
            "WebCallbackId": "web-callback-e2e",
            "NoticeContentId": "notice-content-e2e",
        }
    ]
    assert notice_payload["NoticeRules"][0]["Escalate"] is False

    alarm_payload = next(payload for action, payload, _ in client.calls if action == "CreateAlarm")
    assert "Condition" not in alarm_payload
    assert "AlarmLevel" not in alarm_payload
    assert alarm_payload["MultiConditions"] == [
        {"Condition": "$1.error_count > 0", "AlarmLevel": 0}
    ]
    assert alarm_payload["GroupTriggerStatus"] is True
    assert alarm_payload["GroupTriggerCondition"] == ["request_uri", "status"]
    assert alarm_payload["CallBack"] == {"Headers": [], "Body": ""}


def test_alarm_e2e_cli_dry_run_reports_advanced_mode(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        ["alarm", "verify", "e2e", "--region", "ap-shanghai", "--dry-run", "--advanced"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    data = json_output(result)["data"]
    assert data["advanced"] is True
    assert fake_client.calls == []


def test_alarm_e2e_can_run_optional_robot_smoke_test(monkeypatch):
    client = FakeClsClient(responses=_responses())
    sent: list[tuple[str, str]] = []
    monkeypatch.setenv("CLS_ALARM_TEST_WEBHOOK_URL", "https://example.com/wecom/private-token")
    monkeypatch.setenv("CLS_ALARM_TEST_FEISHU_WEBHOOK_URL", "https://example.com/feishu/secret")

    result = run_alarm_e2e(
        client,
        "ap-shanghai",
        AlarmE2EOptions(
            confirm_real_write=True,
            run_id="fixed-run",
            poll_seconds=0,
            poll_interval_seconds=0,
            send_wecom=True,
            send_feishu=True,
        ),
        robot_sender=lambda rendered, robot, env, timeout: sent.append((robot, env))
        or {"errcode": 0},
    )

    assert result["status"] == "PASS"
    assert sent == [
        ("wecom", "CLS_ALARM_TEST_WEBHOOK_URL"),
        ("feishu", "CLS_ALARM_TEST_FEISHU_WEBHOOK_URL"),
    ]


def test_alarm_e2e_sample_context_contains_cls_notification_fields():
    client = FakeClsClient(responses=_responses())
    captured_render: list[dict[str, Any]] = []

    result = run_alarm_e2e(
        client,
        "ap-shanghai",
        AlarmE2EOptions(
            confirm_real_write=True,
            run_id="fixed-run",
            poll_seconds=0,
            poll_interval_seconds=0,
            send_wecom=True,
            send_feishu=False,
        ),
        robot_sender=lambda rendered, robot, env, timeout: captured_render.append(rendered)
        or {"errcode": 0},
        env_getter=lambda name: (
            "https://example.com/wecom" if name == "CLS_ALARM_TEST_WEBHOOK_URL" else None
        ),
    )

    assert result["status"] == "PASS"
    content = captured_render[0]["NoticeContents"][0]["TriggerContent"]["Content"]
    assert "- 所属账号：1000000000(cls-cli-e2e)" in content
    assert "- 地域：ap-shanghai" in content
    assert "- 日志主题：cls-cli-alarm-e2e-fixed-run" in content
    assert "- 首次触发：" in content and "- 首次触发：\n" not in content
    assert "- 本次通知：" in content and "- 本次通知：\n" not in content


def test_alarm_e2e_cleans_up_after_failure():
    client = FakeClsClient(responses=_responses())

    def failing_invoke(action: str, payload: dict[str, Any], region: str) -> dict[str, Any]:
        client.calls.append((action, payload, region))
        if action == "UploadLog":
            raise RuntimeError("upload failed")
        return client.responses[action]

    client.invoke = failing_invoke  # type: ignore[method-assign]

    result = run_alarm_e2e(
        client,
        "ap-shanghai",
        AlarmE2EOptions(confirm_real_write=True, run_id="fixed-run"),
    )

    actions = [call[0] for call in client.calls]
    assert result["status"] == "FAIL"
    assert actions[-3:] == ["DeleteIndex", "DeleteTopic", "DeleteLogset"]
    assert any(finding["phase"] == "upload_logs" for finding in result["findings"])


def test_alarm_e2e_does_not_pass_when_execution_log_did_not_trigger():
    responses = _responses()
    responses["DescribeAlertRecordHistory"] = {
        "Response": {"Records": [], "RequestId": "req-history"}
    }
    responses["GetAlarmLog"] = {
        "Response": {
            "Results": [
                {
                    "LogJson": '{"condition_evaluate_result":"QueryResultUnmatch",'
                    '"notification_send_result":"NotSend",'
                    '"reach_trigger":"false",'
                    '"summary_cn":"执行语句结果不满足触发条件"}'
                }
            ],
            "RequestId": "req-log",
        }
    }
    client = FakeClsClient(responses=responses)

    result = run_alarm_e2e(
        client,
        "ap-shanghai",
        AlarmE2EOptions(
            confirm_real_write=True,
            run_id="fixed-run",
            poll_seconds=0,
            poll_interval_seconds=0,
        ),
    )

    assert result["status"] == "PARTIAL"
    assert any(finding["phase"] == "alarm_trigger" for finding in result["findings"])


def test_alarm_e2e_policy_uses_wide_query_window_for_scheduler_delay():
    client = FakeClsClient(responses=_responses())

    run_alarm_e2e(
        client,
        "ap-shanghai",
        AlarmE2EOptions(
            confirm_real_write=True,
            run_id="fixed-run",
            poll_seconds=0,
            poll_interval_seconds=0,
        ),
    )

    create_alarm_payload = next(
        payload for action, payload, _ in client.calls if action == "CreateAlarm"
    )
    target = create_alarm_payload["AlarmTargets"][0]
    assert target["StartTimeOffset"] == -10
    assert target["EndTimeOffset"] == 0
    assert create_alarm_payload["MonitorTime"] == {"Type": "Period", "Time": 1}
