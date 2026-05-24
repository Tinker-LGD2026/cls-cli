from __future__ import annotations

import json
import re
import time
from typing import Any

from cls_cli.core.input import parse_timestamp_ms

SENSITIVE_KEY_RE = re.compile(r"secret|token|authorization|signature|credential|password|key", re.I)
SENSITIVE_QUERY_RE = re.compile(
    r"([?&](?:key|token|access_token|signature|secret|secret_key)=)[^&\"'\\\s]+",
    re.I,
)
BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.I)


def test_policy_queries(
    client: Any,
    policy: dict[str, Any],
    region: str,
    from_ms: int,
    to_ms: int,
    limit: int,
) -> dict[str, Any]:
    query_results: list[list[dict[str, Any]]] = []
    query_logs: list[list[dict[str, Any]]] = []
    raw_responses: list[dict[str, Any]] = []
    targets = policy.get("AlarmTargets")
    if not isinstance(targets, list):
        targets = []
    for target in targets:
        if not isinstance(target, dict):
            continue
        response = client.invoke(
            "SearchLog",
            {
                "TopicId": target.get("TopicId"),
                "QueryString": target.get("Query"),
                "From": from_ms,
                "To": to_ms,
                "Limit": limit,
            },
            region,
        )
        raw_responses.append(response)
        query_results.append(analysis_records(response))
        query_logs.append(query_logs_from_response(response))
    condition = policy.get("Condition") or multi_condition_summary(policy)
    return {
        "sample_context": {
            "Alarm": policy.get("Name", ""),
            "AlarmID": policy.get("AlarmId", ""),
            "Condition": condition,
            "QueryResult": query_results,
            "TriggerResult": query_results,
            "QueryLog": query_logs,
        },
        "condition_preview": {"condition": condition, "likely_trigger": None},
        "raw": {"search_responses": raw_responses},
    }


def debug_window(from_time: str | None, to_time: str | None, hours: int) -> tuple[int, int]:
    to_ms = parse_timestamp_ms(to_time, "to") or int(time.time() * 1000)
    from_ms = parse_timestamp_ms(from_time, "from") or to_ms - hours * 60 * 60 * 1000
    return from_ms, to_ms


def analysis_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    response = payload.get("Response", {})
    records = response.get("AnalysisRecords") or response.get("AnalysisResults")
    if isinstance(records, list) and records:
        return [parse_json_object(record) for record in records]
    return [
        row["content"]
        for row in query_logs_from_response(payload)
        if isinstance(row.get("content"), dict)
    ]


def query_logs_from_response(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in response_list(payload, "Results"):
        if not isinstance(item, dict):
            continue
        content = parse_json_object(item.get("LogJson"))
        rows.append(
            {
                "content": content,
                "time": item.get("Time"),
                "source": item.get("Source", ""),
                "fileName": item.get("FileName", ""),
                "topicId": item.get("TopicId", ""),
            }
        )
    return rows


def parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return {"raw": value}
        return loaded if isinstance(loaded, dict) else {"value": loaded}
    return {}


def multi_condition_summary(policy: dict[str, Any]) -> str:
    conditions = policy.get("MultiConditions")
    if not isinstance(conditions, list):
        return ""
    values = [item.get("Condition") for item in conditions if isinstance(item, dict)]
    return "; ".join(str(value) for value in values if value)


def explain_debug(
    policy: dict[str, Any], history: dict[str, Any], execution_log: dict[str, Any]
) -> dict[str, Any]:
    alarms = response_list(policy, "Alarms")
    records = response_list(history, "Records")
    logs = parsed_alarm_logs(execution_log)
    causes: list[str] = []
    next_actions: list[str] = []
    if not alarms:
        return {
            "summary": "未找到告警策略，请确认 alarm-id、地域和权限。",
            "probable_causes": ["告警策略不存在或当前账号无权限访问"],
            "next_actions": [
                "调用 cls alarm policy list 检查策略 ID",
                "确认 --region 与资源地域一致",
            ],
            "raw": sanitize_sensitive(
                {"policy": policy, "history": history, "execution_log": execution_log}
            ),
        }
    for item in logs:
        if item.get("condition_evaluate_result") == "QueryResultUnmatch":
            causes.append("查询结果未满足触发条件")
            next_actions.append("复查告警策略 Query 和 Condition，确认 SQL alias 与条件字段一致")
        notify_result = str(item.get("notification_send_result") or "")
        if notify_result in {"SendFail", "SendPartFail"}:
            causes.append("通知发送失败")
            next_actions.append("检查通知渠道组、通知模板、回调地址和接收人配置")
        if item.get("process_error_msg"):
            causes.append(str(item["process_error_msg"]))
    if not records and not logs:
        summary = "告警策略存在，但所选时间窗口内没有执行详情或告警历史。"
        next_actions.append("扩大 --from/--to 时间范围，或确认 MonitorTime 调度周期")
    elif "查询结果未满足触发条件" in causes:
        summary = "告警策略存在，但最近执行结果未满足触发条件。"
    elif any(cause in {"通知发送失败"} for cause in causes):
        summary = "告警策略已触发，但通知链路存在失败。"
    else:
        summary = "告警策略存在，未发现明确执行异常。"
    return {
        "summary": summary,
        "probable_causes": list(dict.fromkeys(causes)),
        "next_actions": list(dict.fromkeys(next_actions)),
        "raw": sanitize_sensitive(
            {"policy": policy, "history": history, "execution_log": execution_log}
        ),
    }


def sanitize_sensitive(value: Any, key: str | None = None) -> Any:
    if key and SENSITIVE_KEY_RE.search(key):
        return "<redacted>"
    if isinstance(value, dict):
        return {
            item_key: sanitize_sensitive(item_value, item_key)
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [sanitize_sensitive(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                loaded = json.loads(value)
            except json.JSONDecodeError:
                pass
            else:
                return json.dumps(sanitize_sensitive(loaded), ensure_ascii=False)
        value = SENSITIVE_QUERY_RE.sub(lambda match: f"{match.group(1)}<redacted>", value)
        return BEARER_RE.sub("Bearer <redacted>", value)
    return value


def response_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get("Response", {}).get(key)
    return value if isinstance(value, list) else []


def parsed_alarm_logs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for item in response_list(payload, "Results"):
        if not isinstance(item, dict):
            continue
        raw = item.get("LogJson")
        if isinstance(raw, str):
            try:
                loaded = json.loads(raw)
            except json.JSONDecodeError:
                loaded = {"raw": raw}
            if isinstance(loaded, dict):
                parsed.append(loaded)
    return parsed


def filters(values: dict[str, str | None]) -> list[dict[str, str | list[str]]]:
    result: list[dict[str, str | list[str]]] = []
    for key, value in values.items():
        if value:
            result.append({"Key": key, "Values": [value]})
    return result


def alarm_log_query(alarm_id: str | None, topic_id: str | None) -> str | None:
    parts: list[str] = []
    if alarm_id:
        parts.append(f'alert_id:"{alarm_id}"')
    if topic_id:
        parts.append(f'monitored_object:"{topic_id}"')
    return " AND ".join(parts) if parts else None
