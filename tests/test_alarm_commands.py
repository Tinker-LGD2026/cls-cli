from __future__ import annotations

import json

from cls_cli.cli import app
from tests.conftest import json_output


def test_alarm_policy_create_uses_payload_file(runner, cli_obj, fake_client, tmp_path):
    payload = tmp_path / "alarm.json"
    payload.write_text('{"Name":"high-error","Status":true}', encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "alarm",
            "policy",
            "create",
            "--region",
            "ap-guangzhou",
            "--payload",
            f"@{payload}",
            "--skip-validation",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        ("CreateAlarm", {"Name": "high-error", "Status": True}, "ap-guangzhou")
    ]


def test_alarm_notice_list_invokes_describe_alarm_notices(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        ["alarm", "notice", "list", "--region", "ap-guangzhou"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [("DescribeAlarmNotices", {}, "ap-guangzhou")]


def test_alarm_integration_list_invokes_describe_web_callbacks(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        ["alarm", "integration", "list", "--region", "ap-guangzhou"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [("DescribeWebCallbacks", {}, "ap-guangzhou")]


def test_alarm_integration_create_reads_webhook_from_env_and_redacts_output(
    runner, cli_obj, fake_client, monkeypatch
):
    monkeypatch.setenv("CLS_ALARM_WEBHOOK_URL", "https://callback.example.com/hook")
    monkeypatch.setenv("CLS_ALARM_WEBHOOK_KEY", "test-signing-key")

    result = runner.invoke(
        app,
        [
            "alarm",
            "integration",
            "create",
            "--region",
            "ap-guangzhou",
            "--name",
            "prod-wecom",
            "--type",
            "wecom",
            "--webhook-env",
            "CLS_ALARM_WEBHOOK_URL",
            "--key-env",
            "CLS_ALARM_WEBHOOK_KEY",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "CreateWebCallback",
            {
                "Name": "prod-wecom",
                "Type": "WeCom",
                "Webhook": "https://callback.example.com/hook",
                "Key": "test-signing-key",
            },
            "ap-guangzhou",
        )
    ]
    assert "private-token" not in result.stdout
    assert "test-signing-key" not in result.stdout


def test_alarm_integration_validate_rejects_http_without_method(runner, tmp_path):
    payload = tmp_path / "integration.json"
    payload.write_text(
        '{"Name":"http-callback","Type":"Http","Webhook":"https://example.com/callback"}',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["alarm", "integration", "validate", "--payload", f"@{payload}"],
    )

    assert result.exit_code == 1
    data = json_output(result)["data"]
    assert data["valid"] is False
    assert any(issue["code"] == "method_required" for issue in data["issues"])


def test_alarm_notice_delete_uses_alarm_notice_id_field(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        [
            "alarm",
            "notice",
            "delete",
            "--region",
            "ap-guangzhou",
            "--notice-id",
            "notice-123",
            "--force",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        ("DeleteAlarmNotice", {"AlarmNoticeId": "notice-123"}, "ap-guangzhou")
    ]


def test_alarm_notice_validate_rejects_empty_notice_rules(runner, tmp_path):
    payload = tmp_path / "notice.json"
    payload.write_text('{"NoticeRules": [{}]}', encoding="utf-8")

    result = runner.invoke(app, ["alarm", "notice", "validate", "--payload", f"@{payload}"])

    assert result.exit_code == 1
    issues = json_output(result)["data"]["issues"]
    assert any(issue["code"] == "notice_rule_target_required" for issue in issues)


def test_alarm_notice_scaffold_references_integration_configuration(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "notice",
            "scaffold",
            "--name",
            "prod-notice",
            "--callback-type",
            "wecom",
            "--integration-id",
            "webcallback-123",
            "--content-id",
            "notice-content-123",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json_output(result)["data"]["payload"]
    assert payload == {
        "Name": "prod-notice",
        "Type": "All",
        "WebCallbacks": [
            {
                "CallbackType": "WeCom",
                "Url": "",
                "WebCallbackId": "webcallback-123",
                "NoticeContentId": "notice-content-123",
            }
        ],
        "AlarmShieldStatus": 1,
    }


def test_alarm_notice_scaffold_builds_advanced_notice_rule(runner):
    rule = (
        '{"Value":"AND","Type":"Operation","Children":['
        '{"Type":"Condition","Value":"NotifyType","Children":['
        '{"Value":"In","Type":"Compare"},{"Value":"[1,2]","Type":"Value"}]}]}'
    )
    result = runner.invoke(
        app,
        [
            "alarm",
            "notice",
            "scaffold",
            "--name",
            "advanced-notice",
            "--advanced-rule",
            "--rule",
            rule,
            "--callback-type",
            "wecom",
            "--integration-id",
            "webcallback-123",
            "--content-id",
            "notice-content-123",
            "--receiver-id",
            "1000001",
            "--receiver-channel",
            "Email",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json_output(result)["data"]["payload"]
    assert payload["Type"] == ""
    assert payload["NoticeReceivers"] == []
    assert payload["WebCallbacks"] == []
    assert payload["CallbackPrioritize"] is False
    rule_payload = payload["NoticeRules"][0]
    assert json.loads(rule_payload["Rule"])["Type"] == "Operation"
    assert rule_payload["WebCallbacks"] == [
        {
            "CallbackType": "WeCom",
            "Url": "",
            "WebCallbackId": "webcallback-123",
            "NoticeContentId": "notice-content-123",
        }
    ]
    assert rule_payload["NoticeReceivers"] == [
        {
            "ReceiverType": "Uin",
            "ReceiverIds": [1000001],
            "ReceiverChannels": ["Email"],
            "StartTime": "00:00:00",
            "EndTime": "23:59:59",
            "Index": 1,
            "NoticeContentId": "",
        }
    ]
    assert rule_payload["Escalate"] is False


def test_alarm_notice_scaffold_builds_browser_confirmed_rule_conditions(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "notice",
            "scaffold",
            "--name",
            "advanced-notice",
            "--advanced-rule",
            "--rule-notify-type",
            "1",
            "--rule-notify-type",
            "2",
            "--rule-level",
            "1",
            "--rule-level",
            "0",
            "--rule-notify-time-between",
            "09:00:00-18:00:00",
            "--rule-duration-gt",
            "1",
            "--rule-alarm-name-regex",
            "^cls-cli-.*",
            "--rule-label-in",
            "service=payment",
            "--rule-label-regex",
            "env=prod|staging",
            "--callback-type",
            "http",
            "--integration-id",
            "webcallback-123",
            "--content-id",
            "notice-content-123",
            "--method",
            "POST",
        ],
    )

    assert result.exit_code == 0, result.stdout
    rule = json.loads(json_output(result)["data"]["payload"]["NoticeRules"][0]["Rule"])
    assert rule["Value"] == "AND"
    assert rule["Type"] == "Operation"
    assert rule["Children"] == [
        {
            "Type": "Condition",
            "Value": "NotifyType",
            "Children": [
                {"Value": "In", "Type": "Compare"},
                {"Value": "[1,2]", "Type": "Value"},
            ],
        },
        {
            "Type": "Condition",
            "Value": "Level",
            "Children": [
                {"Value": "In", "Type": "Compare"},
                {"Value": "[1,0]", "Type": "Value"},
            ],
        },
        {
            "Type": "Condition",
            "Value": "NotifyTime",
            "Children": [
                {"Value": "Between", "Type": "Compare"},
                {"Value": '["09:00:00","18:00:00"]', "Type": "Value"},
            ],
        },
        {
            "Type": "Condition",
            "Value": "Duration",
            "Children": [
                {"Value": ">", "Type": "Compare"},
                {"Value": 1, "Type": "Value"},
            ],
        },
        {
            "Type": "Condition",
            "Value": "AlarmName",
            "Children": [
                {"Value": "=~", "Type": "Compare"},
                {"Value": "^cls-cli-.*", "Type": "Value"},
            ],
        },
        {
            "Type": "Condition",
            "Value": "Label",
            "Children": [
                {"Value": "service", "Type": "Key"},
                {"Value": "In", "Type": "Compare"},
                {"Value": '["payment"]', "Type": "Value"},
            ],
        },
        {
            "Type": "Condition",
            "Value": "Label",
            "Children": [
                {"Value": "env", "Type": "Key"},
                {"Value": "=~", "Type": "Compare"},
                {"Value": "prod|staging", "Type": "Value"},
            ],
        },
    ]


def test_alarm_notice_scaffold_builds_advanced_escalation(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "notice",
            "scaffold",
            "--name",
            "advanced-notice",
            "--advanced-rule",
            "--callback-type",
            "wecom",
            "--integration-id",
            "webcallback-primary",
            "--content-id",
            "notice-content-primary",
            "--escalate",
            "--escalate-interval",
            "10",
            "--escalate-type",
            "2",
            "--escalate-callback-type",
            "wecom",
            "--escalate-integration-id",
            "webcallback-escalate",
            "--escalate-content-id",
            "notice-content-escalate",
        ],
    )

    assert result.exit_code == 0, result.stdout
    rule_payload = json_output(result)["data"]["payload"]["NoticeRules"][0]
    assert rule_payload["Escalate"] is True
    assert rule_payload["Interval"] == 10
    assert rule_payload["Type"] == 2
    assert rule_payload["EscalateNotice"] == {
        "WebCallbacks": [
            {
                "CallbackType": "WeCom",
                "Url": "",
                "WebCallbackId": "webcallback-escalate",
                "NoticeContentId": "notice-content-escalate",
            }
        ]
    }


def test_alarm_history_invokes_describe_alert_record_history(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        [
            "alarm",
            "history",
            "--region",
            "ap-guangzhou",
            "--alarm-id",
            "alarm-123",
            "--topic-id",
            "topic-123",
            "--status",
            "0",
            "--from",
            "1710000000",
            "--to",
            "1710003600",
            "--limit",
            "20",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "DescribeAlertRecordHistory",
            {
                "From": 1710000000000,
                "To": 1710003600000,
                "Limit": 20,
                "Filters": [
                    {"Key": "alertId", "Values": ["alarm-123"]},
                    {"Key": "topicId", "Values": ["topic-123"]},
                    {"Key": "status", "Values": ["0"]},
                ],
            },
            "ap-guangzhou",
        )
    ]


def test_alarm_log_builds_debug_query(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        [
            "alarm",
            "log",
            "--region",
            "ap-guangzhou",
            "--alarm-id",
            "alarm-123",
            "--from",
            "1710000000",
            "--to",
            "1710003600",
            "--limit",
            "100",
            "--sort",
            "asc",
            "--use-new-analysis",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "GetAlarmLog",
            {
                "From": 1710000000000,
                "To": 1710003600000,
                "Query": 'alert_id:"alarm-123"',
                "Limit": 100,
                "Sort": "asc",
                "UseNewAnalysis": True,
            },
            "ap-guangzhou",
        )
    ]


def test_alarm_log_redacts_sensitive_execution_payload(runner, cli_obj, fake_client):
    fake_client.responses = {
        "GetAlarmLog": {
            "Response": {
                "Results": [
                    {
                        "LogJson": json.dumps(
                            {
                                "notification_send_result": "SendSuccess",
                                    "ActualCallback": [
                                        {"URL": "https://callback.example.com/hook?key=private-token"}
                                    ],
                                "SecretText": "very-secret",
                                "Authorization": "Bearer abc",
                            }
                        )
                    }
                ]
            }
        }
    }

    result = runner.invoke(
        app,
        [
            "alarm",
            "log",
            "--region",
            "ap-guangzhou",
            "--alarm-id",
            "alarm-123",
            "--from",
            "1710000000",
            "--to",
            "1710003600",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    output = result.stdout
    assert "private-token" not in output
    assert "very-secret" not in output
    assert "Bearer abc" not in output
    assert "key=<redacted>" in output


def test_alarm_template_generate_webhook_json(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "template",
            "generate",
            "--scenario",
            "http-5xx",
            "--channel",
            "webhook",
            "--fields",
            "request_uri,status,error_count",
            "--name",
            "http 5xx template",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json_output(result)["data"]["payload"]
    assert payload["Name"] == "http 5xx template"
    assert payload["NoticeContents"][0]["Type"] == "Http"
    content = payload["NoticeContents"][0]["TriggerContent"]["Content"]
    assert "{{escape .Alarm}}" in content
    assert "{{toPrettyJson .TriggerResult}}" in content


def test_alarm_template_generate_wecom_uses_robot_markdown_defaults(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "template",
            "generate",
            "--scenario",
            "http-5xx",
            "--channel",
            "wecom",
            "--fields",
            "request_uri,status,error_count",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json_output(result)["data"]["payload"]
    content = payload["NoticeContents"][0]["TriggerContent"]["Content"]
    recovery = payload["NoticeContents"][0]["RecoveryContent"]["Content"]
    assert '{{- define "subTemplate" -}}' in content
    assert '{{- substr (renderTemplate "subTemplate") 0 3500}}' in content
    assert 'renderTemplate "subTemplate" .' not in content
    assert "{{escape_markdown .Alarm}}" in content
    assert "{{escape_markdown .Condition}}" in content
    assert "## 告警概览" in content
    assert "## 命中结果" in content
    assert "{{range .QueryResult[0]}}" in content
    assert "URI={{escape_markdown .request_uri}}" in content
    assert "{{.AnalysisResultFormat_zh}}" in content
    assert "[详细报告]({{.DetailUrl}})" in content
    assert "{{if .CanSilent}}" in content
    assert "{{.SilentUrl}}" in content
    assert "{{.TriggerResult}}" not in recovery


def test_alarm_template_generate_feishu_uses_markdown_html_escape(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "template",
            "generate",
            "--scenario",
            "http-5xx",
            "--channel",
            "feishu",
            "--fields",
            "request_uri,status,error_count",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json_output(result)["data"]["payload"]
    content = payload["NoticeContents"][0]["TriggerContent"]["Content"]
    assert '{{- define "subTemplate" -}}' in content
    assert '{{- substr (renderTemplate "subTemplate") 0 7000}}' in content
    assert 'renderTemplate "subTemplate" .' not in content
    assert "{{escape_markdown_html .Alarm}}" in content
    assert "{{escape_markdown_html .request_uri}}" in content
    assert "{{escape_markdown ." not in content


def test_alarm_template_render_generated_robot_template(runner, tmp_path):
    generated = runner.invoke(
        app,
        [
            "alarm",
            "template",
            "generate",
            "--scenario",
            "http-5xx",
            "--channel",
            "wecom",
            "--fields",
            "request_uri,error_count",
        ],
    )
    assert generated.exit_code == 0, generated.stdout
    notice = tmp_path / "notice.json"
    notice.write_text(
        json.dumps(json_output(generated)["data"]["payload"], ensure_ascii=False),
        encoding="utf-8",
    )
    sample = tmp_path / "sample.json"
    sample.write_text(
        json.dumps(
            {
                "Alarm": "API 5xx",
                "Level_zh": "警告",
                "Condition": "$1.error_count > 10",
                "UIN": "1000000000",
                "Nickname": "demo",
                "Region": "ap-shanghai",
                "Topic": "api-topic",
                "StartTime": "2026-05-21 10:00:00",
                "NotifyTime": "2026-05-21 10:01:00",
                "ConsecutiveAlertNums": 1,
                "TriggerParams": "$1.error_count=27;$1.request_uri=/api/order",
                "QueryResult": [[{"request_uri": "/api/order", "error_count": 27}]],
                "TriggerResult": [[{"request_uri": "/api/order", "error_count": 27}]],
                "DetailUrl": "https://cloud.tencent.com/",
                "QueryUrl": "https://cloud.tencent.com/query",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "alarm",
            "template",
            "render",
            "--payload",
            f"@{notice}",
            "--sample-context",
            f"@{sample}",
        ],
    )

    assert result.exit_code == 0, result.stdout
    content = json_output(result)["data"]["rendered"]["NoticeContents"][0]["TriggerContent"][
        "Content"
    ]
    assert "{{" not in content
    assert "# 【告警】API 5xx" in content
    assert "/api/order" in content
    assert "[详细报告](https://cloud.tencent.com/)" in content


def test_alarm_template_validate_catches_unknown_variable(runner, tmp_path):
    payload = tmp_path / "notice.json"
    payload.write_text(
        '{"Name":"bad","NoticeContents":[{"Type":"Email","TriggerContent":{"Title":"{{.AlarmName}}","Content":"body"}}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["alarm", "template", "validate", "--payload", f"@{payload}"])

    assert result.exit_code == 1
    data = json_output(result)["data"]
    assert data["valid"] is False
    assert data["issues"][0]["code"] == "unknown_variable"
    assert data["issues"][0]["suggestion"] == "{{.Alarm}}"


def test_alarm_template_validate_policy_aliases(runner, tmp_path):
    notice = tmp_path / "notice.json"
    notice.write_text(
        '{"NoticeContents":[{"Type":"Email","TriggerContent":{"Content":"'
        "{{.QueryResult[0][0].error_count}} {{.QueryResult[0][0].request_uri}}"
        '"}}]}',
        encoding="utf-8",
    )
    policy = tmp_path / "policy.json"
    policy.write_text(
        '{"AlarmTargets":[{"Query":"status:>=500 | select count(*) as error_count limit 10"}]}',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "alarm",
            "template",
            "validate",
            "--payload",
            f"@{notice}",
            "--policy-payload",
            f"@{policy}",
        ],
    )

    assert result.exit_code == 1
    data = json_output(result)["data"]
    assert data["valid"] is False
    assert any(issue["code"] == "missing_query_alias" for issue in data["issues"])


def test_alarm_debug_explain_combines_policy_history_and_execution_log(
    runner, cli_obj, fake_client
):
    fake_client.responses = {
        "DescribeAlarms": {
            "Response": {
                "Alarms": [
                    {
                        "AlarmId": "alarm-123",
                        "Name": "api 5xx",
                        "Status": True,
                        "AlarmTargets": [
                            {
                                "TopicId": "topic-123",
                                "Query": "status:>=500 | select count(*) as error_count",
                            }
                        ],
                    }
                ],
                "TotalCount": 1,
            }
        },
        "DescribeAlertRecordHistory": {
            "Response": {
                "Records": [
                    {
                        "RecordId": "record-1",
                        "AlarmId": "alarm-123",
                        "Status": 0,
                        "Trigger": "$1.error_count > 10",
                    }
                ],
                "TotalCount": 1,
            }
        },
        "GetAlarmLog": {
            "Response": {
                "Results": [
                    {
                        "LogJson": (
                            '{"condition_evaluate_result":"QueryResultUnmatch",'
                            '"notification_send_result":"NotSend",'
                            '"process_error_msg":"conditions are not matched"}'
                        )
                    }
                ]
            }
        },
    }

    result = runner.invoke(
        app,
        [
            "alarm",
            "debug",
            "explain",
            "--region",
            "ap-guangzhou",
            "--alarm-id",
            "alarm-123",
            "--from",
            "1710000000",
            "--to",
            "1710003600",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    data = json_output(result)["data"]
    assert data["summary"] == "告警策略存在，但最近执行结果未满足触发条件。"
    assert "查询结果未满足触发条件" in data["probable_causes"]
    assert fake_client.calls == [
        (
            "DescribeAlarms",
            {
                "Filters": [{"Name": "alarmId", "Values": ["alarm-123"]}],
                "Offset": 0,
                "Limit": 1,
            },
            "ap-guangzhou",
        ),
        (
            "DescribeAlertRecordHistory",
            {
                "From": 1710000000000,
                "To": 1710003600000,
                "Offset": 0,
                "Limit": 20,
                "Filters": [{"Key": "alertId", "Values": ["alarm-123"]}],
            },
            "ap-guangzhou",
        ),
        (
            "GetAlarmLog",
            {
                "From": 1710000000000,
                "To": 1710003600000,
                "Query": 'alert_id:"alarm-123"',
                "Limit": 20,
                "UseNewAnalysis": True,
            },
            "ap-guangzhou",
        ),
    ]


def test_alarm_template_render_with_sample_context(runner, tmp_path):
    notice = tmp_path / "notice.json"
    notice.write_text(
        '{"NoticeContents":[{"Type":"Email","TriggerContent":{'
        '"Title":"【{{.Level_zh}}】{{.Alarm}}",'
        '"Content":"接口: {{.TriggerResult[0][0].request_uri}}\\n'
        "错误数: {{.TriggerResult[0][0].error_count}}\\n"
        '{{toPrettyJson .TriggerResult}}"},'
        '"RecoveryContent":{"Title":"恢复 {{.Alarm}}","Content":"已恢复"}}]}',
        encoding="utf-8",
    )
    sample = tmp_path / "sample.json"
    sample.write_text(
        '{"Alarm":"API 5xx","Level_zh":"警告",'
        '"TriggerResult":[[{"request_uri":"/api/order","error_count":27}]]}',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "alarm",
            "template",
            "render",
            "--payload",
            f"@{notice}",
            "--sample-context",
            f"@{sample}",
        ],
    )

    assert result.exit_code == 0, result.stdout
    rendered = json_output(result)["data"]["rendered"]
    content = rendered["NoticeContents"][0]["TriggerContent"]
    assert content["Title"] == "【警告】API 5xx"
    assert "接口: /api/order" in content["Content"]
    assert "错误数: 27" in content["Content"]


def test_alarm_template_send_test_posts_wecom_markdown(runner, tmp_path, monkeypatch):
    notice = tmp_path / "notice.json"
    notice.write_text(
        '{"NoticeContents":[{"Type":"Http","TriggerContent":{'
        '"Title":"【{{.Level_zh}}】{{.Alarm}}",'
        '"Content":"接口: {{.TriggerResult[0][0].request_uri}}"}}]}',
        encoding="utf-8",
    )
    sample = tmp_path / "sample.json"
    sample.write_text(
        '{"Alarm":"API 5xx","Level_zh":"警告","TriggerResult":[[{"request_uri":"/api/order"}]]}',
        encoding="utf-8",
    )
    monkeypatch.setenv("CLS_ALARM_TEST_WEBHOOK_URL", "https://example.com/webhook")
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"errcode":0,"errmsg":"ok"}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["content_type"] = request.headers["Content-type"]
        return FakeResponse()

    monkeypatch.setattr("cls_cli.commands.alarm_template.urlopen", fake_urlopen)

    result = runner.invoke(
        app,
        [
            "alarm",
            "template",
            "send-test",
            "--payload",
            f"@{notice}",
            "--sample-context",
            f"@{sample}",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert captured["url"] == "https://example.com/webhook"
    assert captured["timeout"] == 10
    assert captured["content_type"] == "application/json"
    assert captured["body"]["msgtype"] == "markdown"
    assert "【警告】API 5xx" in captured["body"]["markdown"]["content"]
    assert "接口: /api/order" in captured["body"]["markdown"]["content"]
    data = json_output(result)["data"]
    assert data["sent"] is True
    assert data["response"] == {"errcode": 0, "errmsg": "ok"}


def test_alarm_template_send_test_posts_feishu_interactive_card(runner, tmp_path, monkeypatch):
    notice = tmp_path / "notice.json"
    notice.write_text(
        '{"NoticeContents":[{"Type":"Http","TriggerContent":{'
        '"Title":"【{{.Level_zh}}】{{.Alarm}}",'
        '"Content":"接口: {{.TriggerResult[0][0].request_uri}}"}}]}',
        encoding="utf-8",
    )
    sample = tmp_path / "sample.json"
    sample.write_text(
        '{"Alarm":"API 5xx","Level_zh":"警告","TriggerResult":[[{"request_uri":"/api/order"}]]}',
        encoding="utf-8",
    )
    monkeypatch.setenv("CLS_ALARM_TEST_FEISHU_WEBHOOK_URL", "https://example.com/feishu")
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"StatusCode":0,"StatusMessage":"success","code":0,"msg":"success"}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("cls_cli.commands.alarm_template.urlopen", fake_urlopen)

    result = runner.invoke(
        app,
        [
            "alarm",
            "template",
            "send-test",
            "--payload",
            f"@{notice}",
            "--sample-context",
            f"@{sample}",
            "--robot",
            "feishu",
            "--webhook-url-env",
            "CLS_ALARM_TEST_FEISHU_WEBHOOK_URL",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert captured["url"] == "https://example.com/feishu"
    assert captured["body"]["msg_type"] == "interactive"
    card = captured["body"]["card"]
    assert card["header"]["title"]["content"] == "【警告】API 5xx"
    assert "接口: /api/order" in card["elements"][0]["text"]["content"]
    data = json_output(result)["data"]
    assert data["sent"] is True
    assert data["response"]["code"] == 0


def test_alarm_policy_test_query_builds_sample_context(runner, cli_obj, fake_client, tmp_path):
    query = "status:>=500 | select count(*) as error_count, request_uri group by request_uri"
    policy = tmp_path / "policy.json"
    policy.write_text(
        '{"AlarmTargets":[{"Number":1,"TopicId":"topic-123","Query":"'
        + query
        + '"}],"Condition":"$1.error_count > 10"}',
        encoding="utf-8",
    )
    fake_client.responses = {
        "SearchLog": {
            "Response": {
                "AnalysisRecords": ['{"error_count":27,"request_uri":"/api/order"}'],
                "Results": [
                    {
                        "LogJson": '{"request_uri":"/api/order","status":"500"}',
                        "Time": 1710000000123,
                    }
                ],
            }
        }
    }

    result = runner.invoke(
        app,
        [
            "alarm",
            "policy",
            "test-query",
            "--payload",
            f"@{policy}",
            "--from",
            "1710000000",
            "--to",
            "1710003600",
            "--region",
            "ap-guangzhou",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "SearchLog",
            {
                "TopicId": "topic-123",
                "QueryString": query,
                "From": 1710000000000,
                "To": 1710003600000,
                "Limit": 100,
            },
            "ap-guangzhou",
        )
    ]
    data = json_output(result)["data"]
    assert data["sample_context"]["QueryResult"] == [
        [{"error_count": 27, "request_uri": "/api/order"}]
    ]
    assert data["sample_context"]["QueryLog"][0][0]["content"]["status"] == "500"
    assert data["condition_preview"]["condition"] == "$1.error_count > 10"


def test_alarm_policy_scaffold_http_5xx(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "policy",
            "scaffold",
            "--scenario",
            "http-5xx",
            "--name",
            "api 5xx",
            "--logset-id",
            "logset-123",
            "--topic-id",
            "topic-123",
            "--threshold",
            "10",
            "--window-minutes",
            "5",
            "--fields",
            "request_uri,status",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json_output(result)["data"]["payload"]
    target = payload["AlarmTargets"][0]
    assert payload["Name"] == "api 5xx"
    assert target["LogsetId"] == "logset-123"
    assert target["TopicId"] == "topic-123"
    assert "count(*) as error_count" in target["Query"]
    assert "group by request_uri,status" in target["Query"]
    assert payload["Condition"] == "$1.error_count > 10"


def test_alarm_template_generate_uses_official_notice_content_types(runner):
    cases = [("wecom", "WeCom"), ("feishu", "Lark"), ("dingtalk", "DingTalk")]

    for channel, expected_type in cases:
        result = runner.invoke(
            app,
            ["alarm", "template", "generate", "--channel", channel],
        )

        assert result.exit_code == 0, result.stdout
        payload = json_output(result)["data"]["payload"]
        assert payload["NoticeContents"][0]["Type"] == expected_type


def test_alarm_template_validate_checks_trigger_result_aliases(runner, tmp_path):
    notice = tmp_path / "notice.json"
    notice.write_text(
        '{"NoticeContents":[{"Type":"Email","TriggerContent":{"Content":"'
        "{{.TriggerResult[0][0].error_count}} {{.TriggerResult[0][0].request_uri}}"
        '"}}]}',
        encoding="utf-8",
    )
    policy = tmp_path / "policy.json"
    policy.write_text(
        '{"AlarmTargets":[{"Query":"status:>=500 | select count(*) as error_count limit 10"}]}',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "alarm",
            "template",
            "validate",
            "--payload",
            f"@{notice}",
            "--policy-payload",
            f"@{policy}",
        ],
    )

    assert result.exit_code == 1
    issues = json_output(result)["data"]["issues"]
    assert any(issue["code"] == "missing_query_alias" for issue in issues)


def test_alarm_template_validate_channel_escape_is_channel_aware(runner, tmp_path):
    notice = tmp_path / "notice.json"
    notice.write_text(
        '{"NoticeContents":[{"Type":"Lark","TriggerContent":{"Content":"接口: {{.Alarm}}"}}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["alarm", "template", "validate", "--payload", f"@{notice}"])

    assert result.exit_code == 1
    issues = json_output(result)["data"]["issues"]
    assert any(issue["code"] == "channel_escape_missing" for issue in issues)
    assert any("escape_markdown_html" in (issue["suggestion"] or "") for issue in issues)


def test_alarm_template_render_supports_trigger_params_helpers(runner, tmp_path):
    notice = tmp_path / "notice.json"
    notice.write_text(
        json.dumps(
            {
                "NoticeContents": [
                    {
                        "Type": "WeCom",
                        "TriggerContent": {
                            "Content": "".join(
                                [
                                    '{{range (splitList ";" .TriggerParams)}}',
                                    '{{escape_markdown (regexReplaceAll "^([^=]*)=" ',
                                    '(regexReplaceAll "^\\$[0-9]+\\." . "") "${1}:")}}\n',
                                    "{{end}}",
                                ]
                            )
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    sample = tmp_path / "sample.json"
    sample.write_text(
        '{"TriggerParams":"$1.request_uri=/api/order;$1.error_count=27"}',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "alarm",
            "template",
            "render",
            "--payload",
            f"@{notice}",
            "--sample-context",
            f"@{sample}",
        ],
    )

    assert result.exit_code == 0, result.stdout
    content = json_output(result)["data"]["rendered"]["NoticeContents"][0]["TriggerContent"][
        "Content"
    ]
    assert r"request\_uri:/api/order" in content
    assert r"error\_count:27" in content
    assert "{{" not in content


def test_alarm_policy_scaffold_can_bind_notice_ids(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "policy",
            "scaffold",
            "--scenario",
            "http-5xx",
            "--name",
            "api 5xx",
            "--logset-id",
            "logset-123",
            "--topic-id",
            "topic-123",
            "--notice-id",
            "notice-a",
            "--notice-id",
            "notice-b",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json_output(result)["data"]["payload"]
    assert payload["AlarmNoticeIds"] == ["notice-a", "notice-b"]


def test_alarm_debug_explain_redacts_sensitive_urls(runner, cli_obj, fake_client):
    fake_client.responses = {
        "DescribeAlarms": {"Response": {"Alarms": [{"AlarmId": "alarm-123"}]}},
        "DescribeAlertRecordHistory": {"Response": {"Records": []}},
        "GetAlarmLog": {
            "Response": {
                "Results": [
                    {
                        "LogJson": json.dumps(
                            {
                                "notification_send_result": "SendFail",
                                    "webhook": "https://callback.example.com/hook?key=private-token",
                                    "Authorization": "Bearer abc",
                            }
                        )
                    }
                ]
            }
        },
    }

    result = runner.invoke(
        app,
        [
            "alarm",
            "debug",
            "explain",
            "--region",
            "ap-guangzhou",
            "--alarm-id",
            "alarm-123",
            "--from",
            "1710000000",
            "--to",
            "1710003600",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    raw = json.dumps(json_output(result)["data"]["raw"], ensure_ascii=False)
    assert "private-token" not in raw
    assert "Bearer abc" not in raw
    assert "key=<redacted>" in raw
