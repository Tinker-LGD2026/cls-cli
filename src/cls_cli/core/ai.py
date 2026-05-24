from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from cls_cli.core.errors import InputError

AI_MODELS = {"text2sql", "text2sql-reasoning"}
_SQL_FENCE_RE = re.compile(r"```(?:sql|cql)?\s*\n(?P<query>.*?)\n```", re.IGNORECASE | re.DOTALL)
_QUERY_LINE_RE = re.compile(r"(?P<query>[^\n]*(?:\||select\s+|SELECT\s+)[^\n]*)")


@dataclass(frozen=True)
class GenerateQueryOptions:
    prompt: str
    topic_id: str
    topic_region: str
    model: str = "text2sql"


def build_chat_completions_payload(options: GenerateQueryOptions) -> dict[str, Any]:
    model = options.model.strip()
    if model not in AI_MODELS:
        raise InputError("model must be one of: text2sql, text2sql-reasoning")
    if not options.prompt.strip():
        raise InputError("prompt is required")
    if not options.topic_id.strip():
        raise InputError("topic-id is required")
    if not options.topic_region.strip():
        raise InputError("topic-region is required")
    return {
        "Model": model,
        "Messages": [{"Role": "user", "Content": options.prompt}],
        "Stream": False,
        "Metadata": [
            {"Key": "topic_id", "Value": options.topic_id},
            {"Key": "topic_region", "Value": options.topic_region},
        ],
    }


def generate_query(client: Any, region: str, options: GenerateQueryOptions) -> dict[str, Any]:
    payload = build_chat_completions_payload(options)
    response = client.invoke("ChatCompletions", payload, region)
    return normalize_chat_completions_response(response, options)


def normalize_chat_completions_response(
    response: dict[str, Any], options: GenerateQueryOptions
) -> dict[str, Any]:
    body = response.get("Response", {})
    message = _first_message(body)
    content = str(message.get("Content") or "")
    reasoning_content = message.get("ReasoningContent")
    finish_reason = _first_choice(body).get("FinishReason")
    return {
        "model": str(body.get("Model") or options.model),
        "topic_id": options.topic_id,
        "topic_region": options.topic_region,
        "content": content,
        "query": extract_query_from_content(content),
        "reasoning_content": reasoning_content,
        "finish_reason": finish_reason,
        "usage": body.get("Usage") or {},
        "id": body.get("Id"),
        "request_id": body.get("RequestId"),
    }


def extract_query_from_content(content: str) -> str:
    fence = _SQL_FENCE_RE.search(content)
    if fence:
        return fence.group("query").strip()
    for line in content.splitlines():
        match = _QUERY_LINE_RE.search(line.strip())
        if match:
            return _strip_query_prefix(match.group("query").strip())
    return ""


def _first_choice(body: dict[str, Any]) -> dict[str, Any]:
    choices = body.get("Choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        return choices[0]
    return {}


def _first_message(body: dict[str, Any]) -> dict[str, Any]:
    message = _first_choice(body).get("Message")
    return message if isinstance(message, dict) else {}


def _strip_query_prefix(value: str) -> str:
    if "：" in value:
        return value.split("：", 1)[1].strip()
    lowered = value.lower()
    for prefix in ("query:", "sql:", "cql:"):
        if lowered.startswith(prefix):
            return value[len(prefix) :].strip()
    return value
