from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from cls_cli.core.errors import ConfirmationRequired, InputError


@dataclass(frozen=True)
class AlarmCleanupOptions:
    prefix: str
    force: bool = False
    dry_run: bool = False
    older_than_seconds: int | None = None


_LIST_SPECS: tuple[dict[str, Any], ...] = (
    {
        "type": "alarm",
        "list_action": "DescribeAlarms",
        "list_keys": ("Alarms",),
        "id_keys": ("AlarmId",),
        "name_keys": ("Name", "AlarmName"),
    },
    {
        "type": "alarm_notice",
        "list_action": "DescribeAlarmNotices",
        "list_keys": ("AlarmNotices", "Notices"),
        "id_keys": ("AlarmNoticeId",),
        "name_keys": ("Name", "AlarmNoticeName"),
    },
    {
        "type": "web_callback",
        "list_action": "DescribeWebCallbacks",
        "list_keys": ("WebCallbacks", "Callbacks"),
        "id_keys": ("WebCallbackId",),
        "name_keys": ("Name", "WebCallbackName"),
    },
    {
        "type": "notice_content",
        "list_action": "DescribeNoticeContents",
        "list_keys": ("NoticeContents", "Contents"),
        "id_keys": ("NoticeContentId",),
        "name_keys": ("Name", "NoticeContentName"),
    },
)

_DELETE_SPECS = {
    "alarm": ("DeleteAlarm", "AlarmId"),
    "alarm_notice": ("DeleteAlarmNotice", "AlarmNoticeId"),
    "web_callback": ("DeleteWebCallback", "WebCallbackId"),
    "notice_content": ("DeleteNoticeContent", "NoticeContentId"),
    "index": ("DeleteIndex", "TopicId"),
    "topic": ("DeleteTopic", "TopicId"),
    "logset": ("DeleteLogset", "LogsetId"),
}

_DURATION_RE = re.compile(r"^(\d+)([smhd]?)$")
_DURATION_UNITS = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_older_than(value: str | None) -> int | None:
    if value is None:
        return None
    match = _DURATION_RE.match(value.strip().lower())
    if not match:
        raise InputError("older-than must use seconds or s/m/h/d suffix, for example 3600 or 24h")
    amount = int(match.group(1))
    return amount * _DURATION_UNITS[match.group(2)]


def run_alarm_cleanup(
    client: Any,
    region: str,
    options: AlarmCleanupOptions,
    *,
    now: Callable[[], float] = time.time,
) -> dict[str, Any]:
    if not options.prefix:
        raise InputError("prefix is required")
    if not options.dry_run and not options.force:
        raise ConfirmationRequired("cleanup deletes CLS resources; pass --force or use --dry-run")

    skipped: list[dict[str, Any]] = []
    resources = _discover_resources(client, region, options, now, skipped)
    cleanup_results: list[dict[str, Any]] = []

    if options.dry_run:
        status = "DRY_RUN"
    else:
        cleanup_results = _delete_resources(client, region, resources)
        status = (
            "PASS" if all(item["status"] == "deleted" for item in cleanup_results) else "PARTIAL"
        )

    failed_count = sum(1 for item in cleanup_results if item["status"] == "failed")
    deleted_count = sum(1 for item in cleanup_results if item["status"] == "deleted")
    return {
        "status": status,
        "region": region,
        "prefix": options.prefix,
        "older_than_seconds": options.older_than_seconds,
        "dry_run": options.dry_run,
        "resources": resources,
        "cleanup": cleanup_results,
        "skipped": skipped,
        "summary": {
            "matched": len(resources),
            "deleted": deleted_count,
            "failed": failed_count,
            "skipped": len(skipped),
        },
    }


def _discover_resources(
    client: Any,
    region: str,
    options: AlarmCleanupOptions,
    now: Callable[[], float],
    skipped: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for spec in _LIST_SPECS:
        response = client.invoke(spec["list_action"], {}, region)
        for item in _response_items(response, spec["list_keys"]):
            resource = _resource_from_item(item, spec)
            if _matches_resource(resource, item, options, now, skipped):
                resources.append(resource)

    logsets = []
    for item in _response_items(client.invoke("DescribeLogsets", {}, region), ("Logsets",)):
        resource = _resource_from_item(
            item,
            {
                "type": "logset",
                "id_keys": ("LogsetId",),
                "name_keys": ("LogsetName", "Name"),
            },
        )
        if _matches_resource(resource, item, options, now, skipped):
            logsets.append(resource)

    for logset in logsets:
        topic_payload = {"Filters": [{"Key": "logsetId", "Values": [logset["id"]]}]}
        topic_response = client.invoke("DescribeTopics", topic_payload, region)
        for item in _response_items(topic_response, ("Topics",)):
            topic = _resource_from_item(
                item,
                {
                    "type": "topic",
                    "id_keys": ("TopicId",),
                    "name_keys": ("TopicName", "Name"),
                },
            )
            topic["logset_id"] = logset["id"]
            if _matches_topic(topic, item, logset, options, now, skipped):
                resources.append({"type": "index", "id": topic["id"], "name": topic["name"]})
                resources.append(topic)
        resources.append(logset)
    return resources


def _response_items(response: dict[str, Any], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    body = response.get("Response", {})
    for key in keys:
        value = body.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _resource_from_item(item: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    resource_id = _first_text(item, spec["id_keys"])
    name = _first_text(item, spec["name_keys"])
    return {"type": spec["type"], "id": resource_id, "name": name}


def _matches_resource(
    resource: dict[str, Any],
    item: dict[str, Any],
    options: AlarmCleanupOptions,
    now: Callable[[], float],
    skipped: list[dict[str, Any]],
) -> bool:
    if not resource["id"] or not str(resource["name"]).startswith(options.prefix):
        return False
    return _passes_age_filter(resource, item, options, now, skipped)


def _matches_topic(
    topic: dict[str, Any],
    item: dict[str, Any],
    logset: dict[str, Any],
    options: AlarmCleanupOptions,
    now: Callable[[], float],
    skipped: list[dict[str, Any]],
) -> bool:
    if not topic["id"]:
        return False
    topic_matches = str(topic["name"]).startswith(options.prefix)
    logset_matches = str(logset["name"]).startswith(options.prefix)
    if not (topic_matches or logset_matches):
        return False
    return _passes_age_filter(topic, item, options, now, skipped)


def _passes_age_filter(
    resource: dict[str, Any],
    item: dict[str, Any],
    options: AlarmCleanupOptions,
    now: Callable[[], float],
    skipped: list[dict[str, Any]],
) -> bool:
    if options.older_than_seconds is None:
        return True
    created_at = _created_at(item)
    if created_at is None:
        skipped.append({**resource, "reason": "missing_create_time"})
        return False
    if now() - created_at < options.older_than_seconds:
        skipped.append({**resource, "reason": "too_fresh"})
        return False
    return True


def _created_at(item: dict[str, Any]) -> float | None:
    for key in ("CreateTime", "CreatedTime", "CreateTimestamp", "CreateTimeStamp"):
        value = item.get(key)
        if isinstance(value, int | float):
            return float(value / 1000 if value > 10_000_000_000 else value)
        if isinstance(value, str) and value.isdigit():
            parsed = int(value)
            return float(parsed / 1000 if parsed > 10_000_000_000 else parsed)
    return None


def _delete_resources(
    client: Any, region: str, resources: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for resource in resources:
        action, id_field = _DELETE_SPECS[str(resource["type"])]
        try:
            response = client.invoke(action, {id_field: resource["id"]}, region)
        except Exception as exc:  # noqa: BLE001 - cleanup is best-effort.
            results.append({**resource, "status": "failed", "error": str(exc)})
        else:
            results.append(
                {
                    **resource,
                    "status": "deleted",
                    "request_id": response.get("Response", {}).get("RequestId"),
                }
            )
    return results


def _first_text(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = item.get(key)
        if value is not None:
            return str(value)
    return ""
