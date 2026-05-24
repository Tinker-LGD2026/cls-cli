from __future__ import annotations

import json
import os
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, cast

from cls_cli.core.alarm_integrations import normalize_callback_type
from cls_cli.core.alarm_templates import (
    generate_notice_template,
    render_notice_template,
    scaffold_alarm_policy,
    validate_notice_template,
)
from cls_cli.core.errors import ConfirmationRequired

E2E_ALLOWED_ACTIONS = [
    "CreateLogset",
    "CreateTopic",
    "CreateIndex",
    "UploadLog",
    "SearchLog",
    "DescribeLogHistogram",
    "SearchLog",
    "CreateNoticeContent",
    "CreateWebCallback",
    "CreateAlarmNotice",
    "CreateAlarm",
    "DescribeAlertRecordHistory",
    "GetAlarmLog",
    "DeleteAlarm",
    "DeleteAlarmNotice",
    "DeleteWebCallback",
    "DeleteNoticeContent",
    "DeleteIndex",
    "DeleteTopic",
    "DeleteLogset",
]

RobotSender = Callable[[dict[str, Any], str, str, int], dict[str, Any]]


@dataclass(frozen=True)
class AlarmE2EOptions:
    confirm_real_write: bool = False
    run_id: str | None = None
    name_prefix: str = "cls-cli-alarm-e2e"
    poll_seconds: int = 600
    poll_interval_seconds: int = 30
    cleanup: bool = True
    send_wecom: bool = False
    send_feishu: bool = False
    robot_timeout: int = 10
    notice_ids: list[str] | None = None
    advanced: bool = False


def plan_alarm_e2e(region: str, options: AlarmE2EOptions) -> dict[str, Any]:
    return {
        "dry_run": True,
        "region": region,
        "run_id": options.run_id or _new_run_id(),
        "scope": "alarm-only; logset/topic/index/logs plus alarm templates/policy/debug",
        "advanced": options.advanced,
        "planned_actions": E2E_ALLOWED_ACTIONS,
        "excluded_actions": [
            "CreateMachineGroup",
            "CreateConfig",
            "ApplyConfigToMachineGroup",
            "AddMachineGroupInfo",
        ],
        "cleanup_default": options.cleanup,
    }


def run_alarm_e2e(
    client: Any,
    region: str,
    options: AlarmE2EOptions,
    *,
    robot_sender: RobotSender | None = None,
    env_getter: Callable[[str], str | None] = os.environ.get,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if not options.confirm_real_write:
        raise ConfirmationRequired("pass --confirm-real-write to create temporary CLS resources")

    run_id = options.run_id or _new_run_id()
    name = f"{options.name_prefix}-{run_id}"
    assertions: list[dict[str, Any]] = []
    findings: list[dict[str, str]] = []
    cleanup_results: list[dict[str, str]] = []
    resources: list[dict[str, str]] = []
    status: Literal["PASS", "PARTIAL", "FAIL"] = "FAIL"
    topic_id = ""
    logset_id = ""
    alarm_id = ""

    def record(resource_type: str, resource_id: str, resource_name: str) -> None:
        resources.append({"type": resource_type, "id": resource_id, "name": resource_name})

    try:
        logset = _invoke(client, "CreateLogset", {"LogsetName": name}, region, assertions)
        logset_id = _response_id(logset, "LogsetId")
        record("logset", logset_id, name)

        topic = _invoke(
            client,
            "CreateTopic",
            {"LogsetId": logset_id, "TopicName": name, "PartitionCount": 1},
            region,
            assertions,
        )
        topic_id = _response_id(topic, "TopicId")
        record("topic", topic_id, name)

        _invoke(client, "CreateIndex", _index_payload(topic_id), region, assertions)
        record("index", topic_id, name)

        _invoke(
            client,
            "UploadLog",
            {"TopicId": topic_id, "Logs": _synthetic_logs(run_id)},
            region,
            assertions,
            "upload_logs",
        )

        search = _poll(
            lambda: _invoke(
                client,
                "SearchLog",
                _search_payload(topic_id, run_id),
                region,
                assertions,
                "wait_searchable",
            ),
            lambda payload: bool(_query_logs(payload)),
            options.poll_seconds,
            options.poll_interval_seconds,
            sleep,
        )
        if search is None:
            findings.append({"phase": "wait_searchable", "message": "uploaded logs not searchable"})
        histogram = _invoke(
            client,
            "DescribeLogHistogram",
            _histogram_payload(topic_id, run_id),
            region,
            assertions,
        )
        if _total_count(histogram) <= 0:
            findings.append({"phase": "histogram", "message": "histogram returned zero logs"})

        policy = _policy_payload(
            name, logset_id, topic_id, run_id, options.notice_ids, options.advanced
        )
        policy_query = _invoke(
            client,
            "SearchLog",
            _policy_query_payload(topic_id, policy),
            region,
            assertions,
            "policy_test_query",
        )
        sample_context = _sample_context(policy, policy_query, region)

        created_notice_ids = _verify_templates_and_notifications(
            client,
            region,
            name,
            policy,
            sample_context,
            assertions,
            findings,
            resources,
            robot_sender,
            env_getter,
            options,
        )
        _verify_template_variants(policy, sample_context, assertions, findings)
        if not policy.get("AlarmNoticeIds"):
            alarm_notice_id = _create_alarm_notice(
                client,
                region,
                name,
                created_notice_ids,
                env_getter,
                assertions,
                resources,
                options.advanced,
            )
            policy["AlarmNoticeIds"] = [alarm_notice_id]

        alarm = _invoke(client, "CreateAlarm", policy, region, assertions)
        alarm_id = _response_id(alarm, "AlarmId")
        record("alarm", alarm_id, name)

        history = _poll(
            lambda: _invoke(
                client,
                "DescribeAlertRecordHistory",
                _history_payload(alarm_id, topic_id),
                region,
                assertions,
                "poll_alarm_history",
            ),
            lambda payload: bool(_response_list(payload, "Records")),
            options.poll_seconds,
            options.poll_interval_seconds,
            sleep,
        )
        execution_log = _invoke(
            client,
            "GetAlarmLog",
            _alarm_log_payload(alarm_id, topic_id),
            region,
            assertions,
            "collect_alarm_log",
        )
        history_triggered = history is not None and bool(_response_list(history, "Records"))
        execution_triggered = _execution_log_has_triggered_notification(execution_log)
        if not history_triggered and not execution_triggered:
            status = "PARTIAL"
            findings.append(
                {
                    "phase": "alarm_trigger",
                    "message": (
                        "alarm config accepted but CLS execution logs did not show "
                        "a matched trigger notification in poll window"
                    ),
                }
            )
        elif findings:
            status = "PARTIAL"
        else:
            status = "PASS"

        # Keep created notice IDs reachable for cleanup even if API returned duplicate IDs.
        _ = created_notice_ids
    except Exception as exc:  # noqa: BLE001 - E2E must report and cleanup all failures.
        findings.append({"phase": _phase_from_error(exc), "message": str(exc)})
        status = "FAIL"
    finally:
        if options.cleanup:
            cleanup_results.extend(_cleanup(client, region, resources))

    return {
        "run_id": run_id,
        "status": status,
        "region": region,
        "created_resources": resources,
        "assertions": assertions,
        "findings": findings,
        "cleanup": cleanup_results,
    }


def _verify_templates_and_notifications(
    client: Any,
    region: str,
    name: str,
    policy: dict[str, Any],
    sample_context: dict[str, Any],
    assertions: list[dict[str, Any]],
    findings: list[dict[str, str]],
    resources: list[dict[str, str]],
    robot_sender: RobotSender | None,
    env_getter: Callable[[str], str | None],
    options: AlarmE2EOptions,
) -> list[str]:
    created_notice_ids: list[str] = []
    for channel in ("webhook", "wecom", "feishu"):
        notice = generate_notice_template(
            scenario="http-5xx",
            channel=channel,
            fields=["request_uri", "status", "error_count"],
            name=f"{name}-{channel}",
            language="zh",
        )
        issues = validate_notice_template(notice, policy)
        assertions.append(
            {
                "phase": f"template_validate_{channel}",
                "passed": not issues,
                "issue_count": len(issues),
            }
        )
        if issues:
            findings.append(
                {
                    "phase": f"template_validate_{channel}",
                    "message": json.dumps(
                        [issue.to_dict() for issue in issues], ensure_ascii=False
                    ),
                }
            )
        rendered = render_notice_template(notice, sample_context)
        unrendered = "{{" in json.dumps(rendered, ensure_ascii=False)
        assertions.append({"phase": f"template_render_{channel}", "passed": not unrendered})
        if unrendered:
            findings.append(
                {
                    "phase": f"template_render_{channel}",
                    "message": "unrendered template marker found",
                }
            )

        response = _invoke(client, "CreateNoticeContent", notice, region, assertions)
        notice_id = _response_id(response, "NoticeContentId")
        created_notice_ids.append(notice_id)
        resources.append({"type": "notice_content", "id": notice_id, "name": notice["Name"]})

        if channel == "wecom" and options.send_wecom:
            _send_robot_if_configured(
                rendered,
                "wecom",
                "CLS_ALARM_TEST_WEBHOOK_URL",
                robot_sender,
                env_getter,
                options.robot_timeout,
                assertions,
            )
        if channel == "feishu" and options.send_feishu:
            _send_robot_if_configured(
                rendered,
                "feishu",
                "CLS_ALARM_TEST_FEISHU_WEBHOOK_URL",
                robot_sender,
                env_getter,
                options.robot_timeout,
                assertions,
            )
    return created_notice_ids


def _create_alarm_notice(
    client: Any,
    region: str,
    name: str,
    notice_content_ids: list[str],
    env_getter: Callable[[str], str | None],
    assertions: list[dict[str, Any]],
    resources: list[dict[str, str]],
    advanced: bool = False,
) -> str:
    callbacks: list[dict[str, Any]] = []
    wecom_url = env_getter("CLS_ALARM_TEST_WEBHOOK_URL")
    feishu_url = env_getter("CLS_ALARM_TEST_FEISHU_WEBHOOK_URL")
    if wecom_url:
        web_callback_id = _create_web_callback(
            client,
            region,
            f"{name}-wecom-integration",
            "WeCom",
            wecom_url,
            assertions,
            resources,
        )
        callbacks.append(
            {
                "CallbackType": "WeCom",
                "Url": "",
                "WebCallbackId": web_callback_id,
                "NoticeContentId": notice_content_ids[1],
            }
        )
    if feishu_url:
        web_callback_id = _create_web_callback(
            client,
            region,
            f"{name}-feishu-integration",
            "Lark",
            feishu_url,
            assertions,
            resources,
        )
        callbacks.append(
            {
                "CallbackType": "Lark",
                "Url": "",
                "WebCallbackId": web_callback_id,
                "NoticeContentId": notice_content_ids[2],
            }
        )
    if not callbacks:
        callbacks.append(
            {"CallbackType": "Http", "Url": "", "NoticeContentId": notice_content_ids[0]}
        )
    notice_name = f"{name}-notice-group"
    if advanced:
        payload = {
            "Name": notice_name,
            "Type": "",
            "NoticeReceivers": [],
            "WebCallbacks": [],
            "NoticeRules": [
                {
                    "Rule": _advanced_notice_rule(),
                    "WebCallbacks": callbacks,
                    "Escalate": False,
                }
            ],
            "AlarmShieldStatus": 2,
            "CallbackPrioritize": False,
        }
    else:
        payload = {
            "Name": notice_name,
            "Type": "All",
            "WebCallbacks": callbacks,
            "AlarmShieldStatus": 1,
        }
    response = _invoke(client, "CreateAlarmNotice", payload, region, assertions)
    alarm_notice_id = _response_id(response, "AlarmNoticeId")
    resources.append({"type": "alarm_notice", "id": alarm_notice_id, "name": notice_name})
    return alarm_notice_id


def _advanced_notice_rule() -> str:
    return json.dumps(
        {
            "Value": "AND",
            "Type": "Operation",
            "Children": [
                {
                    "Type": "Condition",
                    "Value": "NotifyType",
                    "Children": [
                        {"Value": "In", "Type": "Compare"},
                        {"Value": "[1,2]", "Type": "Value"},
                    ],
                }
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _create_web_callback(
    client: Any,
    region: str,
    name: str,
    callback_type: str,
    webhook: str,
    assertions: list[dict[str, Any]],
    resources: list[dict[str, str]],
) -> str:
    official_type = normalize_callback_type(callback_type)
    payload = {"Name": name, "Type": official_type, "Webhook": webhook}
    response = _invoke(client, "CreateWebCallback", payload, region, assertions)
    web_callback_id = _response_id(response, "WebCallbackId")
    resources.append({"type": "web_callback", "id": web_callback_id, "name": name})
    return web_callback_id


def _verify_template_variants(
    policy: dict[str, Any],
    sample_context: dict[str, Any],
    assertions: list[dict[str, Any]],
    findings: list[dict[str, str]],
) -> None:
    positive_cases = {
        "trigger_result_fields": (
            "{{range .TriggerResult[0]}}"
            "{{.request_uri}} {{.status}} {{.error_count}}"
            "{{end}}"
        ),
        "query_log_content": "{{toPrettyJson .QueryLog[0][0].content}}",
        "trigger_params": '{{range (splitList ";" .TriggerParams)}}{{.}} {{end}}',
    }
    for name, content in positive_cases.items():
        payload = _variant_payload(content)
        issues = validate_notice_template(payload, policy)
        rendered = render_notice_template(payload, sample_context)
        passed = not issues and "{{" not in json.dumps(rendered, ensure_ascii=False)
        phase = f"template_variant_{name}"
        assertions.append({"phase": phase, "passed": passed, "issue_count": len(issues)})
        if not passed:
            findings.append({"phase": phase, "message": json.dumps(rendered, ensure_ascii=False)})

    negative_cases = {
        "unknown_variable_negative": ("{{.AlarmName}}", "unknown_variable"),
        "missing_alias_negative": ("{{.TriggerResult[0][0].not_selected}}", "missing_query_alias"),
        "channel_escape_negative": ("告警：{{.Alarm}}", "channel_escape_missing"),
    }
    for name, (content, expected_code) in negative_cases.items():
        payload = _variant_payload(content, channel_type="Lark")
        issues = validate_notice_template(payload, policy)
        passed = any(issue.code == expected_code for issue in issues)
        assertions.append(
            {
                "phase": f"template_variant_{name}",
                "passed": passed,
                "expected_issue": expected_code,
            }
        )
        if not passed:
            findings.append(
                {
                    "phase": f"template_variant_{name}",
                    "message": "expected validation issue missing",
                }
            )


def _variant_payload(content: str, channel_type: str = "Email") -> dict[str, Any]:
    return {
        "Name": "variant",
        "Type": 0,
        "NoticeContents": [
            {
                "Type": channel_type,
                "TriggerContent": {"Title": "{{.Alarm}}", "Content": content, "Headers": []},
                "RecoveryContent": {"Title": "恢复", "Content": "恢复", "Headers": []},
            }
        ],
    }


def _send_robot_if_configured(
    rendered: dict[str, Any],
    robot: str,
    env_name: str,
    robot_sender: RobotSender | None,
    env_getter: Callable[[str], str | None],
    timeout: int,
    assertions: list[dict[str, Any]],
) -> None:
    if not env_getter(env_name):
        assertions.append({"phase": f"robot_send_{robot}", "passed": True, "skipped": True})
        return
    if robot_sender is None:
        assertions.append({"phase": f"robot_send_{robot}", "passed": False, "skipped": True})
        return
    response = robot_sender(rendered, robot, env_name, timeout)
    passed = response.get("errcode") == 0 or response.get("code") == 0
    assertions.append(
        {"phase": f"robot_send_{robot}", "passed": passed, "response": _redact(response)}
    )


def _cleanup(client: Any, region: str, resources: list[dict[str, str]]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for resource in reversed(resources):
        resource_type = resource["type"]
        resource_id = resource["id"]
        try:
            if resource_type == "alarm":
                client.invoke("DeleteAlarm", {"AlarmId": resource_id}, region)
            elif resource_type == "alarm_notice":
                client.invoke("DeleteAlarmNotice", {"AlarmNoticeId": resource_id}, region)
            elif resource_type == "web_callback":
                client.invoke("DeleteWebCallback", {"WebCallbackId": resource_id}, region)
            elif resource_type == "notice_content":
                client.invoke("DeleteNoticeContent", {"NoticeContentId": resource_id}, region)
            elif resource_type == "index":
                client.invoke("DeleteIndex", {"TopicId": resource_id}, region)
            elif resource_type == "topic":
                client.invoke("DeleteTopic", {"TopicId": resource_id}, region)
            elif resource_type == "logset":
                client.invoke("DeleteLogset", {"LogsetId": resource_id}, region)
            else:
                continue
        except Exception as exc:  # noqa: BLE001 - cleanup should keep best-effort results.
            results.append(
                {
                    "type": resource_type,
                    "id": resource_id,
                    "status": "failed",
                    "error": str(exc),
                }
            )
        else:
            results.append({"type": resource_type, "id": resource_id, "status": "deleted"})
    return results


def _invoke(
    client: Any,
    action: str,
    payload: dict[str, Any],
    region: str,
    assertions: list[dict[str, Any]],
    phase: str | None = None,
) -> dict[str, Any]:
    response = client.invoke(action, payload, region)
    assertions.append(
        {
            "phase": phase or action,
            "action": action,
            "passed": True,
            "request_id": response.get("Response", {}).get("RequestId"),
        }
    )
    return cast(dict[str, Any], response)


def _poll(
    call: Callable[[], dict[str, Any]],
    ready: Callable[[dict[str, Any]], bool],
    poll_seconds: int,
    poll_interval_seconds: int,
    sleep: Callable[[float], None],
) -> dict[str, Any] | None:
    deadline = time.time() + max(0, poll_seconds)
    while True:
        result = call()
        if ready(result):
            return result
        if time.time() >= deadline:
            return None
        sleep(max(0, poll_interval_seconds))


def _new_run_id() -> str:
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}"


def _index_payload(topic_id: str) -> dict[str, Any]:
    tokenizer = "@&()='\",;:<>[]{}/ \n\t\r"
    fields = [
        ("e2e_id", "text"),
        ("request_uri", "text"),
        ("status", "long"),
        ("latency_ms", "long"),
        ("service", "text"),
        ("env", "text"),
        ("message", "text"),
    ]
    return {
        "TopicId": topic_id,
        "Rule": {
            "FullText": {"CaseSensitive": False, "Tokenizer": tokenizer},
            "KeyValue": {
                "CaseSensitive": False,
                "KeyValues": [
                    {
                        "Key": key,
                        "Value": {"Type": value_type, "Tokenizer": tokenizer, "SqlFlag": True},
                    }
                    for key, value_type in fields
                ],
            },
        },
    }


def _synthetic_logs(run_id: str) -> list[dict[str, Any]]:
    now_ms = int(time.time() * 1000)
    rows = [
        ("/api/order", 500, 231, "order failed"),
        ("/api/order", 502, 245, "upstream failed"),
        ("/api/pay", 503, 301, "payment unavailable"),
        ("/api/health", 200, 12, "ok"),
    ]
    return [
        {
            "time": now_ms + index,
            "e2e_id": run_id,
            "request_uri": uri,
            "status": status,
            "latency_ms": latency,
            "service": "cls-cli-e2e",
            "env": "e2e",
            "message": message,
        }
        for index, (uri, status, latency, message) in enumerate(rows)
    ]


def _search_payload(topic_id: str, run_id: str) -> dict[str, Any]:
    return {
        "TopicId": topic_id,
        "QueryString": f'e2e_id:"{run_id}"',
        "From": int(time.time() * 1000) - 10 * 60 * 1000,
        "To": int(time.time() * 1000) + 60 * 1000,
        "Limit": 20,
    }


def _histogram_payload(topic_id: str, run_id: str) -> dict[str, Any]:
    return {
        "TopicId": topic_id,
        "Query": f'e2e_id:"{run_id}"',
        "From": int(time.time() * 1000) - 10 * 60 * 1000,
        "To": int(time.time() * 1000) + 60 * 1000,
    }


def _policy_payload(
    name: str,
    logset_id: str,
    topic_id: str,
    run_id: str,
    notice_ids: list[str] | None,
    advanced: bool = False,
) -> dict[str, Any]:
    payload = scaffold_alarm_policy(
        scenario="http-5xx",
        name=name,
        logset_id=logset_id,
        topic_id=topic_id,
        threshold=0,
        window_minutes=1,
        fields=["request_uri", "status"],
        notice_ids=notice_ids,
    )
    target = payload["AlarmTargets"][0]
    target["Query"] = (
        f'e2e_id:"{run_id}" AND status:>=500 | select count(*) as error_count, '
        "request_uri, status group by request_uri,status order by error_count desc limit 10"
    )
    target["StartTimeOffset"] = -10
    target["EndTimeOffset"] = 0
    payload["MonitorTime"] = {"Type": "Period", "Time": 1}
    payload["Condition"] = "$1.error_count > 0"
    if advanced:
        condition = str(payload.pop("Condition"))
        alarm_level = int(payload.pop("AlarmLevel", 0))
        payload["MultiConditions"] = [{"Condition": condition, "AlarmLevel": alarm_level}]
        payload["GroupTriggerStatus"] = True
        payload["GroupTriggerCondition"] = ["request_uri", "status"]
        payload["MessageTemplate"] = "{{.Label}}"
        payload["CallBack"] = {"Headers": [], "Body": ""}
    return payload


def _policy_query_payload(topic_id: str, policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "TopicId": topic_id,
        "QueryString": policy["AlarmTargets"][0]["Query"],
        "From": int(time.time() * 1000) - 10 * 60 * 1000,
        "To": int(time.time() * 1000) + 60 * 1000,
        "Limit": 100,
    }


def _history_payload(alarm_id: str, topic_id: str) -> dict[str, Any]:
    return {
        "From": int(time.time() * 1000) - 10 * 60 * 1000,
        "To": int(time.time() * 1000) + 60 * 1000,
        "Offset": 0,
        "Limit": 20,
        "Filters": [
            {"Key": "alertId", "Values": [alarm_id]},
            {"Key": "topicId", "Values": [topic_id]},
        ],
    }


def _alarm_log_payload(alarm_id: str, topic_id: str) -> dict[str, Any]:
    return {
        "From": int(time.time() * 1000) - 10 * 60 * 1000,
        "To": int(time.time() * 1000) + 60 * 1000,
        "Query": f'alert_id:"{alarm_id}" AND monitored_object:"{topic_id}"',
        "Limit": 20,
        "UseNewAnalysis": True,
    }


def _sample_context(
    policy: dict[str, Any], response: dict[str, Any], region: str
) -> dict[str, Any]:
    records = _analysis_records(response)
    now_text = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    alarm_name = str(policy["Name"])
    return {
        "Alarm": alarm_name,
        "AlarmID": "alarm-created-by-cls-e2e",
        "UIN": "1000000000",
        "Nickname": "cls-cli-e2e",
        "Region": region,
        "Topic": alarm_name,
        "Logset": alarm_name,
        "Level_zh": "警告",
        "Condition": _policy_condition_text(policy),
        "StartTime": now_text,
        "NotifyTime": now_text,
        "ConsecutiveAlertNums": 1,
        "NotifyType": 1,
        "TriggerParams": "$1.error_count=3;$1.request_uri=/api/order",
        "TriggerResult": [records],
        "QueryResult": [records],
        "QueryLog": [_query_logs(response)],
        "AnalysisResultFormat_zh": "error_count=3 request_uri=/api/order",
        "DetailUrl": "https://cloud.tencent.com/cls/e2e-detail",
        "QueryUrl": "https://cloud.tencent.com/cls/e2e-query",
        "CanSilent": False,
    }


def _policy_condition_text(policy: dict[str, Any]) -> str:
    condition = policy.get("Condition")
    if isinstance(condition, str):
        return condition
    multi_conditions = policy.get("MultiConditions")
    if isinstance(multi_conditions, list) and multi_conditions:
        first = multi_conditions[0]
        if isinstance(first, dict) and isinstance(first.get("Condition"), str):
            return str(first["Condition"])
    return ""


def _analysis_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = payload.get("Response", {}).get("AnalysisRecords") or []
    parsed = [_parse_json_object(item) for item in records if isinstance(item, str | dict)]
    return parsed or [{"error_count": 0, "request_uri": "", "status": ""}]


def _query_logs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _response_list(payload, "Results"):
        if isinstance(item, dict):
            rows.append(_parse_json_object(item.get("LogJson")))
    return rows


def _execution_log_has_triggered_notification(payload: dict[str, Any]) -> bool:
    for item in _response_list(payload, "Results"):
        if not isinstance(item, dict):
            continue
        log = _parse_json_object(item.get("LogJson"))
        reach_trigger = str(log.get("reach_trigger", "")).lower() == "true"
        condition = str(log.get("condition_evaluate_result", "")).lower()
        notification = str(log.get("notification_send_result", "")).lower()
        status = str(log.get("status", "")).lower()
        if status in {"queryresultunmatch", "triggerfailed"}:
            continue
        if notification in {"notsend", "sendfailed", "failed", "fail"}:
            continue
        if reach_trigger or condition in {"matched", "conditionmatched", "success"}:
            return True
    return False


def _parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return {"raw": value}
        return loaded if isinstance(loaded, dict) else {"value": loaded}
    return {}


def _response_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get("Response", {}).get(key)
    return value if isinstance(value, list) else []


def _response_id(payload: dict[str, Any], key: str) -> str:
    value = payload.get("Response", {}).get(key)
    if not value:
        raise RuntimeError(f"missing response id: {key}")
    return str(value)


def _total_count(payload: dict[str, Any]) -> int:
    value = payload.get("Response", {}).get("TotalCount")
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _phase_from_error(exc: Exception) -> str:
    text = str(exc)
    if "UploadLog" in text or "upload" in text.lower():
        return "upload_logs"
    return "e2e"


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "<redacted>" if _sensitive_key(key) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        wecom_url = os.environ.get("CLS_ALARM_TEST_WEBHOOK_URL", "\0")
        feishu_url = os.environ.get("CLS_ALARM_TEST_FEISHU_WEBHOOK_URL", "\0")
        return value.replace(wecom_url, "<redacted>").replace(feishu_url, "<redacted>")
    return value


def _sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("_", "")
    return any(token in normalized for token in ("secret", "token", "authorization", "signature"))
