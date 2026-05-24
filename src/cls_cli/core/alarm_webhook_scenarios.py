from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebhookFunctionScenario:
    id: str
    title: str
    query: str
    condition: str
    template_body: str
    expected_json_paths: dict[str, str]
    expected_functions: list[str]


def default_webhook_function_scenarios() -> list[WebhookFunctionScenario]:
    return [
        _scenario(
            "case-01-direct-vars",
            "直接变量与 QueryResult 字段提取",
            [
                "direct_variable",
                "query_result_extract",
                "escape",
            ],
            [
                '  "alarm": "{{escape .Alarm}}"',
                '  "alarm_id": "{{escape .AlarmID}}"',
                '  "region": "{{escape .Region}}"',
                '  "notify_type": "{{.NotifyType}}"',
                '  "first_uri": "{{escape .QueryResult[0][0].request_uri}}"',
                '  "first_status": "{{.QueryResult[0][0].status}}"',
            ],
        ),
        _scenario(
            "case-02-index-special",
            "index 访问数组、对象和特殊字段名",
            ["index", "query_log_extract", "escape"],
            [
                '  "status_by_index": "{{index .QueryResult 0 0 "status"}}"',
                '  "service_by_index": "{{index .QueryLog 0 0 "content" "service"}}"',
                '  "dash_field": "{{index (index .QueryLog 0 0 "content") "field-with-dash"}}"',
                '  "space_field": "{{index (index .QueryLog 0 0 "content") "field space"}}"',
                '  "dollar_field": "{{index (index .QueryLog 0 0 "content") "$special"}}"',
            ],
        ),
        _scenario(
            "case-03-range-array",
            "range 遍历 QueryResult 数组",
            ["range_array", "query_result_extract", "escape"],
            [
                (
                    '  "range_rows": "{{range .QueryResult[0]}}'
                    '{{escape .request_uri}}:{{.status}};{{end}}"'
                ),
                '  "range_services": "{{range .QueryResult[0]}}{{escape .service}};{{end}}"',
            ],
        ),
        _scenario(
            "case-04-range-object",
            "range 遍历 QueryLog content 对象",
            ["range_object", "query_log_extract", "escape"],
            [
                (
                    '  "range_object": "{{range $key,$value := index .QueryLog 0 0 '
                    '"content"}}{{escape $key}}={{escape $value}};{{end}}"'
                ),
            ],
        ),
        _scenario(
            "case-05-conditions",
            "条件、比较、逻辑和 len 防越界",
            ["if_else", "comparison", "logic", "len", "whitespace_trim"],
            [
                '  "len_guard": "{{if gt (len .QueryLog) 0}}has_logs{{else}}no_logs{{end}}"',
                (
                    '  "condition_branch": "{{if and (gt .ConsecutiveAlertNums 0) '
                    '(eq .NotifyType 1)}}trigger{{else if eq .NotifyType 2}}'
                    'recovery{{else}}other{{end}}"'
                ),
                (
                    '  "comparison_branch": "{{if ge (index .QueryResult 0 0 '
                    '"max_latency") 400}}slow{{else}}normal{{end}}"'
                ),
                (
                    '  "logic_branch": "{{if or (eq .Level "warn") (not .CanSilent)}}'
                    'active{{else}}silent{{end}}"'
                ),
                '  "trimmed_alarm": "{{- escape .Alarm -}}"',
            ],
        ),
        _scenario(
            "case-06-escaping-json",
            "转义函数与 toPrettyJson",
            ["escape", "escape_markdown", "escape_markdown_html", "toPrettyJson"],
            [
                '  "escaped_message": "{{escape .Message}}"',
                '  "markdown_message": "{{escape_markdown .Message}}"',
                '  "markdown_html_message": "{{escape_markdown_html .Message}}"',
                '  "pretty_query_result": {{toPrettyJson .QueryResult}}',
            ],
        ),
        _scenario(
            "case-07-string-url",
            "字符串、列表与 URL 函数",
            ["regexReplaceAll", "splitList", "url_encode", "url_decode"],
            [
                '  "regex_message": "{{regexReplaceAll "[0-9]+" .Message "#"}}"',
                '  "split_params": "{{range (splitList ";" .TriggerParams)}}{{escape .}}|{{end}}"',
                '  "encoded_query_url": "{{url_encode .QueryUrl}}"',
                '  "decoded_url": "{{url_decode "a%2Fb%3Fc%3D1"}}"',
            ],
        ),
        _scenario(
            "case-08-time-math",
            "时间与算术函数",
            ["fromUnixTime", "date", "dateInZone", "duration", "div", "mul"],
            [
                '  "start_date": "{{date "2006-01-02" (fromUnixTime .StartTimeUnix)}}"',
                (
                    '  "notify_time_shanghai": "{{dateInZone "2006-01-02 15:04:05" '
                    '(fromUnixTime .NotifyTimeUnix) "Asia/Shanghai"}}"'
                ),
                '  "duration_text": "{{duration .Duration}}"',
                '  "duration_minutes": "{{div .Duration 60}}"',
                '  "duration_ms": "{{mul .Duration 1000}}"',
            ],
        ),
        _scenario(
            "case-09-silence-links",
            "静默链接和控制台链接变量",
            ["silent_url", "if_else", "url_encode"],
            [
                '  "detail_url": "{{escape .DetailUrl}}"',
                '  "query_url": "{{escape .QueryUrl}}"',
                '  "encoded_detail_url": "{{url_encode .DetailUrl}}"',
                '  "silent_link": "{{if .CanSilent}}{{.SilentUrl}}{{else}}not_supported{{end}}"',
            ],
        ),
        _scenario(
            "case-10-recovery-template",
            "恢复通知模板与外层变量保存",
            ["recovery_notify_type", "outer_variable", "range_array", "escape"],
            [
                '  "trigger_notify_type": "{{.NotifyType}}"',
                '  "trigger_result_used": true',
                (
                    '  "outer_variable": "{{$alarm := .Alarm}}{{range .QueryResult[0]}}'
                    '{{escape $alarm}}/{{escape .scenario_id}};{{end}}"'
                ),
            ],
        ),
    ]


def select_webhook_function_scenarios(
    case_ids: list[str] | None,
) -> list[WebhookFunctionScenario]:
    scenarios = default_webhook_function_scenarios()
    if not case_ids:
        return scenarios
    by_id = {scenario.id: scenario for scenario in scenarios}
    unknown = [case_id for case_id in case_ids if case_id not in by_id]
    if unknown:
        raise ValueError(f"unknown webhook function case id: {', '.join(unknown)}")
    return [by_id[case_id] for case_id in case_ids]


def instantiate_webhook_function_scenarios(
    scenarios: list[WebhookFunctionScenario], run_id: str
) -> list[WebhookFunctionScenario]:
    return [
        WebhookFunctionScenario(
            id=scenario.id,
            title=scenario.title,
            query=scenario.query.replace("__RUN_ID__", run_id),
            condition=scenario.condition,
            template_body=scenario.template_body.replace("__RUN_ID__", run_id),
            expected_json_paths={
                key: value.replace("__RUN_ID__", run_id)
                for key, value in scenario.expected_json_paths.items()
            },
            expected_functions=scenario.expected_functions,
        )
        for scenario in scenarios
    ]


def recovery_body(scenario_id: str) -> str:
    return (
        "{\n"
        '  "run_id": "__RUN_ID__",\n'
        f'  "scenario_id": "{scenario_id}",\n'
        '  "case_type": "recovery",\n'
        '  "notify_type": "{{.NotifyType}}",\n'
        '  "recovery_state": "{{if eq .NotifyType 2}}recovered{{else}}not_recovery{{end}}",\n'
        '  "trigger_result_used": false\n'
        "}"
    )


def _scenario(
    scenario_id: str,
    title: str,
    expected_functions: list[str],
    fields: list[str],
) -> WebhookFunctionScenario:
    return WebhookFunctionScenario(
        id=scenario_id,
        title=title,
        query=_scenario_query(scenario_id),
        condition="$1.error_count > 0",
        template_body=_json_body(scenario_id, fields),
        expected_json_paths={"run_id": "__RUN_ID__", "scenario_id": scenario_id},
        expected_functions=expected_functions,
    )


def _scenario_query(scenario_id: str) -> str:
    return (
        f'matrix_run_id:"__RUN_ID__" AND scenario_id:"{scenario_id}" AND status:>=500 '
        "| select count(*) as error_count, max(latency_ms) as max_latency, "
        "min(latency_ms) as min_latency, avg(latency_ms) as avg_latency, "
        "request_uri, status, scenario_id, service "
        "group by request_uri,status,scenario_id,service "
        "order by error_count desc limit 10"
    )


def _json_body(scenario_id: str, fields: list[str]) -> str:
    base_fields = [
        '  "run_id": "__RUN_ID__"',
        f'  "scenario_id": "{scenario_id}"',
        '  "case_type": "trigger"',
    ]
    return "{\n" + ",\n".join([*base_fields, *fields]) + "\n}"
