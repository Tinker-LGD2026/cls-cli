from __future__ import annotations

from typing import Any

from cls_cli.core.alarm_policy import validate_generated_field_names
from cls_cli.core.errors import InputError


def generate_notice_template(
    *, scenario: str, channel: str, fields: list[str], name: str | None, language: str
) -> dict[str, Any]:
    scenario = scenario.lower()
    normalized_channel = channel.lower()
    channel_type = _channel_type(channel)
    title = "【{{.Level_zh}}】{{.Alarm}}" if language == "zh" else "[{{.Level}}] {{.Alarm}}"
    recovery_alarm = "{{.Alarm}}"
    if normalized_channel in {"wecom", "feishu"}:
        escape_fn = "escape_markdown" if normalized_channel == "wecom" else "escape_markdown_html"
        max_length = 3500 if normalized_channel == "wecom" else 7000
        content = _robot_markdown_content(fields, escape_fn, max_length)
        recovery_alarm = "{{" + escape_fn + " .Alarm}}"
        headers = []
    elif channel_type == "Http":
        content = _webhook_content(fields)
        recovery_alarm = "{{escape .Alarm}}"
        headers = ["Content-Type:application/json"]
    else:
        content = _text_content(scenario, fields)
        headers = []
    return {
        "Name": name or f"{scenario}-{channel}-notice-content",
        "Type": 0 if language == "zh" else 1,
        "NoticeContents": [
            {
                "Type": channel_type,
                "TriggerContent": {"Title": title, "Content": content, "Headers": headers},
                "RecoveryContent": {
                    "Title": _recovery_title(language, recovery_alarm),
                    "Content": _recovery_content(recovery_alarm),
                    "Headers": headers,
                },
            }
        ],
    }


def scaffold_alarm_policy(
    *,
    scenario: str,
    name: str,
    logset_id: str,
    topic_id: str,
    threshold: int,
    window_minutes: int,
    fields: list[str],
    notice_ids: list[str] | None = None,
) -> dict[str, Any]:
    scenario = scenario.lower()
    validate_generated_field_names(fields, path="fields")
    if scenario != "http-5xx":
        raise InputError(f"unsupported alarm policy scenario: {scenario}")
    group_fields = [field for field in fields if field != "error_count"]
    select_parts = ["count(*) as error_count", *group_fields]
    query = f"status:>=500 | select {', '.join(select_parts)}"
    if group_fields:
        query += f" group by {','.join(group_fields)}"
    query += " order by error_count desc limit 10"
    payload: dict[str, Any] = {
        "Name": name,
        "AlarmTargets": [
            {
                "Query": query,
                "Number": 1,
                "StartTimeOffset": -window_minutes,
                "EndTimeOffset": 0,
                "SyntaxRule": 1,
                "LogsetId": logset_id,
                "TopicId": topic_id,
            }
        ],
        "MonitorTime": {"Type": "Period", "Time": max(1, min(window_minutes, 60))},
        "TriggerCount": 1,
        "AlarmPeriod": 15,
        "Condition": f"$1.error_count > {threshold}",
        "AlarmLevel": 0,
        "Status": True,
        "MonitorObjectType": 0,
    }
    if notice_ids:
        payload["AlarmNoticeIds"] = notice_ids
    return payload


def split_fields(value: str | None, default: list[str]) -> list[str]:
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def _recovery_title(language: str, recovery_alarm: str) -> str:
    return f"【恢复】{recovery_alarm}" if language == "zh" else f"[Recovered] {recovery_alarm}"


def _recovery_content(recovery_alarm: str) -> str:
    return f"告警已恢复\n告警策略：{recovery_alarm}\n恢复时间：{{{{.NotifyTime}}}}"


def _channel_type(channel: str) -> str:
    normalized = channel.lower()
    mapping = {
        "email": "Email",
        "sms": "Sms",
        "wechat": "WeChat",
        "phone": "Phone",
        "webhook": "Http",
        "http": "Http",
        "wecom": "WeCom",
        "feishu": "Lark",
        "lark": "Lark",
        "dingtalk": "DingTalk",
    }
    if normalized not in mapping:
        raise InputError(f"unsupported notice channel: {channel}")
    return mapping[normalized]


def _robot_markdown_content(fields: list[str], escape_fn: str, max_length: int) -> str:
    labels = {"request_uri": "URI", "error_count": "错误数", "status": "状态码"}
    row_parts = [
        f"{labels.get(field, field)}={{{{{escape_fn} .{field}}}}}" for field in fields
    ]
    result_row = " | ".join(row_parts)
    body = "\n".join(
        [
            '{{- define "subTemplate" -}}',
            f"# 【告警】{{{{{escape_fn} .Alarm}}}}",
            "",
            "## 告警概览",
            "- 告警级别：{{.Level_zh}}",
            "- 所属账号：{{.UIN}}({{" + escape_fn + " .Nickname}})",
            "- 地域：{{.Region}}",
            "- 日志主题：{{" + escape_fn + " .Topic}}",
            "- 触发条件：{{" + escape_fn + " .Condition}}",
            "- 首次触发：{{.StartTime}}",
            "- 本次通知：{{.NotifyTime}}",
            "- 连续次数：{{.ConsecutiveAlertNums}}",
            "",
            "{{if .TriggerParams}}",
            "## 触发参数",
            "{{" + escape_fn + " .TriggerParams}}",
            "{{end}}",
            "",
            "## 命中结果",
            "{{range .QueryResult[0]}}",
            "- " + result_row,
            "{{end}}",
            "",
            "{{if .AnalysisResultFormat_zh}}",
            "## 多维分析",
            "{{.AnalysisResultFormat_zh}}",
            "{{end}}",
            '{{- end -}}',
            "",
            f'{{{{- substr (renderTemplate "subTemplate") 0 {max_length}}}}}',
            "",
            "[详细报告]({{.DetailUrl}}) [查询数据]({{.QueryUrl}})"
            "{{if .CanSilent}} [屏蔽告警]({{.SilentUrl}}){{end}}",
        ]
    )
    return body


def _webhook_content(fields: list[str]) -> str:
    field_lines = [
        f'    "{field}": "{{{{escape .TriggerResult[0][0].{field}}}}}"'
        for field in fields
    ]
    custom_fields = ",\n".join(field_lines)
    if custom_fields:
        custom_fields = ",\n  \"fields\": {\n" + custom_fields + "\n  }"
    return (
        "{\n"
        '  "record_id": "{{escape .RecordId}}",\n'
        '  "alarm": "{{escape .Alarm}}",\n'
        '  "alarm_id": "{{escape .AlarmID}}",\n'
        '  "level": "{{escape .Level_zh}}",\n'
        '  "condition": "{{escape .Condition}}",\n'
        '  "trigger_result": {{toPrettyJson .TriggerResult}}'
        f"{custom_fields}\n"
        "}"
    )


def _text_content(scenario: str, fields: list[str]) -> str:
    lines = [
        "告警策略：{{.Alarm}}",
        "告警级别：{{.Level_zh}}",
        "触发条件：{{.Condition}}",
        "通知时间：{{.NotifyTime}}",
        "日志主题：{{.Topic}}",
        "",
        "触发结果：",
        "{{range .TriggerResult[0]}}",
    ]
    for field in fields:
        lines.append(f"- {field}: {{{{.{field}}}}}")
    lines.extend(["{{end}}", "", "详情：{{.DetailUrl}}", "查询：{{.QueryUrl}}"])
    if scenario == "raw-log":
        lines.insert(-2, "最近日志：{{toPrettyJson .QueryLog[0][0].content}}")
    return "\n".join(lines)
