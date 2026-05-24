from __future__ import annotations

import os
import tomllib
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomli_w

from cls_cli.core.errors import ConfigError


@dataclass(frozen=True)
class Profile:
    name: str
    region: str | None = None
    output: str | None = None
    secret_id_env: str | None = None
    secret_key_env: str | None = None

    def public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "region": self.region,
            "output": self.output,
            "secret_id_env": self.secret_id_env,
            "secret_key_env": self.secret_key_env,
        }


class ConfigStore:
    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or default_config_dir()
        self.path = self.config_dir / "config.toml"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"profiles": {}}
        try:
            return tomllib.loads(self.path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"invalid config file: {self.path}") from exc

    def save(self, data: dict[str, Any]) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(tomli_w.dumps(data), encoding="utf-8")
        with suppress(OSError):
            self.path.chmod(0o600)

    def list_profiles(self) -> list[Profile]:
        data = self.load()
        profiles = data.get("profiles", {})
        if not isinstance(profiles, dict):
            raise ConfigError("profiles must be a table")
        return [self._profile(name, value) for name, value in profiles.items()]

    def get_profile(self, name: str | None) -> Profile | None:
        if name is None:
            return None
        data = self.load()
        profiles = data.get("profiles", {})
        if not isinstance(profiles, dict) or name not in profiles:
            raise ConfigError(f"profile not found: {name}")
        value = profiles[name]
        if not isinstance(value, dict):
            raise ConfigError(f"profile must be a table: {name}")
        return self._profile(name, value)

    def set_profile(self, profile: Profile) -> None:
        data = self.load()
        profiles = data.setdefault("profiles", {})
        if not isinstance(profiles, dict):
            raise ConfigError("profiles must be a table")
        profiles[profile.name] = {
            key: value
            for key, value in profile.public_dict().items()
            if key != "name" and value is not None
        }
        self.save(data)

    def delete_profile(self, name: str) -> None:
        data = self.load()
        profiles = data.get("profiles", {})
        if isinstance(profiles, dict):
            profiles.pop(name, None)
        self.save(data)

    def _profile(self, name: str, value: Any) -> Profile:
        if not isinstance(value, dict):
            raise ConfigError(f"profile must be a table: {name}")
        return Profile(
            name=name,
            region=_str_or_none(value.get("region")),
            output=_str_or_none(value.get("output")),
            secret_id_env=_str_or_none(value.get("secret_id_env")),
            secret_key_env=_str_or_none(value.get("secret_key_env")),
        )


def default_config_dir() -> Path:
    configured = os.environ.get("CLS_CLI_CONFIG_DIR")
    if configured:
        return Path(configured)
    return Path.home() / ".cls-cli"


def store_from_obj(obj: dict[str, Any] | None) -> ConfigStore:
    if obj and isinstance(obj.get("config_dir"), Path):
        return ConfigStore(obj["config_dir"])
    return ConfigStore()


def _str_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None
