from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RiskLevel = Literal["read", "write", "destructive"]
OutputMode = Literal["json", "jsonl", "table"]


@dataclass(frozen=True)
class ActionSpec:
    group: str
    command: str
    action: str
    docs_url: str
    qps: int | None
    risk: RiskLevel = "read"
    supports_payload_file: bool = True
    output_mode: OutputMode = "json"

    @property
    def destructive(self) -> bool:
        return self.risk == "destructive"
