#!/usr/bin/env python3
# Compatible with Python 3.6+.

import argparse
import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

SENSITIVE_HEADER_TOKENS = ("authorization", "token", "key", "secret", "signature")
MAX_BODY_BYTES = 1024 * 1024


def _is_sensitive_header(name):
    normalized = name.lower().replace("_", "-")
    return any(token in normalized for token in SENSITIVE_HEADER_TOKENS)


def _redact_headers(headers):
    return {
        name: ("<redacted>" if _is_sensitive_header(name) else value)
        for name, value in headers.items()
    }


def _safe_filename(value):
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)
    return safe or "unknown"


def _parse_json(raw_body):
    if not raw_body:
        return None
    try:
        return json.loads(raw_body)
    except ValueError:
        return None


def _validate_payload(payload):
    issues = []
    if not isinstance(payload, dict):
        return {"passed": False, "issues": ["body_not_json_object"]}
    if not payload.get("run_id"):
        issues.append("missing_run_id")
    if not payload.get("scenario_id"):
        issues.append("missing_scenario_id")
    marker_text = json.dumps(payload, ensure_ascii=False)
    if "{{" in marker_text or "}}" in marker_text:
        issues.append("unrendered_template_marker")
    return {"passed": not issues, "issues": issues}


def _make_record(handler, raw_body):
    parsed_json = _parse_json(raw_body)
    return {
        "received_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "client": handler.client_address[0] if handler.client_address else "",
        "method": handler.command,
        "path": handler.path,
        "headers": _redact_headers(dict(handler.headers.items())),
        "raw_body": raw_body,
        "parsed_json": parsed_json,
        "validation": _validate_payload(parsed_json),
    }


def _case_file(output_dir, record):
    payload = record.get("parsed_json")
    scenario_id = "unknown"
    if isinstance(payload, dict):
        scenario_id = str(payload.get("scenario_id") or "unknown")
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    filename = f"{_safe_filename(scenario_id)}-{stamp}-{int(time.time() * 1000000)}.json"
    return os.path.join(output_dir, "case-results", filename)


def _write_text(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _append_text(path, text):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(text)


def _load_records(output_dir):
    summary_file = os.path.join(output_dir, "received.jsonl")
    if not os.path.exists(summary_file):
        return []
    records = []
    with open(summary_file, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict):
                records.append(record)
    return records


def _record_matches(record, params):
    payload = record.get("parsed_json")
    if not isinstance(payload, dict):
        return False
    run_id = params.get("run_id", [""])[0]
    scenario_id = params.get("scenario_id", [""])[0]
    case_type = params.get("case_type", [""])[0]
    if run_id and payload.get("run_id") != run_id:
        return False
    if scenario_id and payload.get("scenario_id") != scenario_id:
        return False
    return not (case_type and payload.get("case_type") != case_type)


def _filter_records(output_dir, params):
    return [record for record in _load_records(output_dir) if _record_matches(record, params)]


def _summary(records, run_id):
    by_scenario = {}
    validation_failed = 0
    for record in records:
        payload = record.get("parsed_json")
        if isinstance(payload, dict):
            scenario_id = str(payload.get("scenario_id") or "unknown")
            by_scenario[scenario_id] = by_scenario.get(scenario_id, 0) + 1
        validation = record.get("validation")
        if isinstance(validation, dict) and not validation.get("passed", False):
            validation_failed += 1
    return {
        "run_id": run_id or None,
        "total": len(records),
        "validation_failed": validation_failed,
        "by_scenario": by_scenario,
    }


def _send_json(handler, payload, status=200):
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class ThreadingSimpleHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class WebhookHandler(BaseHTTPRequestHandler):
    output_dir = "webhook-output"

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if parsed.path in ("/", "/health", "/healthz"):
            body = b"ok\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path in ("/records", "/case-results"):
            records = _filter_records(self.output_dir, params)
            _send_json(self, {"count": len(records), "records": records})
            return
        if parsed.path == "/summary":
            records = _filter_records(self.output_dir, params)
            _send_json(self, _summary(records, params.get("run_id", [""])[0]))
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(min(length, MAX_BODY_BYTES)).decode("utf-8", errors="replace")
        record = _make_record(self, raw)
        os.makedirs(self.output_dir, exist_ok=True)
        summary_file = os.path.join(self.output_dir, "received.jsonl")
        case_file = _case_file(self.output_dir, record)
        os.makedirs(os.path.dirname(case_file), exist_ok=True)
        record["case_file"] = case_file
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        _append_text(summary_file, line + "\n")
        _write_text(case_file, json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True))
        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):
        print(f"{self.client_address[0]} - - [{self.log_date_time_string()}] {format % args}")


def main():
    parser = argparse.ArgumentParser(description="Simple CLS alarm webhook receiver")
    parser.add_argument("--host", default="0.0.0.0", help="listen host, default: 0.0.0.0")
    parser.add_argument("--port", type=int, default=8765, help="listen port, default: 8765")
    parser.add_argument(
        "--output-dir", default="webhook-output", help="directory for received files"
    )
    args = parser.parse_args()

    WebhookHandler.output_dir = args.output_dir
    server = ThreadingSimpleHTTPServer((args.host, args.port), WebhookHandler)
    print(f"listening on http://{args.host}:{args.port}/cls-alarm-webhook")
    print(f"writing summary to {os.path.join(args.output_dir, 'received.jsonl')}")
    print(f"writing per-case files to {os.path.join(args.output_dir, 'case-results')}")
    print("query records at /records?run_id=<run_id>")
    print("query summary at /summary?run_id=<run_id>")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
