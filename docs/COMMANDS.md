# CLS CLI Commands

## 通用约定

每个资源命令支持：

- `--region`：腾讯云地域，例如 `ap-guangzhou`。
- `--profile`：读取本地 profile 中的默认地域和凭证环境变量名。
- `--output json|table|jsonl`：默认 `json`。
- `--payload @file.json`：从 JSON 文件读取复杂请求。
- `--payload -`：从标准输入读取 JSON。
- `--dry-run`：只输出 Action、region 和 payload，不调用云 API。
- `--skip-validation`：仅在已确认 raw passthrough payload 时用于跳过本地写入前校验。
- `--force`：执行删除或取消等高风险操作。

## 资源命令

```bash
cls logset list --region ap-guangzhou
cls logset get --logset-id logset-xxx --region ap-guangzhou
cls logset create --logset-name prod --region ap-guangzhou
cls logset update --logset-id logset-xxx --logset-name prod-new --region ap-guangzhou
cls logset delete --logset-id logset-xxx --region ap-guangzhou --force

cls topic create --logset-id logset-xxx --topic-name app --payload @examples/create-topic.json --region ap-guangzhou
cls machine-group add-info --group-id group-xxx --ips 10.0.0.1,10.0.0.2 --region ap-guangzhou
cls config apply --config-id config-xxx --group-id group-xxx --region ap-guangzhou
cls index create --topic-id topic-xxx --payload @examples/create-index.json --region ap-guangzhou
cls log search --topic-id topic-xxx --query 'status:500' --start-time 1710000000 --end-time 1710003600 --region ap-guangzhou
cls log histogram --topic-id topic-xxx --query '*' --start-time 1710000000 --end-time 1710003600 --region ap-guangzhou
cls log upload --topic-id topic-xxx --jsonl examples/upload-log.jsonl --region ap-guangzhou
cls ai generate-query --topic-id topic-xxx --topic-region ap-guangzhou --normalize-aliases '统计 5xx 错误数并按接口分组'
cls ai generate-query --topic-id topic-xxx --topic-region ap-guangzhou --dry-run '统计 5xx 错误数'
cls ai generate-query --topic-id topic-xxx --topic-region ap-guangzhou --validate-query --from 1710000000 --to 1710003600 '统计 5xx 错误数'
cls alarm template generate --scenario http-5xx --channel webhook --fields request_uri,status,error_count
cls alarm template validate --payload @notice-content.json --policy-payload @alarm-policy.json
cls alarm template render --payload @notice-content.json --sample-context @sample-alert-context.json
CLS_ALARM_WEBHOOK_URL='企业微信机器人Webhook地址' cls alarm integration create --name prod-wecom --type wecom --webhook-env CLS_ALARM_WEBHOOK_URL --region ap-guangzhou
cls alarm integration list --region ap-guangzhou --all
cls alarm integration list --region ap-guangzhou --offset 0 --limit 20
cls alarm notice scaffold --name prod-notice --callback-type wecom --integration-id webcallback-xxx --content-id notice-content-xxx
cls alarm notice scaffold --name advanced-notice --advanced-rule --rule '{"Value":"AND","Type":"Operation","Children":[{"Type":"Condition","Value":"NotifyType","Children":[{"Value":"In","Type":"Compare"},{"Value":"[1,2]","Type":"Value"}]}]}' --callback-type wecom --integration-id webcallback-xxx --content-id notice-content-xxx --receiver-id 1000001 --receiver-channel Email
CLS_ALARM_TEST_WEBHOOK_URL='企业微信机器人Webhook地址' cls alarm template send-test --robot wecom --payload @notice-content.json --sample-context @sample-alert-context.json
CLS_ALARM_TEST_FEISHU_WEBHOOK_URL='飞书机器人Webhook地址' cls alarm template send-test --robot feishu --webhook-url-env CLS_ALARM_TEST_FEISHU_WEBHOOK_URL --payload @notice-content.json --sample-context @sample-alert-context.json
cls alarm policy scaffold --scenario http-5xx --name 'api 5xx' --logset-id logset-xxx --topic-id topic-xxx --threshold 10 --window-minutes 5 --notice-id notice-xxx
cls alarm policy scaffold --name '域名5xx多级告警' --logset-id logset-xxx --topic-id topic-xxx --query 'host:"a.example.com" AND status>=500 | select count(*) as error_count, request_uri group by request_uri' --condition '$1.error_count > 100' --multi-condition-expr '$1.error_count > 100' --multi-condition-level 1 --multi-condition-expr '$1.error_count > 500' --multi-condition-level 2 --group-by request_uri
cls alarm policy validate --payload @examples/alarm-advanced/policy-multi-conditions.json
cls alarm policy list --payload @describe-alarms-filter.json --region ap-guangzhou
cls alarm policy get --alarm-id alarm-xxx --region ap-guangzhou
cls alarm notice validate --payload @examples/alarm-advanced/notice-rules-basic.json
cls alarm policy test-query --payload @alarm-policy.json --from 1710000000 --to 1710003600 --region ap-guangzhou
cls alarm history --alarm-id alarm-xxx --from 1710000000 --to 1710003600 --status 0 --region ap-guangzhou
cls alarm log --alarm-id alarm-xxx --from 1710000000 --to 1710003600 --limit 100 --use-new-analysis --region ap-guangzhou
cls alarm debug explain --alarm-id alarm-xxx --from 1710000000 --to 1710003600 --region ap-guangzhou
cls alarm verify e2e --region ap-shanghai --dry-run
cls alarm verify e2e --region ap-shanghai --advanced --dry-run
cls alarm verify e2e --region ap-shanghai --confirm-real-write --poll-seconds 600 --poll-interval-seconds 30
cls alarm verify e2e --region ap-shanghai --advanced --confirm-real-write --poll-seconds 900 --poll-interval-seconds 30
cls alarm verify webhook-functions --region ap-shanghai --dry-run
CLS_ALARM_PUBLIC_WEBHOOK_URL='https://public.example.com/cls-alarm-webhook' cls alarm verify webhook-functions --region ap-shanghai --confirm-real-write --poll-seconds 600 --poll-interval-seconds 30
cls alarm verify webhook-functions --region ap-shanghai --confirm-real-write --external-receiver --public-webhook-url https://public.example.com/cls-alarm-webhook --external-receiver-result-url https://public.example.com/records
cls alarm bundle plan --bundle @bundle.json
cls alarm bundle apply --bundle @bundle.json --confirm-real-write --region ap-guangzhou
cls alarm bundle rollback --manifest @manifest.json --region ap-guangzhou --force
cls alarm bundle status --manifest @manifest.json
cls alarm verify cleanup --region ap-shanghai --prefix cls-cli- --dry-run
cls alarm verify cleanup --region ap-shanghai --prefix cls-cli- --older-than 24h --force
cls alarm policy create --payload @examples/create-alarm.json --region ap-guangzhou --skip-validation
```

## AI 命令说明

- `ai generate-query` 调用 CLS 官方 `ChatCompletions` 非流式接口，使用 `text2sql` 或 `text2sql-reasoning` 模型，将自然语言转换为 CLS 检索分析语句。必须提供 `--topic-id` 和 `--topic-region`，CLI 会通过 Metadata 把主题上下文传给官方 AI 接口；默认只生成不执行，`--dry-run` 只输出即将提交给 `ChatCompletions` 的 payload，`--only-query` 可只输出提取出的查询语句，便于复制给 `log search` 或告警策略。`--normalize-aliases` 会把 AI 可能生成的中文/带引号 SQL alias 规范化成适合 `Condition` 引用的严格英文 alias，并在 JSON 输出中返回 `original_query`、`alias_map` 和 `condition_hints`。如需证明生成语句可执行，可加 `--validate-query --from ... --to ...`，CLI 会在 AI 返回后调用 `SearchLog` 并输出 `query_validation`。

## 日志命令说明

- `log search` 按官方 `SearchLog` 调用，CLI 参数 `--query` 会映射为 `QueryString`。
- `log histogram` 按官方 `DescribeLogHistogram` 调用，CLI 参数 `--query` 会映射为 `Query`。
- `--start-time`、`--end-time` 可传秒级或毫秒级 Unix 时间戳，最终请求统一使用官方要求的毫秒。
- `log upload --jsonl` 每行一个 JSON 对象，CLI 会通过 CLS 专用 Python SDK 上传 Protobuf 二进制日志，不走 JSON CommonClient。

## 告警 Agent 化命令说明

- `alarm template generate` 按场景、渠道和字段生成 `CreateNoticeContent` payload，目前内置 `http-5xx` 场景；`--channel wecom` 会生成企业微信 Markdown 友好的默认模板，使用 `escape_markdown`；`--channel feishu` 会生成飞书卡片/Markdown 友好的默认模板，使用 `escape_markdown_html`。
- `alarm template validate` 校验通知模板变量、Webhook JSON 转义，并可结合 `--policy-payload` 检查 `QueryResult` 字段是否由策略查询输出。
- `alarm template render` 使用样例告警上下文本地渲染触发/恢复通知内容，便于上线前确认客户最终看到的消息。
- `alarm template send-test` 将渲染后的触发通知以企业微信机器人 markdown 消息发送到 `CLS_ALARM_TEST_WEBHOOK_URL`，只用于验证机器人展示效果；Webhook 地址只从环境变量读取，避免写入文件或命令参数。
- `alarm integration create|update|delete|list` 管理控制台“集成配置”，底层对应 `CreateWebCallback` 等 API；`create/update` 可通过 `--webhook-env`、`--key-env` 从环境变量读取机器人地址和私钥，输出会脱敏。`list` 默认按 `--offset 0 --limit 20` 拉取单页，并在 JSON 中输出 `total_count`、`fetched_count`、`truncated`、`page_count` 和 `request_ids`；需要拿全量时使用 `--all`，避免 Agent 把第一页误判为全量。
- `alarm integration scaffold|validate` 生成和校验集成配置 payload，支持 `wecom|dingtalk|feishu|http`，其中 `http` 必须指定 `POST|PUT`。
- `alarm notice scaffold` 生成通知渠道组 payload，推荐通过 `WebCallbacks[].WebCallbackId` 引用已创建集成配置，并绑定 `NoticeContentId`；加 `--advanced-rule` 可生成控制台确认结构的 `NoticeRules`，支持 `--rule` JSON 规则字符串，或使用浏览器真实验证过的规则树参数：`--rule-notify-type`、`--rule-level`、`--rule-notify-time-between`、`--rule-duration-gt`、`--rule-alarm-name-regex`、`--rule-label-in key=v1,v2`、`--rule-label-regex key=regex`；同时支持 `--receiver-id/--receiver-channel` 接收人、`--escalate*` 升级通知和 `--callback-prioritize`。`alarm notice validate` 会检查 `Url` 与 `WebCallbackId` 的互斥规则，并对控制台确认的 `NoticeRules[].Rule` JSON 字符串、`NoticeReceivers`、`WebCallbacks`、`Escalate`、`EscalateNotice`、`CallbackPrioritize` 和疑似时间段字段做确定性结构校验。
- `alarm policy scaffold` 支持两种模式：不传 `--query/--condition` 时生成内置 `http-5xx` 示例策略；传入 `--query` 和 `--condition` 时使用通用模式，把 `cls ai generate-query` 或人工确认后的检索分析语句组装成策略 payload。高级策略可用 `--multi-condition-expr/--multi-condition-level` 生成 `MultiConditions`，用 `--group-by` 生成分组触发字段，用 `--callback-body/--callback-header` 生成策略级 `CallBack`；浏览器真实验证过的 `--monitor-type fixed|cron`、`--cron-expression`、`--analysis-query`、`--analysis-original-fields`、`--classification key=value` 可生成固定/cron 调度、多维分析和告警分类；复杂字段仍可用 `@file.json` 透传。生成 `MultiConditions` 时会按官方互斥规则省略 `Condition/AlarmLevel`。
- `alarm policy validate` 校验 `AlarmTargets[].Query`、`Condition` 与查询 alias 的一致性，并对 `MultiConditions`、`GroupTriggerStatus`、`GroupTriggerCondition`、`Analysis[]`、`Classifications`、`MessageTemplate`、`CallBack`、`MonitorTime` 做 schema-lite 类型校验。字段校验说明：CLS `CreateIndex` 文档未给出完整字段名字符集约束，CLI 只对本地生成的 SQL alias 使用严格标识符规则；对高级字段只做确定性结构校验，不猜测未确认的官方业务语义。
- `alarm validate bundle` 聚合校验策略、通知内容模板、通知渠道组和集成配置，并检查 `AlarmNoticeId`、`NoticeContentId`、`WebCallbackId` 的绑定关系。
- `alarm bundle plan|apply|rollback|status` 支持把 topic、integration、notice_content、notice、policy 组合成可执行图。每个资源可独立选择 `existing`、`create`、`update`、`skip`，因此可复用客户已有 topic、集成配置或通知渠道组；`apply` 会把前序资源返回的 ID 注入后续 payload 并输出 manifest，`rollback` 只删除 manifest 中 `mode=create` 的资源。
- `alarm verify e2e` 执行真实告警闭环验证，仅创建临时日志集、主题、索引、合成日志、集成配置、通知内容模板、告警通知渠道组和告警策略，不涉及机器组和采集配置；真实写入必须传 `--confirm-real-write`，默认清理资源，默认不直发机器人 webhook。加 `--advanced` 会使用真实 API 创建 `MultiConditions` 告警策略和 `NoticeRules` 高级通知渠道组；若确实要额外做机器人展示 smoke test，显式加 `--send-robot-smoke-test`，该结果不作为 CLS 真实触发通过依据。
- `alarm verify webhook-functions` 只验证 `Http` Webhook 告警通知：本机 receiver 模式会写入 `.tmp/alarm-webhook-matrix/<run_id>/received.jsonl`，云端创建临时 CLS 资源并发送到 `--public-webhook-url` 或 `CLS_ALARM_PUBLIC_WEBHOOK_URL`。由于 CLS 在公网回调，本地 `127.0.0.1` 地址不能直接使用，必须提供可公网访问的回调 URL；该 URL 可以来自公网机器、反向代理或隧道。若使用 `--external-receiver`，默认不假设客户告警平台提供结果查询接口，仅以 `notification_send_result=SendSuccess` 作为发送证据；只有自建测试 receiver 暴露 `/records` 等接口时，才可额外传 `--external-receiver-result-url` 自动校验远端收包。该流程覆盖变量提取、`index`、`range`、对象循环、`if/else if`、比较/逻辑、`len`、转义、`toPrettyJson`、`regexReplaceAll`、`splitList`、URL、时间和恢复通知模板等函数；密钥只从运行时环境变量读取，不写入报告。
- `alarm verify cleanup` 按 `--prefix` 扫描并清理真实验证遗留的 `Alarm`、`AlarmNotice`、`WebCallback`、`NoticeContent`、`Index`、`Topic`、`Logset`。默认必须先 `--dry-run` 预览，真实删除必须显式传 `--force`；可用 `--older-than 24h` 只清理早于指定时长的资源，避免误删刚创建的验证资源。
- `alarm history` 支持 `--from`、`--to`、`--alarm-id`、`--topic-id`、`--status`、`--alarm-level`、`--offset`、`--limit`，时间可传秒或毫秒。
- `alarm log` 支持 `--from`、`--to`、`--alarm-id`、`--topic-id`、`--query`、`--limit`、`--context`、`--sort`、`--use-new-analysis`，用于排查策略执行详情。

## 错误输出

```json
{
  "error": {
    "code": "AuthFailure.SecretIdNotFound",
    "message": "secret id not found",
    "request_id": "req-xxx",
    "action": "DescribeLogsets",
    "region": "ap-guangzhou",
    "retryable": false
  }
}
```

## 退出码

| 退出码 | 含义 |
|---:|---|
| 0 | 成功 |
| 1 | 参数、输入或安全确认错误 |
| 2 | 认证错误 |
| 3 | 云 API 错误 |
| 4 | 限频或暂时不可用 |
| 5 | 本地配置或文件错误 |
