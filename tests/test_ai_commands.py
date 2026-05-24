from __future__ import annotations

from cls_cli.cli import app
from cls_cli.core.ai import extract_query_from_content
from tests.conftest import json_output


def _chat_response() -> dict[str, object]:
    return {
        "Response": {
            "Id": "chatcmpl-1",
            "Model": "text2sql",
            "Created": 1775102996,
            "Choices": [
                {
                    "Message": {
                        "Role": "assistant",
                        "Content": (
                            "建议查询：\n```sql\n"
                            "status:>=500 | select count(*) as error_count\n```"
                        ),
                        "ReasoningContent": "根据 status 字段过滤 5xx。",
                    },
                    "FinishReason": "stop",
                }
            ],
            "Usage": {"PromptTokens": 10, "CompletionTokens": 20, "TotalTokens": 30},
            "RequestId": "req-ai-1",
        }
    }


def test_ai_generate_query_invokes_chat_completions_with_topic_metadata(
    runner, cli_obj, fake_client
):
    fake_client.responses = {"ChatCompletions": _chat_response()}

    result = runner.invoke(
        app,
        [
            "ai",
            "generate-query",
            "统计 5xx 错误数",
            "--topic-id",
            "topic-123",
            "--topic-region",
            "ap-shanghai",
            "--region",
            "ap-guangzhou",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "ChatCompletions",
            {
                "Model": "text2sql",
                "Messages": [{"Role": "user", "Content": "统计 5xx 错误数"}],
                "Stream": False,
                "Metadata": [
                    {"Key": "topic_id", "Value": "topic-123"},
                    {"Key": "topic_region", "Value": "ap-shanghai"},
                ],
            },
            "ap-guangzhou",
        )
    ]
    data = json_output(result)["data"]
    assert data["model"] == "text2sql"
    assert data["query"] == "status:>=500 | select count(*) as error_count"
    assert data["reasoning_content"] == "根据 status 字段过滤 5xx。"
    assert data["usage"] == {"PromptTokens": 10, "CompletionTokens": 20, "TotalTokens": 30}
    assert data["request_id"] == "req-ai-1"


def test_ai_generate_query_supports_reasoning_model_and_only_query_output(
    runner, cli_obj, fake_client
):
    fake_client.responses = {"ChatCompletions": _chat_response()}

    result = runner.invoke(
        app,
        [
            "ai",
            "generate-query",
            "统计 5xx 错误数",
            "--topic-id",
            "topic-123",
            "--topic-region",
            "ap-shanghai",
            "--model",
            "text2sql-reasoning",
            "--only-query",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip() == "status:>=500 | select count(*) as error_count"
    assert fake_client.calls[0][1]["Model"] == "text2sql-reasoning"


def test_ai_generate_query_rejects_unsupported_model(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        [
            "ai",
            "generate-query",
            "统计错误",
            "--topic-id",
            "topic-123",
            "--topic-region",
            "ap-shanghai",
            "--model",
            "other",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 1
    assert json_output(result)["error"]["code"] == "INPUT_ERROR"
    assert fake_client.calls == []


def test_extract_query_from_content_prefers_sql_fence():
    content = "说明\n```sql\nlevel:ERROR | select count(*) as error_count\n```"

    assert extract_query_from_content(content) == "level:ERROR | select count(*) as error_count"


def test_extract_query_from_content_falls_back_to_query_like_line():
    assert extract_query_from_content("可使用：status:>=500 | select count(*) as c") == (
        "status:>=500 | select count(*) as c"
    )


def test_ai_generate_query_normalizes_aliases(runner, cli_obj, fake_client):
    fake_client.responses = {
        "ChatCompletions": {
            "Response": {
                "Model": "text2sql",
                "Choices": [
                    {
                        "Message": {
                            "Content": (
                                "```sql\n"
                                "status>=500 | SELECT request_uri, count(*) AS \"5xx错误数量\" "
                                "GROUP BY request_uri ORDER BY \"5xx错误数量\" DESC\n"
                                "```"
                            )
                        },
                        "FinishReason": "stop",
                    }
                ],
                "RequestId": "req-ai-normalize",
            }
        }
    }

    result = runner.invoke(
        app,
        [
            "ai",
            "generate-query",
            "统计 5xx 错误数",
            "--topic-id",
            "topic-123",
            "--topic-region",
            "ap-shanghai",
            "--normalize-aliases",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    data = json_output(result)["data"]
    assert data["original_query"] == (
        'status>=500 | SELECT request_uri, count(*) AS "5xx错误数量" '
        'GROUP BY request_uri ORDER BY "5xx错误数量" DESC'
    )
    assert data["query"] == (
        "status>=500 | SELECT request_uri, count(*) AS error_count "
        "GROUP BY request_uri ORDER BY error_count DESC"
    )
    assert data["alias_map"] == {"5xx错误数量": "error_count"}
    assert data["condition_hints"] == ["$1.error_count > 0"]


def test_ai_generate_query_dry_run_outputs_chat_payload_without_cloud_call(
    runner, cli_obj, fake_client
):
    result = runner.invoke(
        app,
        [
            "ai",
            "generate-query",
            "统计 5xx 错误数",
            "--topic-id",
            "topic-123",
            "--topic-region",
            "ap-shanghai",
            "--dry-run",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == []
    data = json_output(result)["data"]
    assert data["dry_run"] is True
    assert data["action"] == "ChatCompletions"
    assert data["payload"]["Metadata"] == [
        {"Key": "topic_id", "Value": "topic-123"},
        {"Key": "topic_region", "Value": "ap-shanghai"},
    ]


def test_ai_generate_query_can_validate_generated_query_with_search_log(
    runner, cli_obj, fake_client
):
    fake_client.responses = {
        "ChatCompletions": _chat_response(),
        "SearchLog": {
            "Response": {
                "AnalysisRecords": ['{"error_count": 3}'],
                "Results": [],
                "RequestId": "req-search",
            }
        },
    }

    result = runner.invoke(
        app,
        [
            "ai",
            "generate-query",
            "统计 5xx 错误数",
            "--topic-id",
            "topic-123",
            "--topic-region",
            "ap-shanghai",
            "--validate-query",
            "--from",
            "1710000000",
            "--to",
            "1710003600",
            "--limit",
            "20",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert [call[0] for call in fake_client.calls] == ["ChatCompletions", "SearchLog"]
    assert fake_client.calls[1] == (
        "SearchLog",
        {
            "TopicId": "topic-123",
            "QueryString": "status:>=500 | select count(*) as error_count",
            "From": 1710000000000,
            "To": 1710003600000,
            "Limit": 20,
        },
        "ap-shanghai",
    )
    data = json_output(result)["data"]
    assert data["query_validation"]["passed"] is True
    assert data["query_validation"]["request_id"] == "req-search"


def test_ai_generate_query_only_query_uses_normalized_alias(runner, cli_obj, fake_client):
    fake_client.responses = {
        "ChatCompletions": {
            "Response": {
                "Model": "text2sql",
                "Choices": [
                    {
                        "Message": {"Content": 'status>=500 | SELECT count(*) AS "错误数量"'},
                        "FinishReason": "stop",
                    }
                ],
            }
        }
    }

    result = runner.invoke(
        app,
        [
            "ai",
            "generate-query",
            "统计错误数",
            "--topic-id",
            "topic-123",
            "--topic-region",
            "ap-shanghai",
            "--normalize-aliases",
            "--only-query",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip() == "status>=500 | SELECT count(*) AS error_count"
