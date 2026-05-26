from __future__ import annotations

from typing import Any

import typer

from cls_cli.core.alarm_discovery import discovery_result, filter_by_name
from cls_cli.core.config import store_from_obj
from cls_cli.core.errors import CliError
from cls_cli.core.execution import _client, _obj, _resolve_region
from cls_cli.core.output import emit_data, emit_error

app = typer.Typer(no_args_is_help=True, help="Discover existing alarm resources by name.")


@app.command("integration")
def discover_integration(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    allow_multiple: bool = typer.Option(False, "--allow-multiple"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    _discover(
        ctx,
        resource="integration",
        action="DescribeWebCallbacks",
        item_key="WebCallbacks",
        id_key="WebCallbackId",
        name=name,
        base_payload={},
        limit=20,
        allow_multiple=allow_multiple,
        region=region,
        profile=profile,
        output=output,
    )


@app.command("notice")
def discover_notice(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    allow_multiple: bool = typer.Option(False, "--allow-multiple"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    _discover(
        ctx,
        resource="notice",
        action="DescribeAlarmNotices",
        item_key="AlarmNotices",
        id_key="AlarmNoticeId",
        name=name,
        base_payload={},
        limit=100,
        allow_multiple=allow_multiple,
        region=region,
        profile=profile,
        output=output,
    )


@app.command("notice-content")
def discover_notice_content(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    allow_multiple: bool = typer.Option(False, "--allow-multiple"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    _discover(
        ctx,
        resource="notice_content",
        action="DescribeNoticeContents",
        item_key="NoticeContents",
        id_key="NoticeContentId",
        name=name,
        base_payload={},
        limit=100,
        allow_multiple=allow_multiple,
        region=region,
        profile=profile,
        output=output,
    )


@app.command("policy")
def discover_policy(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    topic_id: str | None = typer.Option(None, "--topic-id"),
    allow_multiple: bool = typer.Option(False, "--allow-multiple"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
) -> None:
    filters = []
    if topic_id:
        filters.append({"Key": "topicId", "Values": [topic_id]})
    base_payload = {"Filters": filters} if filters else {}
    _discover(
        ctx,
        resource="policy",
        action="DescribeAlarms",
        item_key="Alarms",
        id_key="AlarmId",
        name=name,
        base_payload=base_payload,
        limit=100,
        allow_multiple=allow_multiple,
        region=region,
        profile=profile,
        output=output,
    )


def _discover(
    ctx: typer.Context,
    *,
    resource: str,
    action: str,
    item_key: str,
    id_key: str,
    name: str,
    base_payload: dict[str, Any],
    limit: int,
    allow_multiple: bool,
    region: str | None,
    profile: str | None,
    output: str,
) -> None:
    try:
        store = store_from_obj(_obj(ctx))
        profile_obj = store.get_profile(profile)
        selected_region = _resolve_region(region, profile_obj)
        items, request_ids = _list_all(
            _client(ctx, profile_obj), action, base_payload, item_key, selected_region, limit
        )
        matches = filter_by_name(items, name)
        result = discovery_result(resource, matches, id_key, request_ids=request_ids)
        emit_data(result, output)
        if result["match_count"] != 1 and not allow_multiple:
            raise typer.Exit(1)
    except CliError as exc:
        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc


def _list_all(
    client: Any,
    action: str,
    base_payload: dict[str, Any],
    item_key: str,
    region: str,
    limit: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    offset = 0
    items: list[dict[str, Any]] = []
    request_ids: list[str] = []
    while True:
        payload = {**base_payload, "Offset": offset, "Limit": limit}
        response = client.invoke(action, payload, region).get("Response", {})
        page_items = response.get(item_key) or []
        if isinstance(page_items, list):
            items.extend([item for item in page_items if isinstance(item, dict)])
        request_id = response.get("RequestId")
        if request_id:
            request_ids.append(str(request_id))
        total = _total_count(response, len(items))
        if len(items) >= total or not page_items:
            return items, request_ids
        offset += limit


def _total_count(response: dict[str, Any], fallback: int) -> int:
    value = response.get("TotalCount")
    return value if isinstance(value, int) and value >= 0 else fallback
