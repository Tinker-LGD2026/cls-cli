from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CliError(Exception):
    code: str
    message: str
    exit_code: int = 1
    request_id: str | None = None
    action: str | None = None
    region: str | None = None
    retryable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "request_id": self.request_id,
            "action": self.action,
            "region": self.region,
            "retryable": self.retryable,
        }


class InputError(CliError):
    def __init__(self, message: str) -> None:
        super().__init__("INPUT_ERROR", message, 1)


class ConfigError(CliError):
    def __init__(self, message: str) -> None:
        super().__init__("CONFIG_ERROR", message, 5)


class AuthenticationError(CliError):
    def __init__(self, message: str) -> None:
        super().__init__("AUTHENTICATION_ERROR", message, 2)


class ConfirmationRequired(CliError):
    def __init__(self, message: str) -> None:
        super().__init__("CONFIRMATION_REQUIRED", message, 1)


class ClsApiError(CliError):
    def __init__(
        self,
        code: str,
        message: str,
        request_id: str | None,
        action: str,
        region: str,
        retryable: bool,
    ) -> None:
        exit_code = 4 if retryable else 3
        if code.startswith("AuthFailure") or code.startswith("Unauthorized"):
            exit_code = 2
        super().__init__(code, message, exit_code, request_id, action, region, retryable)
