from __future__ import annotations

from cls_cli.core.query_alias_normalizer import normalize_query_aliases


def test_normalize_query_aliases_rewrites_quoted_chinese_alias():
    result = normalize_query_aliases(
        'status>=500 | SELECT request_uri, count(*) AS "5xx错误数量" '
        'GROUP BY request_uri ORDER BY "5xx错误数量" DESC'
    )

    assert result.query == (
        "status>=500 | SELECT request_uri, count(*) AS error_count "
        "GROUP BY request_uri ORDER BY error_count DESC"
    )
    assert result.alias_map == {"5xx错误数量": "error_count"}
    assert result.condition_hints == ["$1.error_count > 0"]


def test_normalize_query_aliases_preserves_strict_alias():
    result = normalize_query_aliases(
        "status>=500 | SELECT count(*) AS error_count ORDER BY error_count DESC"
    )

    assert result.query == "status>=500 | SELECT count(*) AS error_count ORDER BY error_count DESC"
    assert result.alias_map == {}
    assert result.condition_hints == []


def test_normalize_query_aliases_generates_unique_aliases():
    result = normalize_query_aliases(
        'status>=500 | SELECT count(*) AS "错误数量", max(latency_ms) AS "错误数量"'
    )

    assert result.query == (
        "status>=500 | SELECT count(*) AS error_count, max(latency_ms) AS error_count_2"
    )
    assert result.alias_map == {"错误数量": "error_count_2"}
    assert result.condition_hints == ["$1.error_count > 0", "$1.error_count_2 > 0"]
