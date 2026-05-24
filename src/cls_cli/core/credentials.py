from __future__ import annotations

import os
from dataclasses import dataclass

from cls_cli.core.config import Profile
from cls_cli.core.errors import AuthenticationError


@dataclass(frozen=True)
class CredentialPair:
    secret_id: str
    secret_key: str


def resolve_credentials(profile: Profile | None) -> CredentialPair:
    secret_id_names = ["TENCENTCLOUD_SECRET_ID", "CLS_SECRET_ID"]
    secret_key_names = ["TENCENTCLOUD_SECRET_KEY", "CLS_SECRET_KEY"]
    if profile and profile.secret_id_env:
        secret_id_names.insert(0, profile.secret_id_env)
    if profile and profile.secret_key_env:
        secret_key_names.insert(0, profile.secret_key_env)

    secret_id = _first_env(secret_id_names)
    secret_key = _first_env(secret_key_names)
    if not secret_id or not secret_key:
        raise AuthenticationError(
            "missing credentials; set TENCENTCLOUD_SECRET_ID/TENCENTCLOUD_SECRET_KEY "
            "or configure profile env variable names"
        )
    return CredentialPair(secret_id=secret_id, secret_key=secret_key)


def _first_env(names: list[str]) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None
