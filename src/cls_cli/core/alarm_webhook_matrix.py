from __future__ import annotations

import os
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from cls_cli.core.alarm_e2e import (
    _cleanup,
    _parse_json_object,
    _poll,
    _response_id,
    _response_list,
)
from cls_cli.core.alarm_webhook_receiver import (
    WebhookCaptureServer,
    validate_received_payload,  # noqa: F401 - backward-compatible public import.
)
from cls_cli.core.alarm_webhook_receiver import (
    has_received_scenario as _has_received_scenario,
)
from cls_cli.core.alarm_webhook_receiver import (
    load_external_receiver_records as _load_external_receiver_records,
)
from cls_cli.core.alarm_webhook_receiver import (
    read_received_records as _read_received_records,
)
from cls_cli.core.alarm_webhook_report import (
    finalize_webhook_matrix_result as _finalize_result,
)
from cls_cli.core.alarm_webhook_scenarios import (
    WebhookFunctionScenario,
    default_webhook_function_scenarios,
)
from cls_cli.core.alarm_webhook_scenarios import (
    instantiate_webhook_function_scenarios as _instantiate_scenarios,
)
from cls_cli.core.alarm_webhook_scenarios import (
    recovery_body as _recovery_body,
)
from cls_cli.core.alarm_webhook_scenarios import (
    select_webhook_function_scenarios as _select_scenarios,
)
from cls_cli.core.errors import ConfirmationRequired

WEBHOOK_MATRIX_ALLOWED_ACTIONS = [
    "CreateLogset",
    "CreateTopic",
    "CreateIndex",
    "UploadLog",
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


@dataclass(frozen=True)
class WebhookMatrixOptions:
    confirm_real_write: bool = False
    region: str = "ap-shanghai"
    run_id: str | None = None
    name_prefix: str = "cls-cli-webhook-fn"
    receiver_host: str = "127.0.0.1"
    receiver_port: int = 8765
    public_webhook_url: str | None = None
    poll_seconds: int = 600
    poll_interval_seconds: int = 30
    cleanup: bool = True
    output_dir: Path = Path(".tmp/alarm-webhook-matrix")
    start_receiver: bool = True
    external_receiver: bool = False
    external_receiver_result_url: str | None = None
    case_ids: list[str] | None = None


def plan_webhook_function_matrix(options: WebhookMatrixOptions) -> dict[str, Any]:
    run_id = options.run_id or _new_run_id()
    scenarios = _select_scenarios(options.case_ids)
    return {
        "dry_run": True,
        "region": options.region,
        "run_id": run_id,
        "scope": "webhook-only alarm variable function matrix",
        "planned_actions": WEBHOOK_MATRIX_ALLOWED_ACTIONS,
        "excluded_actions": [
            "CreateMachineGroup",
            "CreateConfig",
            "ApplyConfigToMachineGroup",
            "AddMachineGroupInfo",
        ],
        "scenario_count": len(scenarios),
        "scenario_ids": [scenario.id for scenario in scenarios],
        "covered_functions": sorted(
            {fn for scenario in scenarios for fn in scenario.expected_functions}
        ),
        "receiver": {
            "host": options.receiver_host,
            "port": options.receiver_port,
            "start_receiver": options.start_receiver,
            "external_receiver": options.external_receiver,
        },
        "public_webhook_url": "<configured>" if options.public_webhook_url else "<required>",
        "external_receiver_result_url": (
            "<configured>" if options.external_receiver_result_url else None
        ),
        "output_dir": str(options.output_dir / run_id),
        "cleanup_default": options.cleanup,
    }


def run_webhook_function_matrix(
    client: Any,
    options: WebhookMatrixOptions,
    *,
    tunnel_detector: Callable[[str, int], str | None] | None = None,
    external_receiver_loader: Callable[[str, str], list[dict[str, Any]]] | None = None,
    env_getter: Callable[[str], str | None] = os.environ.get,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if not options.confirm_real_write:
        raise ConfirmationRequired("pass --confirm-real-write to create temporary CLS resources")

    run_id = options.run_id or _new_run_id()
    run_dir = options.output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    received_file = run_dir / "received.jsonl"
    resources: list[dict[str, str]] = []
    assertions: list[dict[str, Any]] = []
    findings: list[dict[str, str]] = []
    cleanup_results: list[dict[str, str]] = []
    scenario_results: list[dict[str, Any]] = []
    status: Literal["PASS", "PARTIAL", "FAIL"] = "FAIL"
    scenarios = _instantiate_scenarios(_select_scenarios(options.case_ids), run_id)
    scenario_ids = {scenario.id for scenario in scenarios}
    load_external_records = external_receiver_loader or _load_external_receiver_records

    receiver: WebhookCaptureServer | None = None
    try:
        if options.start_receiver and not options.external_receiver:
            receiver = WebhookCaptureServer(
                options.receiver_host,
                options.receiver_port,
                received_file,
                expected_run_id=run_id,
                scenario_ids=scenario_ids,
            )
            receiver.__enter__()

        public_url = _resolve_public_webhook_url(
            options,
            receiver,
            tunnel_detector or _detect_public_tunnel,
            env_getter,
        )
        if not public_url:
            findings.append(
                {
                    "phase": "public_webhook_url",
                    "message": (
                        "CLS cannot call a localhost webhook. Set --public-webhook-url or "
                        "CLS_ALARM_PUBLIC_WEBHOOK_URL to a publicly reachable tunnel URL."
                    ),
                }
            )
            return _finalize_result(
                run_id,
                options.region,
                "FAIL",
                resources,
                assertions,
                findings,
                cleanup_results,
                scenario_results,
                received_file,
                run_dir,
            )

        name = f"{options.name_prefix}-{run_id}"
        logset = _invoke(client, "CreateLogset", {"LogsetName": name}, options.region, assertions)
        logset_id = _response_id(logset, "LogsetId")
        _record(resources, "logset", logset_id, name)

        topic = _invoke(
            client,
            "CreateTopic",
            {"LogsetId": logset_id, "TopicName": name, "PartitionCount": 1},
            options.region,
            assertions,
        )
        topic_id = _response_id(topic, "TopicId")
        _record(resources, "topic", topic_id, name)

        _invoke(client, "CreateIndex", _index_payload(topic_id), options.region, assertions)
        _record(resources, "index", topic_id, name)

        _invoke(
            client,
            "UploadLog",
            {"TopicId": topic_id, "Logs": _synthetic_logs(run_id)},
            options.region,
            assertions,
            "upload_logs",
        )

        searchable = _poll(
            lambda: _invoke(
                client,
                "SearchLog",
                _search_payload(topic_id, run_id),
                options.region,
                assertions,
                "wait_searchable",
            ),
            lambda payload: bool(_query_logs(payload)),
            options.poll_seconds,
            options.poll_interval_seconds,
            sleep,
        )
        if searchable is None:
            findings.append({"phase": "wait_searchable", "message": "uploaded logs not searchable"})

        for scenario in scenarios:
            policy = _policy_payload(name, logset_id, topic_id, scenario)
            def poll_policy_query(
                current_policy: dict[str, Any] = policy,
                current_scenario_id: str = scenario.id,
            ) -> dict[str, Any]:
                return _invoke(
                    client,
                    "SearchLog",
                    _policy_query_payload(topic_id, current_policy),
                    options.region,
                    assertions,
                    f"policy_test_query_{current_scenario_id}",
                )

            query_response = _poll(
                poll_policy_query,
                lambda payload: bool(_analysis_records(payload)),
                options.poll_seconds,
                options.poll_interval_seconds,
                sleep,
            )
            analysis_records = _analysis_records(query_response or {})
            scenario_result: dict[str, Any] = {
                "id": scenario.id,
                "title": scenario.title,
                "expected_functions": scenario.expected_functions,
                "query_matched": bool(analysis_records),
                "webhook_received": False,
                "send_success": False,
            }
            scenario_results.append(scenario_result)
            if not analysis_records:
                findings.append(
                    {
                        "phase": "policy_test_query",
                        "message": f"{scenario.id} query returned no data",
                    }
                )
                continue

            notice = _notice_content_payload(f"{name}-{scenario.id}-content", scenario)
            notice_response = _invoke(
                client, "CreateNoticeContent", notice, options.region, assertions
            )
            notice_content_id = _response_id(notice_response, "NoticeContentId")
            _record(resources, "notice_content", notice_content_id, notice["Name"])

            callback_response = _invoke(
                client,
                "CreateWebCallback",
                {
                    "Name": f"{name}-{scenario.id}-http",
                    "Type": "Http",
                    "Webhook": public_url,
                    "Method": "POST",
                },
                options.region,
                assertions,
            )
            web_callback_id = _response_id(callback_response, "WebCallbackId")
            _record(resources, "web_callback", web_callback_id, f"{name}-{scenario.id}-http")

            notice_group = _invoke(
                client,
                "CreateAlarmNotice",
                _alarm_notice_payload(
                    f"{name}-{scenario.id}-notice", web_callback_id, notice_content_id
                ),
                options.region,
                assertions,
            )
            alarm_notice_id = _response_id(notice_group, "AlarmNoticeId")
            _record(resources, "alarm_notice", alarm_notice_id, f"{name}-{scenario.id}-notice")
            policy["AlarmNoticeIds"] = [alarm_notice_id]

            alarm_response = _invoke(client, "CreateAlarm", policy, options.region, assertions)
            alarm_id = _response_id(alarm_response, "AlarmId")
            _record(resources, "alarm", alarm_id, f"{name}-{scenario.id}")
            scenario_result["alarm_id"] = alarm_id

            scenario_id = scenario.id

            def poll_execution_log(
                current_alarm_id: str = alarm_id,
                current_scenario_id: str = scenario_id,
            ) -> dict[str, Any]:
                return _invoke(
                    client,
                    "GetAlarmLog",
                    _alarm_log_payload(current_alarm_id, topic_id),
                    options.region,
                    assertions,
                    f"collect_alarm_log_{current_scenario_id}",
                )

            execution_log = _poll(
                poll_execution_log,
                _execution_log_has_send_success,
                options.poll_seconds,
                options.poll_interval_seconds,
                sleep,
            ) or {}
            send_success = _execution_log_has_send_success(execution_log)
            scenario_result["history_records"] = send_success
            scenario_result["send_success"] = send_success
            if not send_success:
                findings.append(
                    {
                        "phase": "alarm_send",
                        "message": (
                            f"{scenario.id} did not show "
                            "notification_send_result=SendSuccess"
                        ),
                    }
                )

            if options.external_receiver:
                scenario_result["external_receiver"] = True
                if options.external_receiver_result_url:
                    scenario_result["external_receiver_result_url"] = "<configured>"
                    external_error = ""

                    def read_external_received() -> dict[str, Any]:
                        nonlocal external_error
                        try:
                            return {
                                "records": load_external_records(
                                    options.external_receiver_result_url or "", run_id
                                )
                            }
                        except Exception as exc:  # noqa: BLE001 - optional test receiver may be down.
                            external_error = _redact_error(str(exc))
                            return {"records": []}

                    def external_received_ready(
                        payload: dict[str, Any], current_scenario_id: str = scenario.id
                    ) -> bool:
                        return _has_received_scenario(
                            cast(list[dict[str, Any]], payload["records"]),
                            run_id,
                            current_scenario_id,
                        )

                    external_received = _poll(
                        read_external_received,
                        external_received_ready,
                        options.poll_seconds,
                        options.poll_interval_seconds,
                        sleep,
                    )
                    external_records = (
                        cast(list[dict[str, Any]], external_received["records"])
                        if external_received is not None
                        else []
                    )
                    webhook_received = _has_received_scenario(
                        external_records, run_id, scenario.id
                    )
                    scenario_result["webhook_received"] = webhook_received
                    if not webhook_received:
                        message = f"{scenario.id} external webhook record not found"
                        if external_error:
                            message = f"{message}: {external_error}"
                        findings.append({"phase": "external_webhook_receive", "message": message})
                else:
                    scenario_result["webhook_received"] = send_success
            else:
                def read_received() -> dict[str, Any]:
                    return {"records": _read_received_records(received_file)}

                def received_ready(
                    payload: dict[str, Any], current_scenario_id: str = scenario.id
                ) -> bool:
                    return _has_received_scenario(
                        cast(list[dict[str, Any]], payload["records"]),
                        run_id,
                        current_scenario_id,
                    )

                received = _poll(
                    read_received,
                    received_ready,
                    options.poll_seconds,
                    options.poll_interval_seconds,
                    sleep,
                )
                scenario_records = (
                    cast(list[dict[str, Any]], received["records"])
                    if received is not None
                    else _read_received_records(received_file)
                )
                webhook_received = _has_received_scenario(scenario_records, run_id, scenario.id)
                scenario_result["webhook_received"] = webhook_received
                if not webhook_received:
                    findings.append(
                        {
                            "phase": "webhook_receive",
                            "message": f"{scenario.id} webhook not received",
                        }
                    )

        if all(
            item.get("query_matched") and item.get("send_success") and item.get("webhook_received")
            for item in scenario_results
        ) and not findings:
            status = "PASS"
        elif scenario_results:
            status = "PARTIAL"
        else:
            status = "FAIL"
    except Exception as exc:  # noqa: BLE001 - real E2E must report and cleanup failures.
        findings.append({"phase": "webhook_matrix", "message": str(exc)})
        status = "FAIL"
    finally:
        if options.cleanup and resources:
            cleanup_results.extend(_cleanup(client, options.region, resources))
        if receiver is not None:
            receiver.__exit__(None, None, None)

    return _finalize_result(
        run_id,
        options.region,
        status,
        resources,
        assertions,
        findings,
        cleanup_results,
        scenario_results,
        received_file,
        run_dir,
    )


def _resolve_public_webhook_url(
    options: WebhookMatrixOptions,
    receiver: WebhookCaptureServer | None,
    tunnel_detector: Callable[[str, int], str | None],
    env_getter: Callable[[str], str | None],
) -> str | None:
    configured = options.public_webhook_url or env_getter("CLS_ALARM_PUBLIC_WEBHOOK_URL")
    if configured:
        return configured
    if receiver is None:
        return None
    port = int(receiver.local_url.rsplit(":", 1)[1].split("/", 1)[0])
    return tunnel_detector(options.receiver_host, port)


def _detect_public_tunnel(_host: str, _port: int) -> str | None:
    return None


def _notice_content_payload(
    name: str, scenario: WebhookFunctionScenario
) -> dict[str, Any]:
    return {
        "Name": name,
        "Type": 0,
        "NoticeContents": [
            {
                "Type": "Http",
                "TriggerContent": {
                    "Title": "{{escape .Alarm}}",
                    "Content": scenario.template_body,
                    "Headers": ["Content-Type:application/json"],
                },
                "RecoveryContent": {
                    "Title": "{{escape .Alarm}} recovered",
                    "Content": _recovery_body(scenario.id).replace(
                        "__RUN_ID__", scenario.expected_json_paths["run_id"]
                    ),
                    "Headers": ["Content-Type:application/json"],
                },
            }
        ],
    }


def _policy_payload(
    name: str, logset_id: str, topic_id: str, scenario: WebhookFunctionScenario
) -> dict[str, Any]:
    return {
        "Name": f"{name}-{scenario.id}",
        "AlarmTargets": [
            {
                "LogsetId": logset_id,
                "TopicId": topic_id,
                "Query": scenario.query,
                "Number": 1,
                "StartTimeOffset": -10,
                "EndTimeOffset": 0,
                "SyntaxRule": 1,
            }
        ],
        "MonitorTime": {"Type": "Period", "Time": 1},
        "TriggerCount": 1,
        "AlarmPeriod": 15,
        "Condition": scenario.condition,
        "AlarmLevel": 0,
        "Status": True,
        "MonitorObjectType": 0,
    }


def _alarm_notice_payload(
    name: str, web_callback_id: str, notice_content_id: str
) -> dict[str, Any]:
    return {
        "Name": name,
        "Type": "All",
        "WebCallbacks": [
            {
                "CallbackType": "Http",
                "Url": "",
                "WebCallbackId": web_callback_id,
                "NoticeContentId": notice_content_id,
                "Method": "POST",
            }
        ],
        "AlarmShieldStatus": 1,
    }


def _index_payload(topic_id: str) -> dict[str, Any]:
    tokenizer = "@&()='\",;:<>[]{}/ \n\t\r"
    fields = [
        ("matrix_run_id", "text"),
        ("scenario_id", "text"),
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
    rows: list[tuple[str, str, int, int, str, str]] = []
    for case_index, scenario in enumerate(default_webhook_function_scenarios(), start=1):
        rows.extend(
            [
                (
                    scenario.id,
                    f"/api/case/{case_index}/order",
                    500,
                    400 + case_index,
                    f"svc-{case_index}",
                    f"case {case_index} failed id={1000 + case_index}",
                ),
                (
                    scenario.id,
                    f"/api/case/{case_index}/order",
                    502,
                    120 + case_index,
                    f"svc-{case_index}",
                    f"case {case_index} upstream id={2000 + case_index}",
                ),
                (
                    scenario.id,
                    f"/api/case/{case_index}/health",
                    200,
                    40 + case_index,
                    f"svc-{case_index}",
                    f"case {case_index} ok id={3000 + case_index}",
                ),
            ]
        )
    return [
        {
            "time": now_ms + index,
            "matrix_run_id": run_id,
            "scenario_id": scenario_id,
            "request_uri": uri,
            "status": status,
            "latency_ms": latency,
            "service": service,
            "env": "webhook-matrix",
            "message": message,
            "field-with-dash": "dash-value",
            "field space": "space-value",
            "$special": "dollar-value",
        }
        for index, (scenario_id, uri, status, latency, service, message) in enumerate(rows)
    ]


def _search_payload(topic_id: str, run_id: str) -> dict[str, Any]:
    return {
        "TopicId": topic_id,
        "QueryString": f'matrix_run_id:"{run_id}"',
        "From": int(time.time() * 1000) - 10 * 60 * 1000,
        "To": int(time.time() * 1000) + 60 * 1000,
        "Limit": 20,
    }


def _policy_query_payload(topic_id: str, policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "TopicId": topic_id,
        "QueryString": policy["AlarmTargets"][0]["Query"],
        "From": int(time.time() * 1000) - 10 * 60 * 1000,
        "To": int(time.time() * 1000) + 60 * 1000,
        "Limit": 100,
        "UseNewAnalysis": True,
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


def _invoke(
    client: Any,
    action: str,
    payload: dict[str, Any],
    region: str,
    assertions: list[dict[str, Any]],
    phase: str | None = None,
) -> dict[str, Any]:
    attempts = 3
    for attempt in range(1, attempts + 1):
        try:
            response = client.invoke(action, payload, region)
        except Exception as exc:  # noqa: BLE001 - classify SDK/network errors by payload text.
            if attempt >= attempts or not _retryable_api_exception(exc):
                raise
            assertions.append(
                {
                    "phase": phase or action,
                    "action": action,
                    "passed": False,
                    "retry": attempt,
                    "error": _redact_error(str(exc)),
                }
            )
            time.sleep(min(10, 2 * attempt))
            continue
        assertions.append(
            {
                "phase": phase or action,
                "action": action,
                "passed": True,
                "request_id": response.get("Response", {}).get("RequestId"),
            }
        )
        return cast(dict[str, Any], response)
    raise RuntimeError(f"{action} failed after retry")


def _retryable_api_exception(exc: Exception) -> bool:
    text = str(exc)
    return any(
        token in text
        for token in (
            "ClientNetworkError",
            "LogRequestError",
            "UNEXPECTED_EOF_WHILE_READING",
            "RequestLimitExceeded",
            "InternalError",
            "HTTPConnectionPool",
            "HTTPSConnectionPool",
        )
    )


def _redact_error(text: str) -> str:
    return text.replace(os.environ.get("CLS_SECRET_ID", "\0"), "<redacted>").replace(
        os.environ.get("CLS_SECRET_KEY", "\0"), "<redacted>"
    )


def _analysis_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = payload.get("Response", {}).get("AnalysisRecords") or []
    return [_parse_json_object(item) for item in records if isinstance(item, str | dict)]


def _query_logs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _response_list(payload, "Results"):
        if isinstance(item, dict):
            rows.append(_parse_json_object(item.get("LogJson")))
    return rows


def _execution_log_has_send_success(payload: dict[str, Any]) -> bool:
    for item in _response_list(payload, "Results"):
        if not isinstance(item, dict):
            continue
        log = _parse_json_object(item.get("LogJson"))
        notification = str(log.get("notification_send_result", "")).lower()
        if notification == "sendsuccess":
            return True
    return False


def _record(
    resources: list[dict[str, str]], resource_type: str, resource_id: str, name: str
) -> None:
    resources.append({"type": resource_type, "id": resource_id, "name": name})


def _new_run_id() -> str:
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}"
