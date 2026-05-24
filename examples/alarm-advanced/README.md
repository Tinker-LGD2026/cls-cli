# CLS Alarm Advanced Payload Examples

These examples are for `cls-cli` advanced alarm validation and Agent/Skill orchestration.

Accuracy rule:

- Fields confirmed by existing CLI behavior are validated strictly.
- Advanced fields whose full official semantics are not yet confirmed are validated conservatively.
- Use Tencent Cloud CLS official API docs or console-exported payloads as the final source of truth.
- Unknown future fields are preserved by `--payload @file.json` create/update commands.

Recommended workflow:

```bash
cls alarm policy scaffold --name '域名5xx多级告警' --logset-id logset-xxx --topic-id topic-xxx --query 'host:"a.example.com" AND status>=500 | select count(*) as error_count, request_uri group by request_uri' --condition '$1.error_count > 100' --multi-condition-expr '$1.error_count > 100' --multi-condition-level 1 --multi-condition-expr '$1.error_count > 500' --multi-condition-level 2 --group-by request_uri
cls alarm policy validate --payload @examples/alarm-advanced/policy-notice-rules.json
cls alarm policy validate --payload @examples/alarm-advanced/policy-multi-conditions.json
cls alarm policy scaffold --name 'Cron多维分析告警' --logset-id logset-xxx --topic-id topic-xxx --query '* | select count(*) as error_count' --condition '$1.error_count > 0' --monitor-type cron --cron-expression '0/5 * * * *' --analysis-query 'custom query=* | select count(*) as count' --analysis-original-fields '__SOURCE__,__HOSTNAME__,__TIMESTAMP__,__PKG_LOGID__' --classification service=payment --classification env=prod
cls alarm policy validate --payload @examples/alarm-advanced/policy-analysis-classifications.json
cls alarm notice scaffold --name advanced-notice --advanced-rule --rule '{"Value":"AND","Type":"Operation","Children":[{"Type":"Condition","Value":"NotifyType","Children":[{"Value":"In","Type":"Compare"},{"Value":"[1,2]","Type":"Value"}]}]}' --callback-type wecom --integration-id webcallback-xxx --content-id notice-content-xxx --receiver-id 1000001 --receiver-channel Email
cls alarm notice validate --payload @examples/alarm-advanced/notice-rules-advanced.json
cls alarm notice validate --payload @examples/alarm-advanced/notice-rules-generated.json
cls alarm notice scaffold --name advanced-notice --advanced-rule --rule-notify-type 1 --rule-notify-type 2 --rule-level 1 --rule-level 0 --rule-notify-time-between 09:00:00-18:00:00 --rule-duration-gt 1 --rule-alarm-name-regex '^cls-cli-.*' --rule-label-in service=payment --rule-label-regex 'env=prod|staging' --callback-type http --integration-id webcallback-xxx --content-id noticetemplate-xxx --method POST
cls alarm notice validate --payload @examples/alarm-advanced/notice-rules-channel-variants.json
cls alarm notice validate --payload @examples/alarm-advanced/notice-rules-basic.json
cls alarm validate bundle --policy @policy.json --notice @notice.json --notice-content @content.json --integration @integration.json
```
