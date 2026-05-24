from __future__ import annotations

from typing import Any

from cls_cli.cli import app
from tests.conftest import json_output


class PagingClient:
    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self.pages = pages
        self.calls: list[tuple[str, dict[str, Any], str]] = []

    def invoke(self, action: str, payload: dict[str, Any], region: str) -> dict[str, Any]:
        self.calls.append((action, payload, region))
        return self.pages[len(self.calls) - 1]


def _page(total: int, ids: list[str], request_id: str) -> dict[str, Any]:
    return {
        "Response": {
            "TotalCount": total,
            "WebCallbacks": [{"WebCallbackId": item, "Name": item} for item in ids],
            "RequestId": request_id,
        }
    }


def test_alarm_integration_list_uses_offset_limit_and_reports_truncation(runner, tmp_path):
    client = PagingClient([_page(50, [f"callback-{i}" for i in range(20)], "req-page-1")])
    cli_obj = {"client": client, "config_dir": tmp_path / "config"}

    result = runner.invoke(
        app,
        [
            "alarm",
            "integration",
            "list",
            "--region",
            "ap-shanghai",
            "--offset",
            "0",
            "--limit",
            "20",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert client.calls == [("DescribeWebCallbacks", {"Offset": 0, "Limit": 20}, "ap-shanghai")]
    data = json_output(result)["data"]
    assert data["total_count"] == 50
    assert data["fetched_count"] == 20
    assert data["truncated"] is True
    assert data["offset"] == 0
    assert data["limit"] == 20
    assert len(data["Response"]["WebCallbacks"]) == 20


def test_alarm_integration_list_all_fetches_until_total_count(runner, tmp_path):
    client = PagingClient(
        [
            _page(50, [f"callback-{i}" for i in range(20)], "req-page-1"),
            _page(50, [f"callback-{i}" for i in range(20, 40)], "req-page-2"),
            _page(50, [f"callback-{i}" for i in range(40, 50)], "req-page-3"),
        ]
    )
    cli_obj = {"client": client, "config_dir": tmp_path / "config"}

    result = runner.invoke(
        app,
        [
            "alarm",
            "integration",
            "list",
            "--region",
            "ap-shanghai",
            "--all",
            "--limit",
            "20",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert client.calls == [
        ("DescribeWebCallbacks", {"Offset": 0, "Limit": 20}, "ap-shanghai"),
        ("DescribeWebCallbacks", {"Offset": 20, "Limit": 20}, "ap-shanghai"),
        ("DescribeWebCallbacks", {"Offset": 40, "Limit": 20}, "ap-shanghai"),
    ]
    data = json_output(result)["data"]
    assert data["total_count"] == 50
    assert data["fetched_count"] == 50
    assert data["truncated"] is False
    assert data["page_count"] == 3
    assert data["request_ids"] == ["req-page-1", "req-page-2", "req-page-3"]
    assert [item["WebCallbackId"] for item in data["Response"]["WebCallbacks"]] == [
        f"callback-{i}" for i in range(50)
    ]
