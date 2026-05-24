from __future__ import annotations

import time
from typing import Any

from cls_cli.core.config import Profile
from cls_cli.core.credentials import resolve_credentials
from cls_cli.core.errors import ClsApiError


class ClsClient:
    def __init__(self, profile: Profile | None = None) -> None:
        self.profile = profile

    def invoke(self, action: str, payload: dict[str, Any], region: str) -> dict[str, Any]:
        credentials = resolve_credentials(self.profile)
        if action == "UploadLog":
            return self._upload_log(payload, region, credentials.secret_id, credentials.secret_key)
        self._ensure_tencentcloud_version()
        try:
            from tencentcloud.common.common_client import CommonClient
            from tencentcloud.common.credential import Credential
            from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
                TencentCloudSDKException,
            )
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
        except ImportError as exc:
            raise ClsApiError(
                "SDK_IMPORT_ERROR",
                "tencentcloud-sdk-python is required",
                None,
                action,
                region,
                False,
            ) from exc

        http_profile = HttpProfile()
        http_profile.endpoint = "cls.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        credential = Credential(credentials.secret_id, credentials.secret_key)
        client = CommonClient("cls", "2020-10-16", credential, region, profile=client_profile)
        try:
            result = client.call_json(action, payload)
        except TencentCloudSDKException as exc:
            request_id = getattr(exc, "requestId", None) or getattr(exc, "request_id", None)
            code = getattr(exc, "code", "TencentCloudSDKException")
            message = getattr(exc, "message", str(exc))
            retryable = code in {"RequestLimitExceeded", "InternalError"}
            raise ClsApiError(code, message, request_id, action, region, retryable) from exc
        if not isinstance(result, dict):
            return {"Response": result}
        return result

    def _ensure_tencentcloud_version(self) -> None:
        import tencentcloud

        if not hasattr(tencentcloud, "__version__"):
            tencentcloud.__version__ = "UNKNOWN"

    def _upload_log(
        self, payload: dict[str, Any], region: str, secret_id: str, secret_key: str
    ) -> dict[str, Any]:
        try:
            from tencentcloud.log.cls_pb2 import LogGroupList
            from tencentcloud.log.logclient import LogClient
            from tencentcloud.log.logexception import LogException
        except ImportError as exc:
            raise ClsApiError(
                "SDK_IMPORT_ERROR",
                "tencentcloud-cls-sdk-python is required for UploadLog",
                None,
                "UploadLog",
                region,
                False,
            ) from exc

        topic_id = str(payload.get("TopicId") or "")
        logs = payload.get("Logs")
        if not topic_id or not isinstance(logs, list):
            raise ClsApiError(
                "INVALID_UPLOAD_PAYLOAD",
                "UploadLog requires TopicId and Logs list",
                None,
                "UploadLog",
                region,
                False,
            )

        log_group_list = LogGroupList()
        log_group = log_group_list.logGroupList.add()
        log_group.source = "cls-cli"
        log_group.filename = "cls-cli-jsonl"
        now = int(time.time() * 1000)
        for row in logs:
            if not isinstance(row, dict):
                raise ClsApiError(
                    "INVALID_UPLOAD_PAYLOAD",
                    "each log row must be an object",
                    None,
                    "UploadLog",
                    region,
                    False,
                )
            log = log_group.logs.add()
            raw_time = row.get("time") or row.get("timestamp")
            log.time = int(raw_time) if isinstance(raw_time, int | float | str) else now
            for key, value in row.items():
                content = log.contents.add()
                content.key = str(key)
                content.value = str(value)

        endpoint = f"https://{region}.cls.tencentcs.com"
        client = LogClient(endpoint, secret_id, secret_key)
        try:
            response = client.put_log_raw(topic_id, log_group_list)
        except LogException as exc:
            request_id = exc.get_request_id()
            code = exc.get_error_code()
            message = exc.get_error_message()
            retryable = code in {"RequestLimitExceeded", "InternalError"}
            raise ClsApiError(code, message, request_id, "UploadLog", region, retryable) from exc
        return {"Response": {"RequestId": response.get_request_id()}}
