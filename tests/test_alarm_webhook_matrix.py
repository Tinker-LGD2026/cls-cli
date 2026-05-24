from __future__ import annotations

import importlib.util
import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen

from cls_cli.cli import app
from cls_cli.core.alarm_webhook_matrix import (
    WebhookCaptureServer,
    WebhookMatrixOptions,
    default_webhook_function_scenarios,
    plan_webhook_function_matrix,
    run_webhook_function_matrix,
    validate_received_payload,
)
from tests.conftest import FakeClsClient, json_output


def _load_simple_webhook_receiver():
    receiver_path = Path(__file__).resolve().parents[1] / "examples" / "simple_webhook_receiver.py"
    spec = importlib.util.spec_from_file_location("simple_webhook_receiver", receiver_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _responses() -> dict[str, dict[str, object]]:
    return {
        "CreateLogset": {"Response": {"LogsetId": "logset-webhook", "RequestId": "req-logset"}},
        "CreateTopic": {"Response": {"TopicId": "topic-webhook", "RequestId": "req-topic"}},
        "CreateIndex": {"Response": {"RequestId": "req-index"}},
        "UploadLog": {"Response": {"RequestId": "req-upload"}},
        "SearchLog": {
            "Response": {
                "AnalysisRecords": [
                    json.dumps(
                        {
                            "error_count": 2,
                            "max_latency": 456,
                            "min_latency": 123,
                            "avg_latency": 289.5,
                            "request_uri": "/api/order",
                            "status": 500,
                            "scenario_id": "fn-matrix",
                            "service": "checkout",
                        }
                    )
                ],
                "Results": [
                    {
                        "LogJson": json.dumps(
                            {
                                "matrix_run_id": "fixed-run",
                                "scenario_id": "fn-matrix",
                                "status": 500,
                                "request_uri": "/api/order",
                                "service": "checkout",
                            }
                        ),
                        "Time": 1710000000123,
                    }
                ],
                "RequestId": "req-search",
            }
        },
        "CreateNoticeContent": {
            "Response": {"NoticeContentId": "notice-content-webhook", "RequestId": "req-content"}
        },
        "CreateWebCallback": {
            "Response": {"WebCallbackId": "web-callback-webhook", "RequestId": "req-web-callback"}
        },
        "CreateAlarmNotice": {
            "Response": {"AlarmNoticeId": "alarm-notice-webhook", "RequestId": "req-notice"}
        },
        "CreateAlarm": {"Response": {"AlarmId": "alarm-webhook", "RequestId": "req-alarm"}},
        "DescribeAlertRecordHistory": {
            "Response": {"Records": [{"RecordId": "record-webhook"}], "RequestId": "req-history"}
        },
        "GetAlarmLog": {
            "Response": {
                "Results": [
                    {
                        "LogJson": json.dumps(
                            {
                                "condition_evaluate_result": "Matched",
                                "notification_send_result": "SendSuccess",
                                "reach_trigger": "true",
                            }
                        )
                    }
                ],
                "RequestId": "req-log",
            }
        },
        "DeleteAlarm": {"Response": {"RequestId": "req-delete-alarm"}},
        "DeleteAlarmNotice": {"Response": {"RequestId": "req-delete-notice"}},
        "DeleteWebCallback": {"Response": {"RequestId": "req-delete-web-callback"}},
        "DeleteNoticeContent": {"Response": {"RequestId": "req-delete-content"}},
        "DeleteIndex": {"Response": {"RequestId": "req-delete-index"}},
        "DeleteTopic": {"Response": {"RequestId": "req-delete-topic"}},
        "DeleteLogset": {"Response": {"RequestId": "req-delete-logset"}},
    }


def _write_received_records(run_dir, run_id: str = "fixed-run") -> None:
    records = []
    for scenario in default_webhook_function_scenarios():
        records.append(
            json.dumps(
                {
                    "parsed_json": {
                        "run_id": run_id,
                        "scenario_id": scenario.id,
                        "case_type": "trigger",
                    },
                    "validation": {"passed": True, "issues": []},
                }
            )
        )
    (run_dir / "received.jsonl").write_text("\n".join(records) + "\n", encoding="utf-8")


def test_default_scenarios_cover_official_variable_functions():
    scenarios = default_webhook_function_scenarios()
    coverage = {fn for scenario in scenarios for fn in scenario.expected_functions}
    ids = [scenario.id for scenario in scenarios]

    assert len(scenarios) == 10
    assert len(set(ids)) == 10
    assert ids == [
        "case-01-direct-vars",
        "case-02-index-special",
        "case-03-range-array",
        "case-04-range-object",
        "case-05-conditions",
        "case-06-escaping-json",
        "case-07-string-url",
        "case-08-time-math",
        "case-09-silence-links",
        "case-10-recovery-template",
    ]
    assert {
        "direct_variable",
        "query_result_extract",
        "query_log_extract",
        "index",
        "range_array",
        "range_object",
        "outer_variable",
        "if_else",
        "comparison",
        "logic",
        "len",
        "whitespace_trim",
        "escape",
        "escape_markdown",
        "escape_markdown_html",
        "toPrettyJson",
        "regexReplaceAll",
        "splitList",
        "url_encode",
        "url_decode",
        "fromUnixTime",
        "date",
        "dateInZone",
        "duration",
        "div",
        "mul",
        "silent_url",
        "recovery_notify_type",
    }.issubset(coverage)
    body = "\n".join(s.template_body for s in scenarios)
    assert "{{range .QueryResult[0]}}" in body
    assert "{{range $key,$value :=" in body
    assert "{{if gt (len .QueryLog) 0}}" in body
    assert "{{else if" in body
    assert "{{url_encode .QueryUrl}}" in body
    assert "{{dateInZone" in body


def test_capture_server_records_json_and_redacts_sensitive_headers(tmp_path):
    received = tmp_path / "received.jsonl"
    with WebhookCaptureServer("127.0.0.1", 0, received) as server:
        req = Request(
            server.local_url,
            data=b'{"run_id":"fixed-run","scenario_id":"fn-matrix"}',
            headers={"Content-Type": "application/json", "Authorization": "Bearer secret"},
            method="POST",
        )
        with urlopen(req, timeout=3) as response:
            assert response.status == 204

    record = json.loads(received.read_text(encoding="utf-8").strip())
    assert record["headers"]["Authorization"] == "<redacted>"
    assert record["parsed_json"] == {"run_id": "fixed-run", "scenario_id": "fn-matrix"}
    assert record["validation"]["passed"] is True
    case_files = list((tmp_path / "case-results").glob("fn-matrix-*.json"))
    assert len(case_files) == 1
    case_record = json.loads(case_files[0].read_text(encoding="utf-8"))
    assert case_record["parsed_json"]["scenario_id"] == "fn-matrix"


def test_validate_received_payload_requires_run_and_scenario():
    ok = validate_received_payload({"run_id": "fixed-run", "scenario_id": "fn-matrix"}, "fixed-run")
    missing = validate_received_payload({"run_id": "other"}, "fixed-run")

    assert ok["passed"] is True
    assert missing["passed"] is False
    assert "run_id" in missing["issues"]
    assert "scenario_id" in missing["issues"]


def test_simple_webhook_receiver_exposes_records_and_summary(tmp_path):
    module = _load_simple_webhook_receiver()
    module.WebhookHandler.output_dir = str(tmp_path)
    server = module.ThreadingSimpleHTTPServer(("127.0.0.1", 0), module.WebhookHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        for scenario_id in ("case-01-direct-vars", "case-02-index-special"):
            req = Request(
                base_url + "/cls-alarm-webhook",
                data=json.dumps(
                    {"run_id": "fixed-run", "scenario_id": scenario_id, "case_type": "trigger"}
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=3) as response:
                assert response.status == 204

        with urlopen(base_url + "/records?run_id=fixed-run", timeout=3) as response:
            records_payload = json.loads(response.read().decode("utf-8"))
        with urlopen(base_url + "/summary?run_id=fixed-run", timeout=3) as response:
            summary_payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert records_payload["count"] == 2
    assert [record["parsed_json"]["scenario_id"] for record in records_payload["records"]] == [
        "case-01-direct-vars",
        "case-02-index-special",
    ]
    assert summary_payload["run_id"] == "fixed-run"
    assert summary_payload["total"] == 2
    assert summary_payload["by_scenario"] == {
        "case-01-direct-vars": 1,
        "case-02-index-special": 1,
    }


def test_webhook_matrix_preflight_requires_public_url_before_cloud_calls(tmp_path):
    client = FakeClsClient(responses=_responses())

    result = run_webhook_function_matrix(
        client,
        WebhookMatrixOptions(
            confirm_real_write=True,
            region="ap-shanghai",
            run_id="fixed-run",
            public_webhook_url=None,
            output_dir=tmp_path,
            start_receiver=False,
        ),
        tunnel_detector=lambda _host, _port: None,
    )

    assert result["status"] == "FAIL"
    assert any(item["phase"] == "public_webhook_url" for item in result["findings"])
    assert client.calls == []


class SequencedSearchClient(FakeClsClient):
    def __init__(self, responses: dict[str, dict[str, object]]) -> None:
        super().__init__(responses=responses)
        self.search_count = 0

    def invoke(self, action: str, payload: dict[str, object], region: str) -> dict[str, object]:
        if action == "SearchLog":
            self.calls.append((action, payload, region))
            self.search_count += 1
            if self.search_count == 2:
                return {"Response": {"AnalysisRecords": [], "Results": [], "RequestId": "empty"}}
            return self.responses[action]
        return super().invoke(action, payload, region)


def test_webhook_matrix_polls_policy_query_until_analysis_records(tmp_path):
    run_dir = tmp_path / "fixed-run"
    run_dir.mkdir()
    _write_received_records(run_dir)
    client = SequencedSearchClient(_responses())

    result = run_webhook_function_matrix(
        client,
        WebhookMatrixOptions(
            confirm_real_write=True,
            region="ap-shanghai",
            run_id="fixed-run",
            public_webhook_url="https://example.com/cls-webhook",
            poll_seconds=1,
            poll_interval_seconds=0,
            output_dir=tmp_path,
            start_receiver=False,
        ),
        sleep=lambda _seconds: None,
    )

    policy_query_calls = [
        call
        for call in client.calls
        if call[0] == "SearchLog" and "select" in call[1]["QueryString"]
    ]
    first_case_queries = [
        call
        for call in policy_query_calls
        if 'scenario_id:"case-01-direct-vars"' in call[1]["QueryString"]
    ]
    assert len(first_case_queries) == 2
    assert len(result["scenario_results"]) == 10
    assert result["scenario_results"][0]["query_matched"] is True


def test_webhook_matrix_external_receiver_does_not_require_local_received_file(tmp_path):
    client = FakeClsClient(responses=_responses())

    result = run_webhook_function_matrix(
        client,
        WebhookMatrixOptions(
            confirm_real_write=True,
            region="ap-shanghai",
            run_id="fixed-run",
            public_webhook_url="https://public.example.com/cls-alarm-webhook",
            poll_seconds=0,
            poll_interval_seconds=0,
            output_dir=tmp_path,
            start_receiver=False,
            external_receiver=True,
        ),
    )

    assert result["status"] == "PASS"
    assert len(result["scenario_results"]) == 10
    assert all(item["external_receiver"] is True for item in result["scenario_results"])
    assert all(item["webhook_received"] is True for item in result["scenario_results"])


def test_webhook_matrix_external_receiver_can_validate_optional_remote_records(tmp_path):
    client = FakeClsClient(responses=_responses())

    def load_records(result_url: str, run_id: str):
        assert result_url == "http://receiver.example/records"
        assert run_id == "fixed-run"
        return [
            {
                "parsed_json": {
                    "run_id": "fixed-run",
                    "scenario_id": scenario.id,
                    "case_type": "trigger",
                },
                "validation": {"passed": True, "issues": []},
            }
            for scenario in default_webhook_function_scenarios()
        ]

    result = run_webhook_function_matrix(
        client,
        WebhookMatrixOptions(
            confirm_real_write=True,
            region="ap-shanghai",
            run_id="fixed-run",
            public_webhook_url="https://public.example.com/cls-alarm-webhook",
            external_receiver_result_url="http://receiver.example/records",
            poll_seconds=0,
            poll_interval_seconds=0,
            output_dir=tmp_path,
            start_receiver=False,
            external_receiver=True,
        ),
        external_receiver_loader=load_records,
    )

    assert result["status"] == "PASS"
    assert all(item["webhook_received"] is True for item in result["scenario_results"])
    assert all(
        item["external_receiver_result_url"] == "<configured>"
        for item in result["scenario_results"]
    )


def test_webhook_matrix_external_receiver_result_url_reports_missing_records(tmp_path):
    client = FakeClsClient(responses=_responses())

    result = run_webhook_function_matrix(
        client,
        WebhookMatrixOptions(
            confirm_real_write=True,
            region="ap-shanghai",
            run_id="fixed-run",
            public_webhook_url="https://public.example.com/cls-alarm-webhook",
            external_receiver_result_url="http://receiver.example/records",
            poll_seconds=0,
            poll_interval_seconds=0,
            output_dir=tmp_path,
            start_receiver=False,
            external_receiver=True,
        ),
        external_receiver_loader=lambda _url, _run_id: [],
    )

    assert result["status"] == "PARTIAL"
    assert all(item["send_success"] is True for item in result["scenario_results"])
    assert all(item["webhook_received"] is False for item in result["scenario_results"])
    assert any(item["phase"] == "external_webhook_receive" for item in result["findings"])


def test_webhook_matrix_creates_http_webhook_only_and_cleans_up(tmp_path):
    run_dir = tmp_path / "fixed-run"
    run_dir.mkdir()
    _write_received_records(run_dir)
    client = FakeClsClient(responses=_responses())

    result = run_webhook_function_matrix(
        client,
        WebhookMatrixOptions(
            confirm_real_write=True,
            region="ap-shanghai",
            run_id="fixed-run",
            public_webhook_url="https://example.com/cls-webhook",
            poll_seconds=0,
            poll_interval_seconds=0,
            output_dir=tmp_path,
            start_receiver=False,
        ),
    )

    assert result["status"] == "PASS"
    actions = [call[0] for call in client.calls]
    assert actions.count("CreateWebCallback") == 10
    assert actions.count("CreateAlarmNotice") == 10
    assert actions.count("CreateAlarm") == 10
    assert "CreateMachineGroup" not in actions
    create_alarm_payload = next(
        payload for action, payload, _ in client.calls if action == "CreateAlarm"
    )
    assert create_alarm_payload["AlarmPeriod"] == 15
    assert create_alarm_payload["TriggerCount"] == 1
    assert create_alarm_payload["MonitorObjectType"] == 0
    assert create_alarm_payload["AlarmTargets"][0]["SyntaxRule"] == 1
    policy_query_payload = next(
        payload
        for action, payload, _ in client.calls
        if action == "SearchLog" and "select" in payload["QueryString"]
    )
    assert policy_query_payload["UseNewAnalysis"] is True
    notice_content_payload = next(
        payload for action, payload, _ in client.calls if action == "CreateNoticeContent"
    )
    content = notice_content_payload["NoticeContents"][0]["TriggerContent"]
    assert content["Headers"] == ["Content-Type:application/json"]
    callback_payload = next(
        payload for action, payload, _ in client.calls if action == "CreateWebCallback"
    )
    assert callback_payload["Type"] == "Http"
    assert callback_payload["Method"] == "POST"
    notice_payload = next(
        payload for action, payload, _ in client.calls if action == "CreateAlarmNotice"
    )
    assert notice_payload["WebCallbacks"] == [
        {
            "CallbackType": "Http",
            "Url": "",
            "WebCallbackId": "web-callback-webhook",
            "NoticeContentId": "notice-content-webhook",
            "Method": "POST",
        }
    ]
    assert actions.count("DeleteAlarm") == 10
    assert actions.count("DeleteAlarmNotice") == 10
    assert actions[-3:] == ["DeleteIndex", "DeleteTopic", "DeleteLogset"]


def test_webhook_matrix_can_select_case_subset():
    options = WebhookMatrixOptions(
        region="ap-shanghai",
        case_ids=["case-06-escaping-json", "case-10-recovery-template"],
    )

    plan = plan_webhook_function_matrix(options)

    assert plan["scenario_count"] == 2
    assert plan["scenario_ids"] == ["case-06-escaping-json", "case-10-recovery-template"]
    assert "escape_markdown" in plan["covered_functions"]
    assert "recovery_notify_type" in plan["covered_functions"]



def test_webhook_matrix_cli_dry_run_makes_no_cloud_calls(runner, cli_obj, fake_client, tmp_path):
    result = runner.invoke(
        app,
        [
            "alarm",
            "verify",
            "webhook-functions",
            "--region",
            "ap-shanghai",
            "--dry-run",
            "--output-dir",
            str(tmp_path),
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    data = json_output(result)["data"]
    assert data["dry_run"] is True
    assert data["region"] == "ap-shanghai"
    assert "CreateWebCallback" in data["planned_actions"]
    assert fake_client.calls == []


def test_plan_webhook_function_matrix_redacts_public_url(tmp_path):
    plan = plan_webhook_function_matrix(
        WebhookMatrixOptions(
            confirm_real_write=False,
            region="ap-shanghai",
            public_webhook_url="https://example.com/hook?key=private-token",
            output_dir=tmp_path,
        )
    )

    assert "private-token" not in json.dumps(plan)
    assert plan["public_webhook_url"] == "<configured>"
