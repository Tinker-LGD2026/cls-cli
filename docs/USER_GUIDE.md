# User Guide

`cls-cli` is an Agent-friendly command line tool for Tencent Cloud CLS. It exposes deterministic CLI operations for log search, resource management, AI query generation, alarm policy scaffolding, notification templates, notification groups, bundle planning, optional bundle application, and alarm debugging.

It is suitable for assisted operations and controlled Agent workflows. Review `docs/SECURITY.md` before unattended production updates.

## Supported use cases

- List, create, update, and delete common CLS resources.
- Search logs, histograms, context, uploads, and exports.
- Generate CLS query statements with official CLS AI.
- Build alarm policy payloads from generated or manual queries.
- Generate, validate, render, and send-test alarm notice templates.
- Manage alarm webhook integrations and alarm notice groups.
- Validate cross-resource alarm bundles.
- Plan and apply composed alarm bundles.
- Debug existing alarms through history and execution logs.
- Run temporary real E2E verification and cleanup.

## Credentials and profiles

Prefer environment variables:

```bash
export TENCENTCLOUD_SECRET_ID='<set-locally>'
export TENCENTCLOUD_SECRET_KEY='<set-locally>'
```

Alternative variable names are supported:

```bash
export CLS_SECRET_ID='<set-locally>'
export CLS_SECRET_KEY='<set-locally>'
```

Profile usage stores environment variable names and default region, not raw secrets:

```bash
cls profile set dev --region ap-guangzhou \
  --secret-id-env TENCENTCLOUD_SECRET_ID \
  --secret-key-env TENCENTCLOUD_SECRET_KEY
cls logset list --profile dev
```

## Output model

The default output is JSON.

Success:

```json
{"data":{"Response":{"RequestId":"req-xxx"}}}
```

Error:

```json
{"error":{"code":"AuthFailure.SecretIdNotFound","message":"secret id not found","request_id":"req-xxx","action":"DescribeLogsets","region":"ap-guangzhou","retryable":false}}
```

Use `--output table` for humans and `--output jsonl` only for commands that return list-like values. Agents should prefer JSON.

## Logs and indexes

Common read path:

```bash
cls logset list --region ap-guangzhou
cls topic list --logset-id logset-xxx --region ap-guangzhou
cls index get --topic-id topic-xxx --region ap-guangzhou
cls log search --topic-id topic-xxx --query '*' --start-time 1710000000 --end-time 1710003600 --region ap-guangzhou
```

Create index when needed:

```bash
cls index create --topic-id topic-xxx --payload @examples/create-index.json --region ap-guangzhou
```

## AI query generation

CLS AI already has internal topic context access. Provide `--topic-id` and `--topic-region`. The prompt, topic ID, and topic region are sent to the CLS official AI service, so do not include credentials, webhook URLs, personal sensitive information, or unnecessary raw log content in prompts.

```bash
cls ai generate-query --topic-id topic-xxx --topic-region ap-guangzhou --normalize-aliases '统计 5xx 错误数并按接口分组'
```

Use `--dry-run` to inspect the AI request payload. Use `--validate-query --from ... --to ...` when execution evidence is needed.

Agents should parse JSON fields such as `data.query`, `data.alias_map`, `data.condition_hints`, and `data.query_validation`. Avoid `--only-query` in automated workflows because it emits a bare string.

## Alarm workflow

Recommended creation path:

1. Generate or confirm query.
2. Scaffold policy payload.
3. Validate policy payload.
4. Generate notice content template.
5. Validate template with policy payload.
6. Create or reuse integration configuration.
7. Scaffold notice group.
8. Validate notice group.
9. Validate bundle references.
10. Plan bundle.
11. Apply only after explicit confirmation.

Example:

```bash
cls alarm policy scaffold \
  --name 'payment 5xx' \
  --logset-id logset-xxx \
  --topic-id topic-xxx \
  --query 'status:>=500 | select count(*) as error_count' \
  --condition '$1.error_count > 10' \
  --notice-id notice-xxx

cls alarm policy validate --payload @alarm-policy.json
cls alarm template validate --payload @notice-content.json --policy-payload @alarm-policy.json
cls alarm validate bundle --policy @alarm-policy.json --notice-content @notice-content.json --notice @alarm-notice.json --integration @integration.json
```

## Existing-resource-first bundle workflow

Many customer environments already have topics, integrations, and notice groups. Reuse them when IDs are provided.

Typical resource modes:

- `existing`: resource already exists and IDs are provided.
- `create`: CLI creates resource and records returned ID.
- `update`: CLI modifies existing resource.
- `skip`: resource is outside this workflow.

Plan first:

```bash
cls alarm bundle plan --bundle @bundle.json
```

Apply only after review:

```bash
cls alarm bundle apply --bundle @bundle.json --region ap-guangzhou --confirm-real-write
```

Rollback created resources if needed:

```bash
cls alarm bundle rollback --manifest @manifest.json --region ap-guangzhou --force
```

Important: rollback deletes resources created in the same apply. It does not restore previous snapshots for `update` resources yet.

## Debugging alarms

Start read-only:

```bash
cls alarm debug explain --alarm-id alarm-xxx --from 1710000000 --to 1710003600 --region ap-guangzhou
cls alarm history --alarm-id alarm-xxx --from 1710000000 --to 1710003600 --region ap-guangzhou
cls alarm log --alarm-id alarm-xxx --from 1710000000 --to 1710003600 --use-new-analysis --region ap-guangzhou
```

Use the output to distinguish:

- policy not found;
- query result not matching the condition;
- trigger succeeded but notification failed;
- selected time window too narrow;
- region/account mismatch.

## Verification and cleanup

Real E2E verification creates temporary resources and requires explicit confirmation:

```bash
cls alarm verify e2e --region ap-shanghai --dry-run
cls alarm verify e2e --region ap-shanghai --confirm-real-write --poll-seconds 600 --poll-interval-seconds 30
```

Cleanup preview and deletion:

```bash
cls alarm verify cleanup --region ap-shanghai --prefix cls-cli- --dry-run
cls alarm verify cleanup --region ap-shanghai --prefix cls-cli- --older-than 24h --force
```

## Technical-preview limits

- Bundle rollback deletes resources created in the same apply; it does not restore previous snapshots for `update` mode yet.
- Bundle plan validates structure but does not yet provide strict apply-level dry-run with fully resolved payload validation.
- Dedicated discover/upsert helpers are future work; use list/get and payload filters for now.
- `alarm.content.create/update` write-time validation is a known hardening item.
- Treat `--skip-validation` as an escape hatch, not a default path.
