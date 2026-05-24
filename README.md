# CLS CLI

面向腾讯云日志服务（CLS）的 Agent 友好命令行工具。所有行为、参数和验证以腾讯云 CLS 官方 API 文档为准。

适用于 CLS 资源管理、日志查询、告警配置辅助和受控 Agent 工作流。

## Documentation

- Quickstart: `docs/QUICKSTART.md`
- User guide: `docs/USER_GUIDE.md`
- Agent integration: `docs/AGENT_INTEGRATION.md`
- Bundle schema: `docs/BUNDLE_SCHEMA.md`
- Security: `docs/SECURITY.md`
- Install: `docs/INSTALL.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md`
- Commands: `docs/COMMANDS.md`
- API matrix: `docs/API_MATRIX.md`

## 安装

```bash
uv sync
uv run cls --help
```

## 认证

默认从环境变量读取凭证，不建议把密钥写入配置文件：

```bash
export TENCENTCLOUD_SECRET_ID=<set-locally>
export TENCENTCLOUD_SECRET_KEY=<set-locally>
uv run cls logset list --region ap-guangzhou
```

也兼容：

```bash
export CLS_SECRET_ID=<set-locally>
export CLS_SECRET_KEY=<set-locally>
```

## Profile

```bash
uv run cls profile set dev --region ap-guangzhou \
  --secret-id-env TENCENTCLOUD_SECRET_ID \
  --secret-key-env TENCENTCLOUD_SECRET_KEY
uv run cls logset list --profile dev
```

配置文件默认位于 `~/.cls-cli/config.toml`，也可通过 `CLS_CLI_CONFIG_DIR` 指定目录。

## 命令范围

```text
cls profile list|show|set|use|delete
cls logset list|get|create|update|delete
cls topic list|get|create|update|delete
cls machine-group list|get|create|update|delete|machines|add-info|delete-info
cls config list|get|create|update|delete|apply|remove|bound-groups|bound-configs
cls index get|create|update|delete|rebuild-estimate|rebuild-create|rebuild-list|rebuild-cancel
cls log search|histogram|context|upload|export-create|export-list|export-delete
cls ai generate-query
cls alarm policy list|get|create|update|delete|scaffold|validate|test-query
cls alarm integration list|create|update|delete|scaffold|validate
cls alarm notice list|create|update|delete|scaffold|validate
cls alarm shield|content|callback list|create|update|delete
cls alarm template generate|validate|render|send-test
cls alarm validate bundle
cls alarm bundle plan|apply|rollback|status
cls alarm debug explain
cls alarm verify e2e|webhook-functions|cleanup
cls alarm history|log
```

## Agent 调用约定

- 默认输出 JSON：`{"data": ...}` 或 `{"error": ...}`。
- 复杂请求使用 `--payload @file.json` 或 `--payload -`。
- 批量上传日志可使用 JSON Lines：`cls log upload --topic-id xxx --jsonl logs.jsonl --region ap-guangzhou`，底层使用 CLS 专用二进制上传 SDK。
- `cls ai generate-query` 调用 CLS 官方 `ChatCompletions` 非流式接口，基于自然语言、`--topic-id` 和 `--topic-region` 生成检索分析语句；默认只生成不执行。
- `cls log search` / `histogram` / `export-create` 的 `--start-time`、`--end-time` 可传秒级或毫秒级 Unix 时间戳，CLI 会按官方 API 转为毫秒。
- 删除类命令必须传 `--force`；可先使用 `--dry-run` 查看将要调用的 Action 和 payload。
- 推荐告警配置链路：先用 `cls ai generate-query` 生成检索分析语句，再用 `cls alarm policy scaffold --query --condition` 组装策略，用 `cls alarm template generate/validate/render` 生成并预览通知内容，用 `cls alarm integration` 和 `cls alarm notice` 维护通知链路，最后用 `cls alarm validate bundle` 做总校验。
- 告警模板可先用 `cls alarm template generate` 生成，再用 `validate` 校验变量、渠道化转义和策略查询字段配合；需要真实闭环时可运行 `cls alarm verify e2e`，加 `--advanced` 会真实创建 `MultiConditions` + `NoticeRules` 高级告警链路；该命令只创建日志集/主题/索引/合成日志、集成配置、通知内容模板、告警通知渠道组和告警策略，默认不直发机器人 webhook；若测试中断遗留资源，可先用 `cls alarm verify cleanup --prefix ... --dry-run` 预览，再加 `--force` 清理。
- 错误结构固定包含：`code`、`message`、`request_id`、`action`、`region`、`retryable`。

## 示例

```bash
uv run cls topic create --region ap-guangzhou --logset-id logset-xxx --payload @examples/create-topic.json
uv run cls index create --region ap-guangzhou --topic-id topic-xxx --payload @examples/create-index.json
uv run cls log search --region ap-guangzhou --topic-id topic-xxx --query 'status:500' --start-time 1710000000 --end-time 1710003600
uv run cls ai generate-query --topic-id topic-xxx --topic-region ap-guangzhou '统计 5xx 错误数并按接口分组'
uv run cls ai generate-query --topic-id topic-xxx --topic-region ap-guangzhou --normalize-aliases '统计 5xx 错误数并按接口分组'
uv run cls ai generate-query --topic-id topic-xxx --topic-region ap-guangzhou --only-query '统计支付失败次数'
uv run cls alarm template generate --scenario http-5xx --channel wecom --fields request_uri,status,error_count
uv run cls alarm template generate --scenario http-5xx --channel feishu --fields request_uri,status,error_count
uv run cls alarm template render --payload @notice-content.json --sample-context @sample-alert-context.json
export CLS_ALARM_WEBHOOK_URL='企业微信机器人Webhook地址'
uv run cls alarm integration create --region ap-guangzhou --name prod-wecom --type wecom --webhook-env CLS_ALARM_WEBHOOK_URL
uv run cls alarm notice scaffold --name prod-notice --callback-type wecom --integration-id webcallback-xxx --content-id notice-content-xxx
uv run cls alarm notice scaffold --name advanced-notice --advanced-rule --rule '{"Value":"AND","Type":"Operation","Children":[{"Type":"Condition","Value":"NotifyType","Children":[{"Value":"In","Type":"Compare"},{"Value":"[1,2]","Type":"Value"}]}]}' --callback-type wecom --integration-id webcallback-xxx --content-id notice-content-xxx --receiver-id 1000001 --receiver-channel Email
export CLS_ALARM_TEST_WEBHOOK_URL='企业微信机器人Webhook地址'
uv run cls alarm template send-test --robot wecom --payload @notice-content.json --sample-context @sample-alert-context.json
export CLS_ALARM_TEST_FEISHU_WEBHOOK_URL='飞书机器人Webhook地址'
uv run cls alarm template send-test --robot feishu --webhook-url-env CLS_ALARM_TEST_FEISHU_WEBHOOK_URL --payload @notice-content.json --sample-context @sample-alert-context.json
uv run cls alarm policy scaffold --scenario http-5xx --name 'api 5xx' --logset-id logset-xxx --topic-id topic-xxx --threshold 10 --window-minutes 5 --notice-id notice-xxx
uv run cls alarm policy scaffold --name '支付失败告警' --logset-id logset-xxx --topic-id topic-xxx --query 'service:payment | select count(*) as fail_count' --condition '$1.fail_count > 10' --notice-id notice-xxx
uv run cls alarm policy scaffold --name '域名5xx多级告警' --logset-id logset-xxx --topic-id topic-xxx --query 'host:"a.example.com" AND status>=500 | select count(*) as error_count, request_uri group by request_uri' --condition '$1.error_count > 100' --multi-condition-expr '$1.error_count > 100' --multi-condition-level 1 --multi-condition-expr '$1.error_count > 500' --multi-condition-level 2 --group-by request_uri
uv run cls alarm policy validate --payload @alarm-policy.json
uv run cls alarm policy validate --payload @examples/alarm-advanced/policy-notice-rules.json
uv run cls alarm policy validate --payload @examples/alarm-advanced/policy-multi-conditions.json
uv run cls alarm policy validate --payload @examples/alarm-advanced/policy-analysis-classifications.json
uv run cls alarm notice validate --payload @examples/alarm-advanced/notice-rules-advanced.json
uv run cls alarm notice validate --payload @examples/alarm-advanced/notice-rules-basic.json
uv run cls alarm validate bundle --policy @alarm-policy.json --notice-content @notice-content.json --notice @alarm-notice.json --integration @integration.json
uv run cls alarm policy test-query --payload @alarm-policy.json --region ap-guangzhou --from 1710000000 --to 1710003600
uv run cls alarm debug explain --region ap-guangzhou --alarm-id alarm-xxx --from 1710000000 --to 1710003600
uv run cls alarm verify e2e --region ap-shanghai --dry-run
uv run cls alarm verify e2e --region ap-shanghai --confirm-real-write --poll-seconds 600 --poll-interval-seconds 30
uv run cls alarm verify cleanup --region ap-shanghai --prefix cls-cli- --dry-run
uv run cls alarm verify cleanup --region ap-shanghai --prefix cls-cli- --older-than 24h --force
```