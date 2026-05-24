from __future__ import annotations

import json
import os
from typing import Any
from urllib.request import Request, urlopen

import typer

from cls_cli.core.alarm_templates import (
    generate_notice_template,
    render_notice_template,
    split_fields,
    validate_notice_template,
)
from cls_cli.core.errors import CliError, InputError
from cls_cli.core.input import load_json_payload
from cls_cli.core.output import emit_data, emit_error

app = typer.Typer(no_args_is_help=True, help="Generate and validate alarm notice templates.")


@app.command("generate")
def generate_template(
    scenario: str = typer.Option("http-5xx", "--scenario"),
    channel: str = typer.Option("email", "--channel"),
    fields: str | None = typer.Option(None, "--fields"),
    name: str | None = typer.Option(None, "--name"),
    language: str = typer.Option("zh", "--language"),
    output: str = typer.Option("json", "--output"),
) -> None:
    payload = generate_notice_template(
        scenario=scenario,
        channel=channel,
        fields=split_fields(fields, ["request_uri", "status", "error_count"]),
        name=name,
        language=language,
    )
    emit_data({"payload": payload}, output)


@app.command("render")
def render_template(
    payload: str = typer.Option(..., "--payload"),
    sample_context: str = typer.Option(..., "--sample-context"),
    output: str = typer.Option("json", "--output"),
) -> None:
    notice = load_json_payload(payload)
    context = load_json_payload(sample_context)
    emit_data({"rendered": render_notice_template(notice, context)}, output)


@app.command("send-test")
def send_test_template(
    payload: str = typer.Option(..., "--payload"),
    sample_context: str = typer.Option(..., "--sample-context"),
    robot: str = typer.Option("wecom", "--robot"),
    webhook_url_env: str = typer.Option(
        "CLS_ALARM_TEST_WEBHOOK_URL", "--webhook-url-env"
    ),
    timeout: int = typer.Option(10, "--timeout"),
    output: str = typer.Option("json", "--output"),
) -> None:
    try:
        notice = load_json_payload(payload)
        context = load_json_payload(sample_context)
        rendered = render_notice_template(notice, context)
        response = send_robot_message(rendered, robot, webhook_url_env, timeout)
        emit_data({"sent": _robot_response_ok(response), "response": response}, output)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


@app.command("validate")
def validate_template(
    payload: str = typer.Option(..., "--payload"),
    policy_payload: str | None = typer.Option(None, "--policy-payload"),
    output: str = typer.Option("json", "--output"),
) -> None:
    notice = load_json_payload(payload)
    policy = load_json_payload(policy_payload) if policy_payload else None
    issues = validate_notice_template(notice, policy)
    emit_data({"valid": not issues, "issues": [issue.to_dict() for issue in issues]}, output)
    if issues:
        raise typer.Exit(1)


def send_robot_message(
    rendered_notice: dict[str, Any], robot: str, webhook_url_env: str, timeout: int
) -> dict[str, Any]:
    webhook_url = os.environ.get(webhook_url_env)
    if not webhook_url:
        raise InputError(f"environment variable `{webhook_url_env}` is required")
    trigger = _first_trigger_content(rendered_notice)
    title = str(trigger.get("Title") or "CLS 告警模板测试")
    content = str(trigger.get("Content") or "")
    normalized = robot.lower()
    if normalized == "wecom":
        message = {"msgtype": "markdown", "markdown": {"content": f"**{title}**\n{content}"}}
    elif normalized == "feishu":
        message = _feishu_card_message(title, content)
    else:
        raise InputError(f"unsupported robot type: {robot}")
    return _post_json(webhook_url, message, timeout)


def _feishu_card_message(title: str, content: str) -> dict[str, Any]:
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "red",
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": content}},
            ],
        },
    }


def _post_json(webhook_url: str, message: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = Request(
        webhook_url,
        data=json.dumps(message, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    loaded = json.loads(raw)
    return loaded if isinstance(loaded, dict) else {"raw": loaded}


def _robot_response_ok(response: dict[str, Any]) -> bool:
    return response.get("errcode") == 0 or response.get("code") == 0


def _first_trigger_content(rendered_notice: dict[str, Any]) -> dict[str, Any]:
    contents = rendered_notice.get("NoticeContents")
    if not isinstance(contents, list) or not contents:
        raise InputError("notice payload must contain NoticeContents")
    first = contents[0]
    if not isinstance(first, dict):
        raise InputError("notice payload must contain TriggerContent")
    trigger_content = first.get("TriggerContent")
    if not isinstance(trigger_content, dict):
        raise InputError("notice payload must contain TriggerContent")
    return trigger_content
