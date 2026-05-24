from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Self
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import urlopen


class WebhookCaptureServer:
    def __init__(
        self,
        host: str,
        port: int,
        received_file: Path,
        *,
        expected_run_id: str | None = None,
        scenario_ids: set[str] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.received_file = received_file
        self.expected_run_id = expected_run_id
        self.scenario_ids = scenario_ids
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def local_url(self) -> str:
        server = self._server
        port = server.server_address[1] if server else self.port
        return f"http://{self.host}:{port}/cls-alarm-webhook"

    def __enter__(self) -> Self:
        self.received_file.parent.mkdir(parents=True, exist_ok=True)
        capture = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
                length = int(self.headers.get("Content-Length") or "0")
                raw_bytes = self.rfile.read(min(length, 1024 * 1024))
                raw_body = raw_bytes.decode("utf-8", errors="replace")
                parsed_json: Any = None
                try:
                    parsed_json = json.loads(raw_body) if raw_body else None
                except json.JSONDecodeError:
                    parsed_json = None
                validation_payload = parsed_json if isinstance(parsed_json, dict) else {}
                case_file = _case_result_path(capture.received_file.parent, validation_payload)
                record = {
                    "received_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
                    "path": self.path,
                    "headers": _redact_headers(dict(self.headers.items())),
                    "raw_body": raw_body,
                    "parsed_json": parsed_json,
                    "validation": validate_received_payload(
                        validation_payload,
                        capture.expected_run_id,
                        capture.scenario_ids,
                    ),
                    "case_file": str(case_file),
                }
                with capture._lock, capture.received_file.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                    case_file.parent.mkdir(parents=True, exist_ok=True)
                    case_file.write_text(
                        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
                        encoding="utf-8",
                    )
                self.send_response(204)
                self.end_headers()

            def log_message(self, format: str, *_args: Any) -> None:
                _ = format
                return

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)


def validate_received_payload(
    payload: dict[str, Any],
    expected_run_id: str | None = None,
    scenario_ids: set[str] | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    run_id = payload.get("run_id")
    scenario_id = payload.get("scenario_id")
    if not run_id or (expected_run_id is not None and run_id != expected_run_id):
        issues.append("run_id")
    if not scenario_id or (scenario_ids is not None and str(scenario_id) not in scenario_ids):
        issues.append("scenario_id")
    marker_text = json.dumps(payload, ensure_ascii=False)
    if "{{" in marker_text or "}}" in marker_text:
        issues.append("unrendered_template_marker")
    return {"passed": not issues, "issues": issues}


def read_received_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            records.append(loaded)
    return records


def load_external_receiver_records(result_url: str, run_id: str) -> list[dict[str, Any]]:
    with urlopen(external_receiver_records_url(result_url, run_id), timeout=10) as response:
        loaded = json.loads(response.read().decode("utf-8"))
    if isinstance(loaded, list):
        return [item for item in loaded if isinstance(item, dict)]
    if isinstance(loaded, dict):
        records = loaded.get("records")
        if records is None and isinstance(loaded.get("data"), dict):
            records = loaded["data"].get("records")
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
    return []


def external_receiver_records_url(result_url: str, run_id: str) -> str:
    parsed = urlsplit(result_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("run_id", run_id)
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
    )


def has_received_scenario(records: list[dict[str, Any]], run_id: str, scenario_id: str) -> bool:
    for record in records:
        parsed = record.get("parsed_json")
        if not isinstance(parsed, dict):
            continue
        if parsed.get("run_id") != run_id or parsed.get("scenario_id") != scenario_id:
            continue
        if parsed.get("case_type") != "trigger":
            continue
        validation = record.get("validation")
        if isinstance(validation, dict) and validation.get("passed") is False:
            continue
        return True
    return False


def _case_result_path(run_dir: Path, payload: dict[str, Any]) -> Path:
    raw_scenario_id = str(payload.get("scenario_id") or "unknown")
    scenario_id = _safe_filename(raw_scenario_id)
    return run_dir / "case-results" / f"{scenario_id}-{time.time_ns()}.json"


def _safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)


def _redact_headers(headers: dict[str, str]) -> dict[str, str]:
    return {key: ("<redacted>" if _sensitive_key(key) else value) for key, value in headers.items()}


def _sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("_", "-")
    return any(token in normalized for token in ("authorization", "token", "key", "secret"))
