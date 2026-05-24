from __future__ import annotations

import json
from pathlib import Path

from cls_cli.core.alarm_policy import has_blocking_policy_issues, validate_policy_payload


def _base_policy() -> dict:
    return {
        "Name": "advanced-policy",
        "AlarmTargets": [
            {
                "TopicId": "topic-xxx",
                "LogsetId": "logset-xxx",
                "Query": "status>=500 | select count(*) as error_count",
                "Number": 1,
                "StartTimeOffset": -5,
                "EndTimeOffset": 0,
                "SyntaxRule": 1,
            }
        ],
        "MonitorTime": {"Type": "Period", "Time": 5},
        "TriggerCount": 1,
        "AlarmPeriod": 15,
        "Condition": "$1.error_count > 100",
        "AlarmLevel": 0,
        "Status": True,
        "MonitorObjectType": 0,
    }


def test_policy_validate_accepts_console_confirmed_advanced_fields():
    policy = _base_policy()
    policy.update(
        {
            "MultiConditions": [
                {
                    "Condition": "[$1.__QUERYCOUNT__]> 100",
                    "ConditionInteractiveConfig": (
                        '{"Value":{"type":"CONDITION","level":0},"Children":[],"id":"config-xxx"}'
                    ),
                    "AlarmLevel": 0,
                }
            ],
            "GroupTriggerStatus": True,
            "GroupTriggerCondition": [],
            "Analysis": [],
            "Classifications": [],
            "MessageTemplate": "{{.Label}}",
            "CallBack": {"Headers": [], "Body": ""},
        }
    )

    issues = validate_policy_payload(policy)

    assert not has_blocking_policy_issues(issues)


def test_policy_validate_rejects_missing_multi_condition_alias():
    policy = _base_policy()
    policy.pop("Condition")
    policy.pop("AlarmLevel")
    policy["MultiConditions"] = [{"Condition": "$1.missing_count > 100", "AlarmLevel": 1}]

    issues = [issue.to_dict() for issue in validate_policy_payload(policy)]

    assert any(issue["code"] == "missing_condition_alias" for issue in issues)


def test_policy_validate_accepts_browser_confirmed_monitor_analysis_classifications():
    policy = _base_policy()
    policy.update(
        {
            "MonitorTime": {"Type": "Cron", "CronExpression": "0/5 * * * *"},
            "Analysis": [
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
            ],
            "Classifications": [
                {"Key": "service", "Value": "payment"},
                {"Key": "env", "Value": "prod"},
            ],
        }
    )

    issues = validate_policy_payload(policy)

    assert not has_blocking_policy_issues(issues)


def test_policy_validate_rejects_invalid_monitor_analysis_classifications():
    policy = _base_policy()
    policy.update(
        {
            "MonitorTime": {"Type": "Bad", "CronExpression": 123},
            "Analysis": [
                {
                    "Name": 1,
                    "Type": "bad",
                    "Content": [],
                    "ConfigInfo": [{"Key": 1, "Value": []}],
                }
            ],
            "Classifications": [
                {"Key": "Service", "Value": "payment"},
                {"Key": "service", "Value": "a" * 201},
                {"Key": "service", "Value": "dup"},
            ],
        }
    )

    issues = [issue.to_dict() for issue in validate_policy_payload(policy)]
    codes = {issue["code"] for issue in issues}

    assert "monitor_time_type_value_invalid" in codes
    assert "monitor_time_cron_expression_invalid" in codes
    assert "analysis_name_invalid" in codes
    assert "analysis_type_invalid" in codes
    assert "analysis_content_invalid" in codes
    assert "analysis_config_key_invalid" in codes
    assert "analysis_config_value_invalid" in codes
    assert "classification_key_invalid" in codes
    assert "classification_value_invalid" in codes
    assert "classification_key_duplicate" in codes


def test_policy_validate_rejects_invalid_advanced_field_shapes():
    policy = _base_policy()
    policy.update(
        {
            "MultiConditions": {"Condition": "$1.error_count > 100"},
            "GroupTriggerStatus": "true",
            "GroupTriggerCondition": {"GroupBy": ["request_uri"]},
            "Analysis": {"Name": "bad"},
            "Classifications": {"Key": "bad"},
            "MessageTemplate": ["bad"],
            "CallBack": [],
        }
    )

    issues = [issue.to_dict() for issue in validate_policy_payload(policy)]
    codes = {issue["code"] for issue in issues}

    assert "multi_conditions_invalid" in codes
    assert "group_trigger_status_invalid" in codes
    assert "group_trigger_condition_invalid" in codes
    assert "analysis_invalid" in codes
    assert "classifications_invalid" in codes
    assert "message_template_invalid" in codes
    assert "callback_invalid" in codes


def test_policy_validate_rejects_invalid_advanced_nested_shapes():
    policy = _base_policy()
    policy.update(
        {
            "MultiConditions": [
                "bad",
                {
                    "Condition": 123,
                    "ConditionInteractiveConfig": "not-json",
                    "AlarmLevel": "0",
                },
            ],
            "Analysis": ["bad"],
            "Classifications": ["bad"],
            "CallBack": {"Headers": "bad", "Body": []},
            "MonitorTime": {"Type": 1, "Time": "1"},
        }
    )

    issues = [issue.to_dict() for issue in validate_policy_payload(policy)]
    codes = {issue["code"] for issue in issues}

    assert "multi_condition_item_invalid" in codes
    assert "multi_condition_condition_invalid" in codes
    assert "multi_condition_config_invalid" in codes
    assert "multi_condition_alarm_level_invalid" in codes
    assert "analysis_item_invalid" in codes
    assert "classification_item_invalid" in codes
    assert "callback_headers_invalid" in codes
    assert "callback_body_invalid" in codes
    assert "monitor_time_type_invalid" in codes
    assert "monitor_time_time_invalid" in codes


def test_policy_validate_accepts_console_confirmed_example_file():
    example = (
        Path(__file__).resolve().parents[1]
        / "examples/alarm-advanced/policy-notice-rules.json"
    )
    payload = json.loads(example.read_text(encoding="utf-8"))

    issues = validate_policy_payload(payload)

    assert not has_blocking_policy_issues(issues)
