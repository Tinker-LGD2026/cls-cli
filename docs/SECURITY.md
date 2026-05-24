# Security Guide

This document describes safe use of `cls-cli` in customer and Agent workflows.

Use reviewed plans and explicit confirmations for real writes.

## Credential handling

Use environment variables for Tencent Cloud credentials:

```bash
export TENCENTCLOUD_SECRET_ID='<set-locally>'
export TENCENTCLOUD_SECRET_KEY='<set-locally>'
```

Supported aliases:

```bash
export CLS_SECRET_ID='<set-locally>'
export CLS_SECRET_KEY='<set-locally>'
```

Do not:

- commit `.env`;
- put SecretId or SecretKey in payload JSON;
- paste credentials into issue descriptions or logs;
- store raw credentials in profile files.

Profiles store environment variable names, not secret values:

```bash
cls profile set dev --region ap-guangzhou \
  --secret-id-env TENCENTCLOUD_SECRET_ID \
  --secret-key-env TENCENTCLOUD_SECRET_KEY
```

## Webhook and robot secrets

Webhook URLs often contain tokens or keys. Treat them as secrets.

Recommended:

```bash
export CLS_ALARM_WEBHOOK_URL='<set locally; do not paste into docs or chat>'
cls alarm integration create --name prod-wecom --type wecom --webhook-env CLS_ALARM_WEBHOOK_URL --region ap-guangzhou
```

Do not write webhook URLs into:

- Git-tracked bundle files;
- README examples;
- shell history when avoidable;
- chat summaries;
- CI logs.

The CLI redacts common sensitive fields in outputs, but redaction is a safety net, not a storage strategy.

## AI prompt data boundary

`cls ai generate-query` sends the prompt, `topic_id`, and `topic_region` to the CLS official `ChatCompletions` service. Do not include credentials, webhook URLs, personal sensitive information, or unnecessary raw log content in AI prompts.

## CLI enforcement vs Agent policy

The CLI is not a sandbox. It enforces destructive confirmations and selected real-write confirmations, but normal `create`, `update`, `log upload`, and `send-test` commands can perform writes once invoked with valid credentials. Agent platforms should add their own allowlist, risk classification, human confirmation gate, credential isolation, and audit logging around CLI calls.

## Operation risk levels

| Risk | Meaning | Examples |
|---|---|---|
| `read` | No cloud mutation | `list`, `get`, `search`, `history`, `log`, `debug explain` |
| `write` | Creates or modifies cloud resources | `create`, `update`, `bundle apply`, `log upload` |
| `destructive` | Deletes, cancels, unbinds, or cleans up | `delete`, `rollback`, `cleanup`, `cancel` |
| `external write` | Sends data to external systems | `alarm template send-test`, webhook verification |

## Confirmation rules

### `--dry-run`

Use dry-run before risky operations when available. Dry-run should be treated as a plan preview, not as proof that cloud writes will succeed.

### `--confirm-real-write`

Required for flows that create temporary or composed cloud resources:

```bash
cls alarm verify e2e --confirm-real-write
cls alarm bundle apply --confirm-real-write
```

Agents must present the plan and receive explicit user confirmation before adding this flag.

### `--force`

Required for destructive operations:

```bash
cls topic delete --topic-id topic-xxx --force
cls alarm bundle rollback --manifest @manifest.json --force
cls alarm verify cleanup --prefix cls-cli- --force
```

Agents must show target IDs or cleanup filters before using `--force`.

### `--skip-validation`

This bypasses local write-time validation. Use it only for deliberate raw passthrough after user approval.

Do not use it as a workaround for validation errors. Fix the payload unless the user explicitly accepts the risk.

## Bundle apply and rollback

Safe default:

```bash
cls alarm bundle plan --bundle @bundle.json
```

Real write:

```bash
cls alarm bundle apply --bundle @bundle.json --region ap-guangzhou --confirm-real-write
```

Rollback:

```bash
cls alarm bundle rollback --manifest @manifest.json --region ap-guangzhou --force
```

Important limits:

- Rollback deletes resources that were created in the same apply.
- Rollback does not restore previous snapshots for `update` resources yet.
- Manifest checksum and trusted-manifest verification are future hardening items.
- Review manifest source, region, and IDs before rollback.

## Minimum permission guidance

Use least privilege. Split roles when possible:

### Read-only diagnosis

Needs read permissions for:

- logsets/topics/indexes;
- `SearchLog`, `DescribeLogHistogram`, `DescribeLogContext`;
- alarm policies, alarm history, alarm execution logs;
- notice contents, notice groups, and integrations if debugging notification failures.

### Alarm authoring

Needs write permissions for:

- notice content;
- web callback integration;
- alarm notice group;
- alarm policy;
- topic/index only if the workflow creates temporary verification resources.

### Cleanup and rollback

Needs delete permissions for the target resource types. Limit by environment/account where possible.

## Agent-specific rules

Agents should:

- default to read-only commands during diagnosis;
- keep secrets in environment variables;
- write bundle files without secrets;
- use JSON output;
- show plan and risk summary before real writes;
- mention current rollback limits for updates;
- preserve request IDs in final summaries.

Agents should not:

- silently add `--force`;
- silently add `--confirm-real-write`;
- use `--skip-validation` to bypass a failed validator;
- claim update rollback is fully automatic;
- create new integrations when `web_callback_id` is already provided.
