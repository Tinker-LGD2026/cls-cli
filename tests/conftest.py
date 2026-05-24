from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner


@dataclass
class FakeClsClient:
    responses: dict[str, dict[str, Any]] = field(default_factory=dict)
    calls: list[tuple[str, dict[str, Any], str]] = field(default_factory=list)
    error: Exception | None = None

    def invoke(self, action: str, payload: dict[str, Any], region: str) -> dict[str, Any]:
        self.calls.append((action, payload, region))
        if self.error is not None:
            raise self.error
        return self.responses.get(
            action,
            {
                "Response": {
                    "RequestId": "req-123",
                    "Action": action,
                    "Payload": payload,
                    "Region": region,
                }
            },
        )


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def fake_client() -> FakeClsClient:
    return FakeClsClient()


@pytest.fixture
def cli_obj(tmp_path: Path, fake_client: FakeClsClient) -> dict[str, Any]:
    return {"client": fake_client, "config_dir": tmp_path / "config"}


def json_output(result: Any) -> dict[str, Any]:
    return json.loads(result.stdout)
