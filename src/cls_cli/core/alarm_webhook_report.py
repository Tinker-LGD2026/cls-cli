from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def finalize_webhook_matrix_result(
    run_id: str,
    region: str,
    status: str,
    resources: list[dict[str, str]],
    assertions: list[dict[str, Any]],
    findings: list[dict[str, str]],
    cleanup_results: list[dict[str, str]],
    scenario_results: list[dict[str, Any]],
    received_file: Path,
    run_dir: Path,
) -> dict[str, Any]:
    result = {
        "run_id": run_id,
        "status": status,
        "region": region,
        "created_resources": resources,
        "assertions": assertions,
        "findings": findings,
        "scenario_results": scenario_results,
        "received_file": str(received_file),
        "case_results_dir": str(run_dir / "case-results"),
        "cleanup": cleanup_results,
    }
    _write_json(run_dir / "scenario-results.json", scenario_results)
    _write_json(run_dir / "cleanup.json", cleanup_results)
    report_path = run_dir / "report.md"
    report_path.write_text(markdown_webhook_matrix_report(result), encoding="utf-8")
    result["report_path"] = str(report_path)
    return result


def markdown_webhook_matrix_report(result: dict[str, Any]) -> str:
    lines = [
        "# CLS Alarm Webhook Function Matrix Report",
        "",
        f"- run_id: `{result['run_id']}`",
        f"- region: `{result['region']}`",
        f"- status: `{result['status']}`",
        f"- received_file: `{result['received_file']}`",
        "",
        "## Scenarios",
    ]
    for item in result.get("scenario_results", []):
        summary = (
            "- `{id}`: query={query_matched}, send={send_success}, "
            "webhook={webhook_received}"
        )
        lines.append(
            summary.format(
                id=item.get("id"),
                query_matched=item.get("query_matched"),
                send_success=item.get("send_success"),
                webhook_received=item.get("webhook_received"),
            )
        )
    lines.extend(["", "## Findings"])
    findings = result.get("findings") or []
    if findings:
        for item in findings:
            lines.append(f"- `{item.get('phase')}`: {item.get('message')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Cleanup"])
    cleanup = result.get("cleanup") or []
    if cleanup:
        for item in cleanup:
            lines.append(f"- `{item.get('type')}` `{item.get('id')}`: {item.get('status')}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(content, encoding="utf-8")
