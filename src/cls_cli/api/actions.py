from __future__ import annotations

from cls_cli.api.models import ActionSpec

BASE = "https://cloud.tencent.com/document/api/614"

ACTION_SPECS: dict[str, ActionSpec] = {
    "logset.list": ActionSpec("logset", "list", "DescribeLogsets", f"{BASE}/58624", 100),
    "logset.get": ActionSpec("logset", "get", "DescribeLogsets", f"{BASE}/58624", 100),
    "logset.create": ActionSpec("logset", "create", "CreateLogset", f"{BASE}/58626", 20, "write"),
    "logset.update": ActionSpec("logset", "update", "ModifyLogset", f"{BASE}/58623", 20, "write"),
    "logset.delete": ActionSpec(
        "logset", "delete", "DeleteLogset", f"{BASE}/58625", 20, "destructive"
    ),
    "topic.list": ActionSpec("topic", "list", "DescribeTopics", f"{BASE}/56454", 50),
    "topic.get": ActionSpec("topic", "get", "DescribeTopics", f"{BASE}/56454", 50),
    "topic.create": ActionSpec("topic", "create", "CreateTopic", f"{BASE}/56456", 100, "write"),
    "topic.update": ActionSpec("topic", "update", "ModifyTopic", f"{BASE}/56453", 20, "write"),
    "topic.delete": ActionSpec(
        "topic", "delete", "DeleteTopic", f"{BASE}/56455", 20, "destructive"
    ),
    "machine_group.list": ActionSpec(
        "machine-group", "list", "DescribeMachineGroups", f"{BASE}/56438", 20
    ),
    "machine_group.get": ActionSpec(
        "machine-group", "get", "DescribeMachineGroups", f"{BASE}/56438", 20
    ),
    "machine_group.create": ActionSpec(
        "machine-group", "create", "CreateMachineGroup", f"{BASE}/56440", 20, "write"
    ),
    "machine_group.update": ActionSpec(
        "machine-group", "update", "ModifyMachineGroup", f"{BASE}/56436", 20, "write"
    ),
    "machine_group.delete": ActionSpec(
        "machine-group", "delete", "DeleteMachineGroup", f"{BASE}/56439", 20, "destructive"
    ),
    "machine_group.machines": ActionSpec(
        "machine-group", "machines", "DescribeMachines", f"{BASE}/56437", 20
    ),
    "machine_group.add_info": ActionSpec(
        "machine-group", "add-info", "AddMachineGroupInfo", f"{BASE}/82425", 20, "write"
    ),
    "machine_group.delete_info": ActionSpec(
        "machine-group", "delete-info", "DeleteMachineGroupInfo", f"{BASE}/82424", 20, "destructive"
    ),
    "config.list": ActionSpec("config", "list", "DescribeConfigs", f"{BASE}/58616", 20),
    "config.get": ActionSpec("config", "get", "DescribeConfigs", f"{BASE}/58616", 20),
    "config.create": ActionSpec("config", "create", "CreateConfig", f"{BASE}/58620", 30, "write"),
    "config.update": ActionSpec("config", "update", "ModifyConfig", f"{BASE}/58614", 20, "write"),
    "config.delete": ActionSpec(
        "config", "delete", "DeleteConfig", f"{BASE}/58619", 20, "destructive"
    ),
    "config.apply": ActionSpec(
        "config", "apply", "ApplyConfigToMachineGroup", f"{BASE}/58621", 20, "write"
    ),
    "config.remove": ActionSpec(
        "config", "remove", "DeleteConfigFromMachineGroup", f"{BASE}/58618", 20, "destructive"
    ),
    "config.bound_groups": ActionSpec(
        "config", "bound-groups", "DescribeConfigMachineGroups", f"{BASE}/58617", 1000
    ),
    "config.bound_configs": ActionSpec(
        "config", "bound-configs", "DescribeMachineGroupConfigs", f"{BASE}/58615", 20
    ),
    "index.get": ActionSpec("index", "get", "DescribeIndex", f"{BASE}/56443", 20),
    "index.create": ActionSpec("index", "create", "CreateIndex", f"{BASE}/56445", 20, "write"),
    "index.update": ActionSpec("index", "update", "ModifyIndex", f"{BASE}/56442", 20, "write"),
    "index.delete": ActionSpec(
        "index", "delete", "DeleteIndex", f"{BASE}/56444", 20, "destructive"
    ),
    "index.rebuild_estimate": ActionSpec(
        "index", "rebuild-estimate", "EstimateRebuildIndexTask", f"{BASE}/127534", 20
    ),
    "index.rebuild_create": ActionSpec(
        "index", "rebuild-create", "CreateRebuildIndexTask", f"{BASE}/127536", 20, "write"
    ),
    "index.rebuild_list": ActionSpec(
        "index", "rebuild-list", "DescribeRebuildIndexTasks", f"{BASE}/127535", 20
    ),
    "index.rebuild_cancel": ActionSpec(
        "index", "rebuild-cancel", "CancelRebuildIndexTask", f"{BASE}/127537", 20, "destructive"
    ),
    "log.search": ActionSpec("log", "search", "SearchLog", f"{BASE}/56447", 10000),
    "log.histogram": ActionSpec("log", "histogram", "DescribeLogHistogram", f"{BASE}/71726", 10000),
    "log.context": ActionSpec("log", "context", "DescribeLogContext", f"{BASE}/56448", 20),
    "log.upload": ActionSpec("log", "upload", "UploadLog", f"{BASE}/59470", 100000, "write"),
    "log.export_create": ActionSpec(
        "log", "export-create", "CreateExport", f"{BASE}/56451", 20, "write"
    ),
    "log.export_list": ActionSpec("log", "export-list", "DescribeExports", f"{BASE}/56449", 20),
    "log.export_delete": ActionSpec(
        "log", "export-delete", "DeleteExport", f"{BASE}/56450", 20, "destructive"
    ),
    "alarm.policy.list": ActionSpec("alarm", "policy list", "DescribeAlarms", f"{BASE}/56461", 30),
    "alarm.policy.create": ActionSpec(
        "alarm", "policy create", "CreateAlarm", f"{BASE}/56466", 20, "write"
    ),
    "alarm.policy.update": ActionSpec(
        "alarm", "policy update", "ModifyAlarm", f"{BASE}/56459", 20, "write"
    ),
    "alarm.policy.delete": ActionSpec(
        "alarm", "policy delete", "DeleteAlarm", f"{BASE}/56464", 20, "destructive"
    ),
    "alarm.notice.list": ActionSpec(
        "alarm", "notice list", "DescribeAlarmNotices", f"{BASE}/56462", 20
    ),
    "alarm.notice.create": ActionSpec(
        "alarm", "notice create", "CreateAlarmNotice", f"{BASE}/56465", 20, "write"
    ),
    "alarm.notice.update": ActionSpec(
        "alarm", "notice update", "ModifyAlarmNotice", f"{BASE}/56458", 20, "write"
    ),
    "alarm.notice.delete": ActionSpec(
        "alarm", "notice delete", "DeleteAlarmNotice", f"{BASE}/56463", 20, "destructive"
    ),
    "alarm.shield.list": ActionSpec(
        "alarm", "shield list", "DescribeAlarmShields", f"{BASE}/103650", 20
    ),
    "alarm.shield.create": ActionSpec(
        "alarm", "shield create", "CreateAlarmShield", f"{BASE}/103652", 20, "write"
    ),
    "alarm.shield.update": ActionSpec(
        "alarm", "shield update", "ModifyAlarmShield", f"{BASE}/103649", 20, "write"
    ),
    "alarm.shield.delete": ActionSpec(
        "alarm", "shield delete", "DeleteAlarmShield", f"{BASE}/103651", 20, "destructive"
    ),
    "alarm.content.list": ActionSpec(
        "alarm", "content list", "DescribeNoticeContents", f"{BASE}/111714", 20
    ),
    "alarm.content.create": ActionSpec(
        "alarm", "content create", "CreateNoticeContent", f"{BASE}/111716", 20, "write"
    ),
    "alarm.content.update": ActionSpec(
        "alarm", "content update", "ModifyNoticeContent", f"{BASE}/111713", 20, "write"
    ),
    "alarm.content.delete": ActionSpec(
        "alarm", "content delete", "DeleteNoticeContent", f"{BASE}/111715", 20, "destructive"
    ),
    "alarm.callback.list": ActionSpec(
        "alarm", "callback list", "DescribeWebCallbacks", f"{BASE}/115229", 20
    ),
    "alarm.callback.create": ActionSpec(
        "alarm", "callback create", "CreateWebCallback", f"{BASE}/115231", 20, "write"
    ),
    "alarm.callback.update": ActionSpec(
        "alarm", "callback update", "ModifyWebCallback", f"{BASE}/115228", 20, "write"
    ),
    "alarm.callback.delete": ActionSpec(
        "alarm", "callback delete", "DeleteWebCallback", f"{BASE}/115230", 20, "destructive"
    ),
    "alarm.integration.list": ActionSpec(
        "alarm", "integration list", "DescribeWebCallbacks", f"{BASE}/115229", 20
    ),
    "alarm.integration.create": ActionSpec(
        "alarm", "integration create", "CreateWebCallback", f"{BASE}/115231", 20, "write"
    ),
    "alarm.integration.update": ActionSpec(
        "alarm", "integration update", "ModifyWebCallback", f"{BASE}/115228", 20, "write"
    ),
    "alarm.integration.delete": ActionSpec(
        "alarm", "integration delete", "DeleteWebCallback", f"{BASE}/115230", 20, "destructive"
    ),
    "alarm.history": ActionSpec(
        "alarm", "history", "DescribeAlertRecordHistory", f"{BASE}/90291", 40
    ),
    "alarm.log": ActionSpec("alarm", "log", "GetAlarmLog", f"{BASE}/56460", 30),
}


def get_spec(key: str) -> ActionSpec:
    return ACTION_SPECS[key]
