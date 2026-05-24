from __future__ import annotations

from cls_cli.cli import app
from tests.conftest import json_output


def test_alarm_policy_create_validates_payload_before_cloud_call(
    runner, cli_obj, fake_client, tmp_path
):
    payload = tmp_path / "policy.json"
    payload.write_text('{"Name":"bad-policy"}', encoding="utf-8")

    result = runner.invoke(
        app,
        ["alarm", "policy", "create", "--region", "ap-shanghai", "--payload", f"@{payload}"],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    assert json_output(result)["error"]["code"] == "INPUT_ERROR"
    assert "missing_alarm_targets" in json_output(result)["error"]["message"]
    assert fake_client.calls == []


def test_alarm_policy_create_can_explicitly_skip_validation(
    runner, cli_obj, fake_client, tmp_path
):
    payload = tmp_path / "policy.json"
    payload.write_text('{"Name":"raw-policy"}', encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "alarm",
            "policy",
            "create",
            "--region",
            "ap-shanghai",
            "--payload",
            f"@{payload}",
            "--skip-validation",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [("CreateAlarm", {"Name": "raw-policy"}, "ap-shanghai")]


def test_alarm_notice_create_validates_payload_before_cloud_call(
    runner, cli_obj, fake_client, tmp_path
):
    payload = tmp_path / "notice.json"
    payload.write_text('{"Name":"bad-notice","NoticeRules":[{}]}', encoding="utf-8")

    result = runner.invoke(
        app,
        ["alarm", "notice", "create", "--region", "ap-shanghai", "--payload", f"@{payload}"],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    assert "notice_rule_target_required" in json_output(result)["error"]["message"]
    assert fake_client.calls == []


def test_alarm_integration_create_payload_is_validated(
    runner, cli_obj, fake_client, tmp_path
):
    payload = tmp_path / "integration.json"
    payload.write_text('{"Name":"bad-hook","Type":"Http"}', encoding="utf-8")

    result = runner.invoke(
        app,
        ["alarm", "integration", "create", "--region", "ap-shanghai", "--payload", f"@{payload}"],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    assert "webhook_required" in json_output(result)["error"]["message"]
    assert fake_client.calls == []


def test_alarm_callback_dry_run_redacts_sensitive_payload(
    runner, cli_obj, fake_client, tmp_path
):
    payload = tmp_path / "callback.json"
    payload.write_text(
        '{"Name":"hook","Type":"Http","Webhook":"https://callback.example.com/hook","Key":"test-signing-key","Method":"POST"}',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "alarm",
            "callback",
            "create",
            "--region",
            "ap-shanghai",
            "--payload",
            f"@{payload}",
            "--dry-run",
            "--skip-validation",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    raw = result.stdout
    assert "private-token" not in raw
    assert "test-signing-key" not in raw
    assert json_output(result)["data"]["payload"]["Webhook"] == "***REDACTED***"
    assert json_output(result)["data"]["payload"]["Key"] == "***REDACTED***"
    assert fake_client.calls == []


def test_alarm_callback_create_validates_payload_before_cloud_call(
    runner, cli_obj, fake_client, tmp_path
):
    payload = tmp_path / "callback.json"
    payload.write_text('{"Name":"bad-callback","Type":"Http"}', encoding="utf-8")

    result = runner.invoke(
        app,
        ["alarm", "callback", "create", "--region", "ap-shanghai", "--payload", f"@{payload}"],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    assert "webhook_required" in json_output(result)["error"]["message"]
    assert fake_client.calls == []


def test_alarm_notice_create_rejects_missing_notification_target(
    runner, cli_obj, fake_client, tmp_path
):
    payload = tmp_path / "notice.json"
    payload.write_text('{"Name":"bad-notice"}', encoding="utf-8")

    result = runner.invoke(
        app,
        ["alarm", "notice", "create", "--region", "ap-shanghai", "--payload", f"@{payload}"],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    assert "notice_target_required" in json_output(result)["error"]["message"]
    assert fake_client.calls == []


def test_alarm_policy_update_validates_payload_before_cloud_call(
    runner, cli_obj, fake_client, tmp_path
):
    payload = tmp_path / "policy.json"
    payload.write_text('{"Name":"bad-policy"}', encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "alarm",
            "policy",
            "update",
            "--region",
            "ap-shanghai",
            "--alarm-id",
            "alarm-123",
            "--payload",
            f"@{payload}",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    assert "missing_alarm_targets" in json_output(result)["error"]["message"]
    assert fake_client.calls == []


def test_alarm_integration_create_dry_run_redacts_sensitive_payload(
    runner, cli_obj, fake_client, tmp_path
):
    payload = tmp_path / "integration.json"
    payload.write_text(
        '{"Name":"hook","Type":"Http","Webhook":"https://callback.example.com/hook","Key":"test-signing-key","Method":"POST"}',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "alarm",
            "integration",
            "create",
            "--region",
            "ap-shanghai",
            "--payload",
            f"@{payload}",
            "--dry-run",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    raw = result.stdout
    assert "private-token" not in raw
    assert "test-signing-key" not in raw
    assert json_output(result)["data"]["payload"]["Webhook"] == "***REDACTED***"
    assert json_output(result)["data"]["payload"]["Key"] == "***REDACTED***"
    assert fake_client.calls == []


def test_alarm_callback_create_redacts_sensitive_response(
    runner, cli_obj, fake_client, tmp_path
):
    payload = tmp_path / "callback.json"
    payload.write_text(
        '{"Name":"hook","Type":"Http","Webhook":"https://callback.example.com/hook","Key":"test-signing-key","Method":"POST"}',
        encoding="utf-8",
    )
    fake_client.responses = {
        "CreateWebCallback": {
            "Response": {
                "Webhook": "https://callback.example.com/hook",
                "Key": "test-signing-key",
                "RequestId": "req-callback",
            }
        }
    }

    result = runner.invoke(
        app,
        ["alarm", "callback", "create", "--region", "ap-shanghai", "--payload", f"@{payload}"],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    raw = result.stdout
    assert "private-token" not in raw
    assert "test-signing-key" not in raw
    assert json_output(result)["data"]["Response"]["Webhook"] == "***REDACTED***"
    assert json_output(result)["data"]["Response"]["Key"] == "***REDACTED***"
