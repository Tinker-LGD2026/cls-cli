# CLS API Matrix

本表记录当前 CLI 覆盖的 CLS 官方 API。

> 官方 API 概览：https://cloud.tencent.com/document/product/614/56480

| CLI | CLS Action | 官方文档 | QPS | 风险 |
|---|---|---|---:|---|
| `cls logset list/get` | `DescribeLogsets` | https://cloud.tencent.com/document/api/614/58624 | 100 | read |
| `cls logset create` | `CreateLogset` | https://cloud.tencent.com/document/api/614/58626 | 20 | write |
| `cls logset update` | `ModifyLogset` | https://cloud.tencent.com/document/api/614/58623 | 20 | write |
| `cls logset delete` | `DeleteLogset` | https://cloud.tencent.com/document/api/614/58625 | 20 | destructive |
| `cls topic list/get` | `DescribeTopics` | https://cloud.tencent.com/document/api/614/56454 | 50 | read |
| `cls topic create` | `CreateTopic` | https://cloud.tencent.com/document/api/614/56456 | 100 | write |
| `cls topic update` | `ModifyTopic` | https://cloud.tencent.com/document/api/614/56453 | 20 | write |
| `cls topic delete` | `DeleteTopic` | https://cloud.tencent.com/document/api/614/56455 | 20 | destructive |
| `cls machine-group list/get` | `DescribeMachineGroups` | https://cloud.tencent.com/document/api/614/56438 | 20 | read |
| `cls machine-group create` | `CreateMachineGroup` | https://cloud.tencent.com/document/api/614/56440 | 20 | write |
| `cls machine-group update` | `ModifyMachineGroup` | https://cloud.tencent.com/document/api/614/56436 | 20 | write |
| `cls machine-group delete` | `DeleteMachineGroup` | https://cloud.tencent.com/document/api/614/56439 | 20 | destructive |
| `cls machine-group machines` | `DescribeMachines` | https://cloud.tencent.com/document/api/614/56437 | 20 | read |
| `cls machine-group add-info` | `AddMachineGroupInfo` | https://cloud.tencent.com/document/api/614/82425 | 20 | write |
| `cls machine-group delete-info` | `DeleteMachineGroupInfo` | https://cloud.tencent.com/document/api/614/82424 | 20 | destructive |
| `cls config list/get` | `DescribeConfigs` | https://cloud.tencent.com/document/api/614/58616 | 20 | read |
| `cls config create` | `CreateConfig` | https://cloud.tencent.com/document/api/614/58620 | 30 | write |
| `cls config update` | `ModifyConfig` | https://cloud.tencent.com/document/api/614/58614 | 20 | write |
| `cls config delete` | `DeleteConfig` | https://cloud.tencent.com/document/api/614/58619 | 20 | destructive |
| `cls config apply` | `ApplyConfigToMachineGroup` | https://cloud.tencent.com/document/api/614/58621 | 20 | write |
| `cls config remove` | `DeleteConfigFromMachineGroup` | https://cloud.tencent.com/document/api/614/58618 | 20 | destructive |
| `cls config bound-groups` | `DescribeConfigMachineGroups` | https://cloud.tencent.com/document/api/614/58617 | 1000 | read |
| `cls config bound-configs` | `DescribeMachineGroupConfigs` | https://cloud.tencent.com/document/api/614/58615 | 20 | read |
| `cls index get` | `DescribeIndex` | https://cloud.tencent.com/document/api/614/56443 | 20 | read |
| `cls index create` | `CreateIndex` | https://cloud.tencent.com/document/api/614/56445 | 20 | write |
| `cls index update` | `ModifyIndex` | https://cloud.tencent.com/document/api/614/56442 | 20 | write |
| `cls index delete` | `DeleteIndex` | https://cloud.tencent.com/document/api/614/56444 | 20 | destructive |
| `cls index rebuild-estimate` | `EstimateRebuildIndexTask` | https://cloud.tencent.com/document/api/614/127534 | 20 | read |
| `cls index rebuild-create` | `CreateRebuildIndexTask` | https://cloud.tencent.com/document/api/614/127536 | 20 | write |
| `cls index rebuild-list` | `DescribeRebuildIndexTasks` | https://cloud.tencent.com/document/api/614/127535 | 20 | read |
| `cls index rebuild-cancel` | `CancelRebuildIndexTask` | https://cloud.tencent.com/document/api/614/127537 | 20 | destructive |
| `cls log search` | `SearchLog` | https://cloud.tencent.com/document/api/614/56447 | 10000 | read |
| `cls log histogram` | `DescribeLogHistogram` | https://cloud.tencent.com/document/api/614/71726 | 10000 | read |
| `cls log context` | `DescribeLogContext` | https://cloud.tencent.com/document/api/614/56448 | 20 | read |
| `cls log upload` | `UploadLog` | https://cloud.tencent.com/document/api/614/59470 | 100000 | write，二进制上传 |
| `cls log export-create` | `CreateExport` | https://cloud.tencent.com/document/api/614/56451 | 20 | write |
| `cls log export-list` | `DescribeExports` | https://cloud.tencent.com/document/api/614/56449 | 20 | read |
| `cls log export-delete` | `DeleteExport` | https://cloud.tencent.com/document/api/614/56450 | 20 | destructive |
| `cls ai generate-query` | `ChatCompletions` (`text2sql` / `text2sql-reasoning`, non-stream); `--normalize-aliases` is local deterministic post-processing; `--dry-run` emits request payload; `--validate-query` calls `SearchLog` after AI response | https://cloud.tencent.com/document/product/614/130043 | 20 | AI read + local |
| `cls alarm policy list/get/create/update/delete` | `DescribeAlarms` / `CreateAlarm` / `ModifyAlarm` / `DeleteAlarm`; `get` uses confirmed `alarmId` filter | https://cloud.tencent.com/document/product/614/56480 | 20-30 | mixed |
| `cls alarm policy scaffold/validate` | local generator and static validator; can generate `MultiConditions`, group trigger, policy-level `CallBack`, `MonitorTime` fixed/cron, `Analysis`, and `Classifications`; advanced fields support raw passthrough plus browser/API-confirmed strict shape validation | https://cloud.tencent.com/document/api/614/56466 | - | local |
| `cls alarm validate bundle` | local cross-resource validator for policy/content/notice/integration | https://cloud.tencent.com/document/product/614/56480 | - | local |
| `cls alarm bundle plan` | local execution graph planner for topic/integration/content/notice/policy with `existing/create/update/skip` modes | local | - | local |
| `cls alarm bundle apply` | `CreateTopic` / `ModifyTopic` / `CreateWebCallback` / `ModifyWebCallback` / `CreateNoticeContent` / `ModifyNoticeContent` / `CreateAlarmNotice` / `ModifyAlarmNotice` / `CreateAlarm` / `ModifyAlarm` as required by bundle modes | https://cloud.tencent.com/document/product/614/56480 | mixed | write |
| `cls alarm bundle rollback` | `DeleteAlarm` / `DeleteAlarmNotice` / `DeleteNoticeContent` / `DeleteWebCallback` / `DeleteTopic` for manifest resources created by `apply` | https://cloud.tencent.com/document/product/614/56480 | mixed | destructive |
| `cls alarm bundle status` | local manifest inspection | local | - | local |
| `cls alarm policy test-query` | `SearchLog` preview | https://cloud.tencent.com/document/api/614/56447 | 10000 | read |
| `cls alarm template generate/validate/render` | local generator/validator/renderer | https://cloud.tencent.com/document/product/614/74718 | - | local |
| `cls alarm template send-test` | WeCom/Feishu robot webhook smoke test | https://developer.work.weixin.qq.com/document/path/91770 / https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot | - | external write |
| `cls alarm verify e2e` | `CreateLogset` / `CreateTopic` / `CreateIndex` / `UploadLog` / `SearchLog` / `DescribeLogHistogram` / `CreateNoticeContent` / `CreateWebCallback` / `CreateAlarmNotice` / `CreateAlarm` / `DescribeAlertRecordHistory` / `GetAlarmLog` plus cleanup; no direct robot webhook unless `--send-robot-smoke-test` | https://cloud.tencent.com/document/product/614/56480 | mixed | real e2e write |
| `cls alarm verify cleanup` | `DescribeAlarms` / `DescribeAlarmNotices` / `DescribeWebCallbacks` / `DescribeNoticeContents` / `DescribeLogsets` / `DescribeTopics` plus `DeleteAlarm` / `DeleteAlarmNotice` / `DeleteWebCallback` / `DeleteNoticeContent` / `DeleteIndex` / `DeleteTopic` / `DeleteLogset` when `--force` | https://cloud.tencent.com/document/product/614/56480 | mixed | destructive |
| `cls alarm integration list/create/update/delete` | `DescribeWebCallbacks` / `CreateWebCallback` / `ModifyWebCallback` / `DeleteWebCallback` | https://cloud.tencent.com/document/api/614/115229 / https://cloud.tencent.com/document/api/614/115231 | 20 | mixed |
| `cls alarm integration scaffold/validate` | local generator/validator for WebCallback payload | https://cloud.tencent.com/document/product/614/98563 | - | local |
| `cls alarm notice list/create/update/delete` | `DescribeAlarmNotices` / `CreateAlarmNotice` / `ModifyAlarmNotice` / `DeleteAlarmNotice` | https://cloud.tencent.com/document/product/614/56480 | 20 | mixed |
| `cls alarm notice scaffold/validate` | local generator/validator for `CreateAlarmNotice` payload referencing `WebCallbackId`; can generate browser/API-confirmed `NoticeRules` for notify type, level, notify time, duration, alarm name, labels, receivers, callbacks and escalation; supports raw passthrough plus strict shape validation | https://cloud.tencent.com/document/api/614/56465 | - | local |
| `cls alarm shield list/create/update/delete` | `DescribeAlarmShields` / `CreateAlarmShield` / `ModifyAlarmShield` / `DeleteAlarmShield` | https://cloud.tencent.com/document/product/614/56480 | 20 | mixed |
| `cls alarm content list/create/update/delete` | `DescribeNoticeContents` / `CreateNoticeContent` / `ModifyNoticeContent` / `DeleteNoticeContent` | https://cloud.tencent.com/document/product/614/56480 | 20 | mixed |
| `cls alarm callback list/create/update/delete` | `DescribeWebCallbacks` / `CreateWebCallback` / `ModifyWebCallback` / `DeleteWebCallback` | https://cloud.tencent.com/document/product/614/56480 | 20 | mixed |
| `cls alarm history` | `DescribeAlertRecordHistory` | https://cloud.tencent.com/document/api/614/90291 | 40 | read |
| `cls alarm log` | `GetAlarmLog` | https://cloud.tencent.com/document/api/614/56460 | 30 | read |
| `cls alarm debug explain` | `DescribeAlarms` + `DescribeAlertRecordHistory` + `GetAlarmLog` | https://cloud.tencent.com/document/product/614/56480 | mixed | read |

| Alarm write validation | local validators for `alarm policy/notice/integration/callback create/update`; `--skip-validation` preserves confirmed raw passthrough | local | - | local |

## 不覆盖项

主题分区接口 `DescribePartitions`、`SplitPartition`、`MergePartition` 已在官方 API 概览中标记废弃，本期不实现。
