from __future__ import annotations

import json
from pathlib import Path

from cls_cli.core.alarm_integrations import validate_notice_payload


def test_notice_validate_accepts_console_confirmed_notice_rules():
    payload = {
        "Name": "advanced-notice",
        "Type": "",
        "NoticeReceivers": [],
        "WebCallbacks": [],
        "NoticeRules": [
            {
                "Rule": (
                    '{"Value":"AND","Type":"Operation","Children":['
                    '{"Type":"Condition","Value":"NotifyType","Children":['
                    '{"Value":"In","Type":"Compare"},'
                    '{"Value":"[1,2]","Type":"Value"}]}]}'
                ),
                "NoticeReceivers": [
                    {
                        "ReceiverType": "Uin",
                        "ReceiverIds": [1000001],
                        "ReceiverChannels": ["Email"],
                        "StartTime": "00:00:00",
                        "EndTime": "23:59:59",
                        "Index": 1,
                        "NoticeContentId": "",
                    }
                ],
                "WebCallbacks": [],
                "Escalate": False,
            }
        ],
        "CallbackPrioritize": False,
    }

    assert validate_notice_payload(payload) == []



def test_notice_validate_accepts_notice_rules_with_web_callback():
    payload = {
        "Name": "advanced-notice",
        "NoticeRules": [
            {
                "WebCallbacks": [
                    {
                        "CallbackType": "WeCom",
                        "WebCallbackId": "webcallback-xxx",
                        "NoticeContentId": "notice-template-xxx",
                        "Url": "",
                    }
                ]
            }
        ],
    }

    assert validate_notice_payload(payload) == []


def test_notice_validate_accepts_notice_rules_with_escalation_object():
    payload = {
        "Name": "advanced-notice",
        "NoticeRules": [
            {
                "EscalateNotice": {
                    "WebCallbacks": [
                        {
                            "CallbackType": "WeCom",
                            "WebCallbackId": "webcallback-escalate",
                            "NoticeContentId": "notice-template-escalate",
                            "Url": "",
                        }
                    ]
                }
            }
        ],
    }

    assert validate_notice_payload(payload) == []


def test_notice_validate_rejects_invalid_notice_rule_shapes():
    payload = {
        "Name": "advanced-notice",
        "NoticeRules": [
            {
                "NoticeReceivers": "bad",
                "WebCallbacks": "bad",
                "EscalateNotice": "bad",
            }
        ],
    }

    issues = validate_notice_payload(payload)
    codes = {issue["code"] for issue in issues}

    assert "notice_receivers_invalid" in codes
    assert "notice_webcallbacks_invalid" in codes
    assert "escalate_notice_invalid" in codes


def test_notice_validate_rejects_invalid_time_window_shape():
    payload = {
        "Name": "advanced-notice",
        "NoticeRules": [
            {
                "WebCallbacks": [
                    {
                        "CallbackType": "WeCom",
                        "WebCallbackId": "webcallback-xxx",
                        "NoticeContentId": "notice-template-xxx",
                        "Url": "",
                    }
                ],
                "NotifyTimeRange": 123,
            }
        ],
    }

    issues = validate_notice_payload(payload)
    codes = {issue["code"] for issue in issues}

    assert "notice_time_window_invalid" in codes


def test_notice_validate_rejects_invalid_console_confirmed_nested_shapes():
    payload = {
        "Name": "advanced-notice",
        "CallbackPrioritize": "false",
        "NoticeRules": [
            {
                "Rule": {"bad": True},
                "NoticeReceivers": [
                    {
                        "ReceiverType": 123,
                        "ReceiverIds": "1000001",
                        "ReceiverChannels": "Email",
                        "StartTime": 0,
                        "EndTime": [],
                        "Index": "1",
                        "NoticeContentId": 123,
                    }
                ],
                "WebCallbacks": ["bad"],
                "Escalate": "false",
                "EscalateNotice": {
                    "NoticeReceivers": "bad",
                    "WebCallbacks": "bad",
                    "Escalate": "true",
                    "Interval": "10",
                    "Type": "1",
                },
            }
        ],
    }

    issues = validate_notice_payload(payload)
    codes = {issue["code"] for issue in issues}

    assert "callback_prioritize_invalid" in codes
    assert "notice_rule_expr_invalid" in codes
    assert "notice_receiver_type_invalid" in codes
    assert "notice_receiver_ids_invalid" in codes
    assert "notice_receiver_channels_invalid" in codes
    assert "notice_receiver_start_time_invalid" in codes
    assert "notice_receiver_end_time_invalid" in codes
    assert "notice_receiver_index_invalid" in codes
    assert "notice_receiver_content_id_invalid" in codes
    assert "notice_webcallback_item_invalid" in codes
    assert "notice_escalate_invalid" in codes
    assert "escalate_notice_receivers_invalid" in codes
    assert "escalate_notice_webcallbacks_invalid" in codes
    assert "escalate_notice_escalate_invalid" in codes
    assert "escalate_notice_interval_invalid" in codes
    assert "escalate_notice_type_invalid" in codes


def test_notice_validate_accepts_console_confirmed_example_file():
    example = (
        Path(__file__).resolve().parents[1]
        / "examples/alarm-advanced/notice-rules-advanced.json"
    )
    payload = json.loads(example.read_text(encoding="utf-8"))

    assert validate_notice_payload(payload) == []
