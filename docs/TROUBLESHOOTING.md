# Troubleshooting

Use JSON output, request IDs, and read-only debug commands to diagnose issues before changing resources.

## Authentication failures

Symptoms:

```json
{"error":{"code":"AuthFailure.SecretIdNotFound","retryable":false}}
```

Actions:

1. Confirm environment variables are set:

```bash
test -n "$TENCENTCLOUD_SECRET_ID" && echo "TENCENTCLOUD_SECRET_ID is set"
test -n "$TENCENTCLOUD_SECRET_KEY" && echo "TENCENTCLOUD_SECRET_KEY is set"
```

2. Confirm profile references the right environment variable names:

```bash
cls profile show dev
```

3. Confirm the account has CLS permissions in the selected region.

## Region or account mismatch

Symptoms:

- Resource not found.
- Empty list responses.
- `debug explain` says the alarm policy does not exist.

Actions:

```bash
cls logset list --region ap-guangzhou
cls topic list --logset-id logset-xxx --region ap-guangzhou
cls alarm policy get --alarm-id alarm-xxx --region ap-guangzhou
```

Try the region where the topic or alarm was created.

## Request limit or transient service errors

Symptoms:

- `RequestLimitExceeded`
- `InternalError`
- network timeout
- exit code `4`
- `retryable=true`

Actions:

- Retry with exponential backoff.
- Reduce concurrent Agent calls.
- Preserve `request_id` in support notes.

## SearchLog returns no rows

Symptoms:

- Query executes but `Results` and `AnalysisRecords` are empty.

Actions:

1. Widen the time range.
2. Confirm topic ID and region.
3. Run a broad query first:

```bash
cls log search --topic-id topic-xxx --query '*' --start-time 1710000000 --end-time 1710003600 --region ap-guangzhou
```

4. Confirm fields are indexed for SQL analysis.

No rows does not automatically mean the query is invalid.

## Alarm condition does not trigger

Symptoms:

- Execution log contains `QueryResultUnmatch`.
- `debug explain` reports that query results did not meet the trigger condition.

Actions:

1. Run policy query manually:

```bash
cls alarm policy test-query --payload @alarm-policy.json --from 1710000000 --to 1710003600 --region ap-guangzhou
```

2. Check selected aliases against the condition:

```bash
cls alarm policy validate --payload @alarm-policy.json
```

3. Confirm `StartTimeOffset`, `EndTimeOffset`, and `MonitorTime` cover the expected data window.

## Notification failed

Symptoms:

- `notification_send_result` is `SendFail` or `SendPartFail`.
- Alarm triggered but no robot message appears.

Actions:

1. Inspect debug summary:

```bash
cls alarm debug explain --alarm-id alarm-xxx --from 1710000000 --to 1710003600 --region ap-guangzhou
```

2. Check notice group bindings:

- `AlarmNoticeIds` in policy;
- `WebCallbackId` in notice group;
- `NoticeContentId` in notice group;
- webhook integration status;
- template JSON escaping and channel-specific escaping.

3. Render template locally with sample context:

```bash
cls alarm template render --payload @notice-content.json --sample-context @sample-alert-context.json
```

4. If testing robot display only, use `send-test`; this does not prove CLS alarm triggering.

## Bundle plan succeeds but apply fails

Possible causes:

- Token resolution issue only discovered during apply.
- Payload validator failure.
- Cloud API rejects a field.
- Resource ID belongs to another region or account.

Actions:

1. Re-run `bundle plan` and inspect resource modes and IDs.
2. Validate individual payloads.
3. Check `error.request_id`, `error.action`, and `error.region`.
4. If resources were created before failure, inspect the returned rollback result.

Current limit: `bundle plan` is not yet a full strict resolved-payload dry-run.

## Rollback or cleanup concern

Before rollback:

```bash
cls alarm bundle status --manifest @manifest.json
```

Before cleanup:

```bash
cls alarm verify cleanup --region ap-shanghai --prefix cls-cli- --dry-run
```

Only delete after confirming region, account, prefix, IDs, and age filter.

Current limit: bundle rollback deletes resources with `mode=create`; it does not restore previous snapshots for `mode=update` resources yet.

## Common validation errors

| Error code | Meaning | Action |
|---|---|---|
| `missing_alarm_targets` | Policy has no query target | Add `AlarmTargets` or use `policy scaffold` |
| `missing_condition_alias` | Condition references an alias not selected by query | Update query alias or condition |
| `invalid_alias_identifier` | SQL alias is not a strict identifier | Use `--normalize-aliases` or rename alias |
| `notice_target_required` | Notice has no receiver, callback, or rules | Add `WebCallbacks`, `NoticeReceivers`, or `NoticeRules` |
| `webhook_required` | Integration payload lacks webhook | Use `--webhook-env` |
| `method_required` | HTTP callback lacks method | Set `POST` or `PUT` |

## Support notes to collect

When escalating, include:

- command run;
- sanitized payload;
- region;
- request ID;
- error code and message;
- whether operation was read, write, or destructive;
- relevant `debug explain` output.
