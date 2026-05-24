# Agent Integration Guide

This guide is for agents that call `cls-cli` as a deterministic CLS execution layer.

Agents may use the CLI for assisted workflows, but must not perform unattended real customer-resource writes without a reviewed plan and explicit confirmation.

## Core contract

- Always prefer `--output json`.
- Parse successful output from `data`.
- Parse failed output from `error`.
- Use `--payload @file.json` for complex payloads.
- Use `--payload -` only when streaming JSON through stdin is safer than writing a temporary file.
- Never put `SecretId`, `SecretKey`, webhook URLs, robot keys, tokens, or authorization headers into tracked files.
- Use environment variables for secret-bearing values.
- Never run real writes until the user has reviewed the plan and confirmed.
- Do not use `--skip-validation` unless the user explicitly requests raw passthrough and accepts the risk.
- Avoid `--only-query`; parse `data.query` from JSON instead.
- Prefer existing customer resources when IDs are provided.

## CLI enforcement vs Agent policy

`cls-cli` is not a sandbox. It enforces destructive confirmations and selected real-write confirmations, but regular write commands can still mutate cloud resources when an Agent invokes them with valid credentials. Agent integrations should maintain their own command allowlist, risk classification, human confirmation gate, credential isolation, and audit log.

`cls ai generate-query` sends the prompt, `topic_id`, and `topic_region` to the CLS official `ChatCompletions` service. Do not include credentials, webhook URLs, personal sensitive information, or unnecessary raw log content in prompts.

## Output handling

Success:

```json
{"data":{"key":"value"}}
```

Error:

```json
{"error":{"code":"...","message":"...","request_id":"...","action":"...","region":"...","retryable":false}}
```

Retry guidance:

- `retryable=true` or exit code `4`: retry with exponential backoff.
- exit code `1`: fix input, validation, or confirmation flow.
- exit code `2`: ask user to fix credentials.
- exit code `3`: inspect CLS API error and `request_id`.
- exit code `5`: fix local config or file path.

## Safety rules for agents

### Real writes

Before any `create`, `update`, `apply`, `send-test`, `verify e2e --confirm-real-write`, or destructive command:

1. Generate or load payload.
2. Run local validators where available.
3. Run `bundle plan` or a command-specific `--dry-run` where available.
4. Present action, region, target IDs, and rollback behavior to the user.
5. Ask for explicit confirmation.
6. Execute only after confirmation.

### Destructive commands

Commands with `--force` delete, cancel, unbind, or clean up resources. Do not add `--force` automatically. Ask for confirmation and show the exact target IDs or cleanup prefix.

### Bundle updates

When `mode=update` is present, warn the user:

```text
Current bundle rollback deletes resources created during this apply. It does not restore previous snapshots for updated resources yet.
```

For update workflows, prefer taking a manual describe snapshot before real writes.

### Secrets

If the user provides a webhook URL containing a key or token, do not write it into bundle JSON. Ask the user to set an environment variable:

```bash
export CLS_ALARM_WEBHOOK_URL='<set locally; do not paste into docs or chat>'
cls alarm integration create --name prod-wecom --type wecom --webhook-env CLS_ALARM_WEBHOOK_URL --region ap-guangzhou
```

## Workflow 1: Generate query and policy

1. Generate query:

```bash
cls ai generate-query --topic-id topic-xxx --topic-region ap-guangzhou --normalize-aliases '统计支付失败次数'
```

2. Parse `data.query` and `data.condition_hints`.
3. Scaffold policy:

```bash
cls alarm policy scaffold --name 'payment failures' --logset-id logset-xxx --topic-id topic-xxx --query '<query>' --condition '$1.error_count > 10' --notice-id notice-xxx
```

4. Validate:

```bash
cls alarm policy validate --payload @policy.json
```

## Workflow 2: Existing topic and existing webhook

Use this when the user provides `topic_id`, `logset_id`, and `web_callback_id`.

- Treat topic as `existing`.
- Treat integration as `existing`.
- Create or reuse notice content and notice group as needed.
- Bind policy to notice group.
- Run `cls alarm bundle plan` before any apply.

## Workflow 3: Existing topic and new webhook

1. Ask the user to set `CLS_ALARM_WEBHOOK_URL`.
2. Create integration through env var:

```bash
cls alarm integration create --name prod-wecom --type wecom --webhook-env CLS_ALARM_WEBHOOK_URL --region ap-guangzhou
```

3. Use returned `WebCallbackId` in bundle or notice scaffold.
4. Do not store the raw webhook URL in examples, bundle files, or chat summaries.

## Workflow 4: Debug existing alarm read-only

Use only read/debug commands:

```bash
cls alarm debug explain --alarm-id alarm-xxx --from 1710000000 --to 1710003600 --region ap-guangzhou
cls alarm history --alarm-id alarm-xxx --from 1710000000 --to 1710003600 --region ap-guangzhou
cls alarm log --alarm-id alarm-xxx --from 1710000000 --to 1710003600 --use-new-analysis --region ap-guangzhou
```

Do not scaffold, create, update, apply, rollback, or cleanup unless the user changes the task from diagnosis to remediation.

## Workflow 5: Real E2E verification

Use temporary resources only after confirmation:

```bash
cls alarm verify e2e --region ap-shanghai --dry-run
cls alarm verify e2e --region ap-shanghai --confirm-real-write --poll-seconds 600 --poll-interval-seconds 30
```

If interrupted, preview cleanup first:

```bash
cls alarm verify cleanup --region ap-shanghai --prefix cls-cli- --dry-run
```

Then delete only after confirmation:

```bash
cls alarm verify cleanup --region ap-shanghai --prefix cls-cli- --older-than 24h --force
```

## Query validation semantics

`ai generate-query --validate-query` proves that `SearchLog` was called and returns `query_validation`. Empty results can mean the time window has no matching data. Do not call the SQL invalid solely because there are no rows. Use `request_id` and the API error status as evidence.

## Known integration limits for agents

- `bundle plan` is not a strict resolved-payload dry-run yet.
- `bundle rollback` does not restore old snapshots for `update` resources.
- Dedicated resource discover/upsert helpers are not complete yet.
- Avoid unattended broad updates until these limits are addressed.
