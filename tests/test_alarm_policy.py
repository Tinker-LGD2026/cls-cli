from __future__ import annotations

import json

from cls_cli.cli import app
from tests.conftest import json_output


def test_policy_validate_accepts_query_alias_and_condition_reference(runner, tmp_path):
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "AlarmTargets": [
                    {
                        "Query": (
                            "status:>=500 | select count(*) as error_count, "
                            "request_uri group by request_uri"
                        )
                    }
                ],
                "Condition": "$1.error_count > 10",
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["alarm", "policy", "validate", "--payload", f"@{policy}"])

    assert result.exit_code == 0, result.stdout
    data = json_output(result)["data"]
    assert data["valid"] is True
    assert data["issues"] == []


def test_policy_validate_rejects_missing_condition_alias(runner, tmp_path):
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "AlarmTargets": [{"Query": "status:>=500 | select count(*) as error_count"}],
                "Condition": "$1.fail_count > 10",
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["alarm", "policy", "validate", "--payload", f"@{policy}"])

    assert result.exit_code == 1
    data = json_output(result)["data"]
    assert data["valid"] is False
    assert any(issue["code"] == "missing_condition_alias" for issue in data["issues"])


def test_policy_scaffold_accepts_ai_generated_query_and_condition(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "policy",
            "scaffold",
            "--name",
            "payment failures",
            "--logset-id",
            "logset-123",
            "--topic-id",
            "topic-123",
            "--query",
            "service:payment | select count(*) as fail_count",
            "--condition",
            "$1.fail_count > 10",
            "--notice-id",
            "notice-123",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json_output(result)["data"]["payload"]
    assert payload["AlarmTargets"][0]["Query"] == (
        "service:payment | select count(*) as fail_count"
    )
    assert payload["Condition"] == "$1.fail_count > 10"
    assert payload["AlarmNoticeIds"] == ["notice-123"]
    assert payload["MonitorTime"] == {"Type": "Period", "Time": 1}
    assert payload["AlarmPeriod"] == 15


def test_policy_scaffold_accepts_explicit_alarm_period_for_query_mode(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "policy",
            "scaffold",
            "--name",
            "payment failures",
            "--logset-id",
            "logset-123",
            "--topic-id",
            "topic-123",
            "--query",
            "service:payment | select count(*) as fail_count",
            "--condition",
            "$1.fail_count > 10",
            "--monitor-period",
            "2",
            "--alarm-period",
            "60",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json_output(result)["data"]["payload"]
    assert payload["MonitorTime"] == {"Type": "Period", "Time": 2}
    assert payload["AlarmPeriod"] == 60


def test_policy_validate_rejects_invalid_generated_alias(runner, tmp_path):
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "AlarmTargets": [{"Query": "* | select count(*) as `bad alias`"}],
                "Condition": "$1.bad_alias > 1",
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["alarm", "policy", "validate", "--payload", f"@{policy}"])

    assert result.exit_code == 1
    data = json_output(result)["data"]
    assert any(issue["code"] == "invalid_alias_identifier" for issue in data["issues"])


def test_policy_scaffold_loads_advanced_json_fields(runner, tmp_path):
    multi = tmp_path / "multi.json"
    analysis = tmp_path / "analysis.json"
    callback = tmp_path / "callback.json"
    multi.write_text('[{"Condition":"$1.fail_count > 10"}]', encoding="utf-8")
    analysis.write_text('[{"Name":"top_uri","Query":"* | select count(*) as c"}]', encoding="utf-8")
    callback.write_text('{"Body":"{\\"alarm\\":\\"{{.Alarm}}\\"}"}', encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "alarm",
            "policy",
            "scaffold",
            "--name",
            "advanced",
            "--logset-id",
            "logset-123",
            "--topic-id",
            "topic-123",
            "--query",
            "* | select count(*) as fail_count",
            "--condition",
            "$1.fail_count > 0",
            "--multi-condition",
            f"@{multi}",
            "--group-trigger-status",
            "true",
            "--analysis",
            f"@{analysis}",
            "--message-template",
            "runbook: check payment",
            "--callback",
            f"@{callback}",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json_output(result)["data"]["payload"]
    assert payload["MultiConditions"] == [{"Condition": "$1.fail_count > 10"}]
    assert payload["GroupTriggerStatus"] is True
    assert payload["Analysis"] == [{"Name": "top_uri", "Query": "* | select count(*) as c"}]
    assert payload["MessageTemplate"] == "runbook: check payment"
    assert payload["CallBack"] == {"Body": '{"alarm":"{{.Alarm}}"}'}


def test_policy_scaffold_builds_advanced_policy_options(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "policy",
            "scaffold",
            "--name",
            "advanced generated",
            "--logset-id",
            "logset-123",
            "--topic-id",
            "topic-123",
            "--query",
            (
                'host:"a.example.com" AND status>=500 | select count(*) as '
                "error_count, request_uri, status group by request_uri,status"
            ),
            "--condition",
            "$1.error_count > 100",
            "--multi-condition-expr",
            "$1.error_count > 100",
            "--multi-condition-level",
            "1",
            "--multi-condition-expr",
            "$1.error_count > 500",
            "--multi-condition-level",
            "2",
            "--group-by",
            "request_uri,status",
            "--callback-body",
            '{"alarm":"{{.Alarm}}"}',
            "--callback-header",
            "Content-Type: application/json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json_output(result)["data"]["payload"]
    assert payload["MultiConditions"] == [
        {"Condition": "$1.error_count > 100", "AlarmLevel": 1},
        {"Condition": "$1.error_count > 500", "AlarmLevel": 2},
    ]
    assert "Condition" not in payload
    assert "AlarmLevel" not in payload
    assert payload["GroupTriggerStatus"] is True
    assert payload["GroupTriggerCondition"] == ["request_uri", "status"]
    assert payload["CallBack"] == {
        "Body": '{"alarm":"{{.Alarm}}"}',
        "Headers": ["Content-Type: application/json"],
    }


def test_policy_scaffold_builds_browser_confirmed_monitor_analysis_classifications(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "policy",
            "scaffold",
            "--name",
            "browser confirmed",
            "--logset-id",
            "logset-123",
            "--topic-id",
            "topic-123",
            "--query",
            "* | select count(*) as error_count",
            "--condition",
            "$1.error_count > 0",
            "--monitor-type",
            "cron",
            "--cron-expression",
            "0/5 * * * *",
            "--analysis-query",
            "custom query=* | select count(*) as count",
            "--analysis-original-fields",
            "__SOURCE__,__HOSTNAME__,__TIMESTAMP__,__PKG_LOGID__",
            "--classification",
            "service=payment",
            "--classification",
            "env=prod",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json_output(result)["data"]["payload"]
    assert payload["MonitorTime"] == {"Type": "Cron", "CronExpression": "0/5 * * * *"}
    assert payload["Analysis"] == [
        {
            "Name": "custom query",
            "Type": "query",
            "Content": "* | select count(*) as count",
            "ConfigInfo": [{"Key": "SyntaxRule", "Value": "1"}],
        },
        {
            "Name": "original logs",
            "Type": "original",
            "Content": "raw logs",
            "ConfigInfo": [
                {
                    "Key": "Fields",
                    "Value": "__SOURCE__,__HOSTNAME__,__TIMESTAMP__,__PKG_LOGID__",
                },
                {"Key": "QueryIndex", "Value": "1"},
                {"Key": "Format", "Value": "2"},
                {"Key": "Limit", "Value": "5"},
                {"Key": "SyntaxRule", "Value": "1"},
            ],
        },
    ]
    assert payload["Classifications"] == [
        {"Key": "service", "Value": "payment"},
        {"Key": "env", "Value": "prod"},
    ]


def test_policy_scaffold_rejects_unsafe_group_by_field(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "policy",
            "scaffold",
            "--name",
            "unsafe group",
            "--logset-id",
            "logset-123",
            "--topic-id",
            "topic-123",
            "--query",
            "* | select count(*) as error_count",
            "--condition",
            "$1.error_count > 0",
            "--group-by",
            "request_uri; drop",
        ],
    )

    assert result.exit_code == 1
    assert "invalid_field_name" in result.stdout


def test_policy_scaffold_rejects_unsafe_generated_field(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "policy",
            "scaffold",
            "--name",
            "unsafe fields",
            "--logset-id",
            "logset-123",
            "--topic-id",
            "topic-123",
            "--fields",
            "request_uri,field\nname",
        ],
    )

    assert result.exit_code == 1
    assert "invalid_field_name" in result.stdout


def test_policy_scaffold_rejects_mismatched_multi_condition_levels(runner):
    result = runner.invoke(
        app,
        [
            "alarm",
            "policy",
            "scaffold",
            "--name",
            "advanced generated",
            "--logset-id",
            "logset-123",
            "--topic-id",
            "topic-123",
            "--query",
            "* | select count(*) as error_count",
            "--condition",
            "$1.error_count > 100",
            "--multi-condition-expr",
            "$1.error_count > 100",
            "--multi-condition-level",
            "1",
            "--multi-condition-level",
            "2",
        ],
    )

    assert result.exit_code == 1
    assert "--multi-condition-level count must match" in result.stdout
