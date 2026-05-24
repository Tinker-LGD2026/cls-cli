from __future__ import annotations

import json

from cls_cli.cli import app
from tests.conftest import json_output


def _write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_alarm_validate_bundle_accepts_matching_policy_template_notice_and_integration(
    runner, tmp_path
):
    policy = tmp_path / "policy.json"
    content = tmp_path / "content.json"
    notice = tmp_path / "notice.json"
    integration = tmp_path / "integration.json"
    _write_json(
        policy,
        {
            "AlarmNoticeIds": ["notice-123"],
            "AlarmTargets": [{"Query": "* | select count(*) as fail_count"}],
            "Condition": "$1.fail_count > 10",
        },
    )
    _write_json(
        content,
        {
            "NoticeContentId": "content-123",
            "NoticeContents": [
                {
                    "Type": "Http",
                    "TriggerContent": {
                        "Content": '{"fail_count":"{{escape .QueryResult[0][0].fail_count}}"}'
                    },
                }
            ],
        },
    )
    _write_json(
        notice,
        {
            "AlarmNoticeId": "notice-123",
            "Type": "All",
            "WebCallbacks": [
                {
                    "CallbackType": "Http",
                    "Url": "",
                    "WebCallbackId": "callback-123",
                    "NoticeContentId": "content-123",
                    "Method": "POST",
                }
            ],
        },
    )
    _write_json(
        integration,
        {
            "WebCallbackId": "callback-123",
            "Name": "hook",
            "Type": "Http",
            "Webhook": "https://example.com/hook/private-token",
            "Method": "POST",
        },
    )

    result = runner.invoke(
        app,
        [
            "alarm",
            "validate",
            "bundle",
            "--policy",
            f"@{policy}",
            "--notice-content",
            f"@{content}",
            "--notice",
            f"@{notice}",
            "--integration",
            f"@{integration}",
        ],
    )

    assert result.exit_code == 0, result.stdout
    data = json_output(result)["data"]
    assert data["valid"] is True
    assert data["issues"] == []
    assert data["summary"] == {
        "policy": True,
        "notice_content": True,
        "notice": True,
        "integration": True,
    }


def test_alarm_validate_bundle_accepts_advanced_notice_rule_bindings(runner, tmp_path):
    policy = tmp_path / "policy.json"
    content = tmp_path / "content.json"
    notice = tmp_path / "notice.json"
    integration = tmp_path / "integration.json"
    _write_json(
        policy,
        {
            "AlarmNoticeIds": ["notice-123"],
            "AlarmTargets": [{"Query": "* | select count(*) as fail_count"}],
            "Condition": "$1.fail_count > 10",
        },
    )
    _write_json(
        content,
        {
            "NoticeContentId": "content-123",
            "NoticeContents": [
                {
                    "Type": "WeCom",
                    "TriggerContent": {"Content": "{{escape_markdown .Alarm}}"},
                }
            ],
        },
    )
    _write_json(
        notice,
        {
            "AlarmNoticeId": "notice-123",
            "NoticeRules": [
                {
                    "WebCallbacks": [
                        {
                            "CallbackType": "WeCom",
                            "Url": "",
                            "WebCallbackId": "callback-123",
                            "NoticeContentId": "content-123",
                        }
                    ],
                    "EscalateNotice": {
                        "WebCallbacks": [
                            {
                                "CallbackType": "WeCom",
                                "Url": "",
                                "WebCallbackId": "callback-123",
                                "NoticeContentId": "content-123",
                            }
                        ]
                    },
                }
            ],
        },
    )
    _write_json(
        integration,
        {"WebCallbackId": "callback-123", "Name": "hook", "Type": "WeCom", "Webhook": "https://example.com/hook"},
    )

    result = runner.invoke(
        app,
        [
            "alarm",
            "validate",
            "bundle",
            "--policy",
            f"@{policy}",
            "--notice-content",
            f"@{content}",
            "--notice",
            f"@{notice}",
            "--integration",
            f"@{integration}",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert json_output(result)["data"]["issues"] == []


def test_alarm_validate_bundle_reports_advanced_notice_rule_mismatches(runner, tmp_path):
    content = tmp_path / "content.json"
    notice = tmp_path / "notice.json"
    integration = tmp_path / "integration.json"
    _write_json(content, {"NoticeContentId": "content-expected", "NoticeContents": []})
    _write_json(
        notice,
        {
            "NoticeRules": [
                {
                    "WebCallbacks": [
                        {
                            "CallbackType": "WeCom",
                            "Url": "",
                            "WebCallbackId": "callback-other",
                            "NoticeContentId": "content-other",
                        }
                    ]
                }
            ]
        },
    )
    _write_json(
        integration,
        {"WebCallbackId": "callback-expected", "Name": "hook", "Type": "WeCom", "Webhook": "https://example.com/hook"},
    )

    result = runner.invoke(
        app,
        [
            "alarm",
            "validate",
            "bundle",
            "--notice-content",
            f"@{content}",
            "--notice",
            f"@{notice}",
            "--integration",
            f"@{integration}",
        ],
    )

    assert result.exit_code == 1
    codes = {issue["code"] for issue in json_output(result)["data"]["issues"]}
    assert "notice_content_mismatch" in codes
    assert "integration_mismatch" in codes


def test_alarm_validate_bundle_reports_cross_resource_mismatches(runner, tmp_path):
    policy = tmp_path / "policy.json"
    content = tmp_path / "content.json"
    notice = tmp_path / "notice.json"
    integration = tmp_path / "integration.json"
    _write_json(
        policy,
        {
            "AlarmTargets": [{"Query": "* | select count(*) as fail_count"}],
            "Condition": "$1.fail_count > 10",
        },
    )
    _write_json(
        content,
        {
            "NoticeContentId": "content-expected",
            "NoticeContents": [
                {
                    "Type": "Http",
                    "TriggerContent": {
                        "Content": '{"missing":"{{escape .QueryResult[0][0].other_count}}"}'
                    },
                }
            ],
        },
    )
    _write_json(
        notice,
        {
            "AlarmNoticeId": "notice-expected",
            "Type": "All",
            "WebCallbacks": [
                {
                    "CallbackType": "Http",
                    "Url": "",
                    "WebCallbackId": "callback-other",
                    "NoticeContentId": "content-other",
                    "Method": "POST",
                }
            ],
        },
    )
    _write_json(
        integration,
        {
            "WebCallbackId": "callback-expected",
            "Name": "hook",
            "Type": "Http",
            "Webhook": "https://example.com/hook",
            "Method": "POST",
        },
    )

    result = runner.invoke(
        app,
        [
            "alarm",
            "validate",
            "bundle",
            "--policy",
            f"@{policy}",
            "--notice-content",
            f"@{content}",
            "--notice",
            f"@{notice}",
            "--integration",
            f"@{integration}",
        ],
    )

    assert result.exit_code == 1
    issues = json_output(result)["data"]["issues"]
    codes = {issue["code"] for issue in issues}
    assert "policy_notice_missing" in codes
    assert "missing_query_alias" in codes
    assert "notice_content_mismatch" in codes
    assert "integration_mismatch" in codes
