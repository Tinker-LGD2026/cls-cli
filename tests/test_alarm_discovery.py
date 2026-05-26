from __future__ import annotations

from cls_cli.cli import app
from tests.conftest import json_output


def test_alarm_discover_integration_selects_single_name(runner, cli_obj, fake_client):
    fake_client.responses = {
        "DescribeWebCallbacks": {
            "Response": {
                "TotalCount": 1,
                "WebCallbacks": [
                    {"WebCallbackId": "webcallback-123", "Name": "prod-primary-wecom"}
                ],
                "RequestId": "req-1",
            }
        }
    }

    result = runner.invoke(
        app,
        [
            "alarm",
            "discover",
            "integration",
            "--name",
            "prod-primary-wecom",
            "--region",
            "ap-shanghai",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        ("DescribeWebCallbacks", {"Offset": 0, "Limit": 20}, "ap-shanghai")
    ]
    data = json_output(result)["data"]
    assert data == {
        "resource": "integration",
        "match_count": 1,
        "ambiguous": False,
        "selected": {"WebCallbackId": "webcallback-123", "Name": "prod-primary-wecom"},
        "matches": [],
        "request_ids": ["req-1"],
    }


def test_alarm_discover_policy_filters_topic_and_name(runner, cli_obj, fake_client):
    fake_client.responses = {
        "DescribeAlarms": {
            "Response": {
                "TotalCount": 1,
                "Alarms": [{"AlarmId": "alarm-123", "Name": "payment-5xx"}],
                "RequestId": "req-policy",
            }
        }
    }

    result = runner.invoke(
        app,
        [
            "alarm",
            "discover",
            "policy",
            "--name",
            "payment-5xx",
            "--topic-id",
            "topic-xxx",
            "--region",
            "ap-shanghai",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "DescribeAlarms",
            {"Filters": [{"Key": "topicId", "Values": ["topic-xxx"]}], "Offset": 0, "Limit": 100},
            "ap-shanghai",
        )
    ]
    data = json_output(result)["data"]
    assert data["resource"] == "policy"
    assert data["selected"] == {"AlarmId": "alarm-123", "Name": "payment-5xx"}
    assert data["request_ids"] == ["req-policy"]


def test_alarm_discover_ambiguous_matches_fail_unless_allowed(runner, cli_obj, fake_client):
    fake_client.responses = {
        "DescribeWebCallbacks": {
            "Response": {
                "TotalCount": 2,
                "WebCallbacks": [
                    {"WebCallbackId": "webcallback-1", "Name": "prod-wecom"},
                    {"WebCallbackId": "webcallback-2", "Name": "prod-wecom"},
                ],
                "RequestId": "req-ambiguous",
            }
        }
    }

    result = runner.invoke(
        app,
        [
            "alarm",
            "discover",
            "integration",
            "--name",
            "prod-wecom",
            "--region",
            "ap-shanghai",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    data = json_output(result)["data"]
    assert data["ambiguous"] is True
    assert data["selected"] is None
    assert data["match_count"] == 2

    allowed = runner.invoke(
        app,
        [
            "alarm",
            "discover",
            "integration",
            "--name",
            "prod-wecom",
            "--allow-multiple",
            "--region",
            "ap-shanghai",
        ],
        obj=cli_obj,
    )

    assert allowed.exit_code == 0, allowed.stdout
    allowed_data = json_output(allowed)["data"]
    assert allowed_data["ambiguous"] is True
    assert allowed_data["match_count"] == 2
    assert allowed_data["selected"] is None
