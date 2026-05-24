from __future__ import annotations

import sys
import types
from typing import Any

from cls_cli.core.client import ClsClient


def test_common_sdk_namespace_version_shim(monkeypatch):
    module = types.ModuleType("tencentcloud")
    monkeypatch.setitem(sys.modules, "tencentcloud", module)

    ClsClient()._ensure_tencentcloud_version()

    assert module.__version__ == "UNKNOWN"


class _Repeated(list[Any]):
    def __init__(self, factory: type[Any]) -> None:
        super().__init__()
        self._factory = factory

    def add(self) -> Any:
        item = self._factory()
        self.append(item)
        return item


class _Content:
    key = ""
    value = ""


class _Log:
    def __init__(self) -> None:
        self.time = 0
        self.contents = _Repeated(_Content)


class _LogTag:
    key = ""
    value = ""


class _LogGroup:
    def __init__(self) -> None:
        self.logs = _Repeated(_Log)
        self.logTags = _Repeated(_LogTag)
        self.filename = ""
        self.source = ""


class _LogGroupList:
    def __init__(self) -> None:
        self.logGroupList = _Repeated(_LogGroup)


class _Response:
    def get_request_id(self) -> str:
        return "upload-req-123"


def test_upload_log_uses_cls_binary_sdk(monkeypatch):
    captured: dict[str, Any] = {}

    class FakeLogClient:
        def __init__(self, endpoint: str, secret_id: str, secret_key: str) -> None:
            captured["endpoint"] = endpoint
            captured["secret_id"] = secret_id
            captured["secret_key"] = secret_key

        def put_log_raw(self, topic_id: str, log_group_list: _LogGroupList) -> _Response:
            captured["topic_id"] = topic_id
            captured["log_group_list"] = log_group_list
            return _Response()

    monkeypatch.setenv("TENCENTCLOUD_SECRET_ID", "sid")
    monkeypatch.setenv("TENCENTCLOUD_SECRET_KEY", "skey")
    monkeypatch.setattr("cls_cli.core.client.time.time", lambda: 1710000000.123)
    monkeypatch.setitem(sys.modules, "tencentcloud.log", types.ModuleType("tencentcloud.log"))
    logclient = types.ModuleType("tencentcloud.log.logclient")
    logclient.LogClient = FakeLogClient
    monkeypatch.setitem(sys.modules, "tencentcloud.log.logclient", logclient)
    cls_pb2 = types.ModuleType("tencentcloud.log.cls_pb2")
    cls_pb2.LogGroupList = _LogGroupList
    monkeypatch.setitem(sys.modules, "tencentcloud.log.cls_pb2", cls_pb2)
    logexception = types.ModuleType("tencentcloud.log.logexception")
    logexception.LogException = Exception
    monkeypatch.setitem(sys.modules, "tencentcloud.log.logexception", logexception)

    result = ClsClient().invoke(
        "UploadLog",
        {"TopicId": "topic-123", "Logs": [{"level": "info", "message": "ok"}]},
        "ap-shanghai",
    )

    assert result == {"Response": {"RequestId": "upload-req-123"}}
    assert captured["endpoint"] == "https://ap-shanghai.cls.tencentcs.com"
    assert captured["secret_id"] == "sid"
    assert captured["secret_key"] == "skey"
    assert captured["topic_id"] == "topic-123"
    group = captured["log_group_list"].logGroupList[0]
    assert group.source == "cls-cli"
    assert len(group.logs) == 1
    assert group.logs[0].time == 1710000000123
    contents = {item.key: item.value for item in group.logs[0].contents}
    assert contents == {"level": "info", "message": "ok"}
