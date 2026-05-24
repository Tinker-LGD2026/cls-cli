# Alarm Bundle Schema

`cls alarm bundle` composes multiple CLS alarm-related resources into one execution graph. It is designed for Agent workflows that need to reuse existing customer resources while creating only the missing pieces.

Plan before apply. Review `docs/SECURITY.md` before real writes.

## Commands

```bash
cls alarm bundle plan --bundle @bundle.json
cls alarm bundle apply --bundle @bundle.json --region ap-guangzhou --confirm-real-write
cls alarm bundle rollback --manifest @manifest.json --region ap-guangzhou --force
cls alarm bundle status --manifest @manifest.json
```

## Top-level shape

```json
{
  "name": "payment-5xx",
  "region": "ap-guangzhou",
  "topic": {},
  "integration": {},
  "notice_content": {},
  "notice": {},
  "policy": {}
}
```

All resource sections are optional. Resources are planned in this order:

```text
topic -> integration -> notice_content -> notice -> policy
```

## Resource modes

### `existing`

Use an existing resource. Required IDs must be provided. The CLI does not create, update, or delete this resource.

```json
{
  "topic": {
    "mode": "existing",
    "logset_id": "logset-xxx",
    "topic_id": "topic-xxx"
  }
}
```

### `create`

Create a new resource using `payload`. The CLI records the returned ID in the manifest and makes it available to later token references.

```json
{
  "notice_content": {
    "mode": "create",
    "payload": {
      "Name": "payment-5xx-content",
      "NoticeContents": [
        {
          "Type": "WeCom",
          "TriggerContent": {
            "Title": "【{{.Level_zh}}】{{.Alarm}}",
            "Content": "告警：{{escape_markdown .Alarm}}\n条件：{{escape_markdown .Condition}}"
          }
        }
      ]
    }
  }
}
```

### `update`

Modify an existing resource using `payload`. The relevant ID is required.

```json
{
  "policy": {
    "mode": "update",
    "alarm_id": "alarm-xxx",
    "payload": {
      "Name": "payment-5xx",
      "AlarmTargets": [],
      "Condition": "$1.error_count > 10"
    }
  }
}
```

Important: rollback snapshot restore for `update` mode is not available yet. If later steps fail, created resources are rolled back, but updated existing resources are not restored automatically.

### `skip`

Ignore this resource in the bundle.

```json
{
  "integration": {
    "mode": "skip"
  }
}
```

## Required ID fields

| Resource | `existing` / `update` required IDs |
|---|---|
| `topic` | `logset_id`, `topic_id` |
| `integration` | `web_callback_id` |
| `notice_content` | `notice_content_id` |
| `notice` | `alarm_notice_id` |
| `policy` | `alarm_id` |

## Token syntax

Payload strings can reference IDs from earlier resources:

```text
${topic.topic_id}
${topic.logset_id}
${integration.web_callback_id}
${notice_content.notice_content_id}
${notice.alarm_notice_id}
```

Example:

```json
{
  "policy": {
    "mode": "create",
    "payload": {
      "Name": "payment-5xx",
      "AlarmNoticeIds": ["${notice.alarm_notice_id}"],
      "AlarmTargets": [
        {
          "LogsetId": "${topic.logset_id}",
          "TopicId": "${topic.topic_id}",
          "Query": "status:>=500 | select count(*) as error_count",
          "Number": 1
        }
      ],
      "Condition": "$1.error_count > 10"
    }
  }
}
```

Token preflight runs before cloud writes in `apply`. If a token cannot be resolved, apply fails before creating resources.

## Minimal existing-resource bundle

```json
{
  "name": "payment-5xx",
  "region": "ap-guangzhou",
  "topic": {
    "mode": "existing",
    "logset_id": "logset-xxx",
    "topic_id": "topic-xxx"
  },
  "integration": {
    "mode": "existing",
    "web_callback_id": "webcallback-xxx"
  },
  "notice_content": {
    "mode": "create",
    "payload": {
      "Name": "payment-5xx-content",
      "NoticeContents": [
        {
          "Type": "WeCom",
          "TriggerContent": {
            "Title": "【{{.Level_zh}}】{{.Alarm}}",
            "Content": "告警：{{escape_markdown .Alarm}}\n条件：{{escape_markdown .Condition}}"
          }
        }
      ]
    }
  },
  "notice": {
    "mode": "create",
    "payload": {
      "Name": "payment-5xx-notice",
      "Type": "All",
      "WebCallbacks": [
        {
          "CallbackType": "WeCom",
          "Url": "",
          "WebCallbackId": "${integration.web_callback_id}",
          "NoticeContentId": "${notice_content.notice_content_id}"
        }
      ]
    }
  },
  "policy": {
    "mode": "create",
    "payload": {
      "Name": "payment-5xx",
      "AlarmNoticeIds": ["${notice.alarm_notice_id}"],
      "AlarmTargets": [
        {
          "LogsetId": "${topic.logset_id}",
          "TopicId": "${topic.topic_id}",
          "Query": "status:>=500 | select count(*) as error_count",
          "Number": 1
        }
      ],
      "Condition": "$1.error_count > 10"
    }
  }
}
```

## Manifest behavior

`bundle apply` returns a manifest containing region and resource IDs. Sensitive fields such as `Webhook` and `Key` are redacted from output.

Example shape:

```json
{
  "name": "payment-5xx",
  "region": "ap-guangzhou",
  "resources": {
    "topic": {"mode": "existing", "logset_id": "logset-xxx", "topic_id": "topic-xxx"},
    "notice_content": {"mode": "create", "notice_content_id": "content-xxx"},
    "notice": {"mode": "create", "alarm_notice_id": "notice-xxx"},
    "policy": {"mode": "create", "alarm_id": "alarm-xxx"}
  }
}
```

## Rollback behavior

Rollback deletes only resources with `mode=create` in the manifest. Deletion order is:

```text
policy -> notice -> notice_content -> integration -> topic
```

Rollback requires `--force`:

```bash
cls alarm bundle rollback --manifest @manifest.json --region ap-guangzhou --force
```

Review the manifest source and region before rollback. Manifest checksum and trusted-manifest enforcement are future hardening items.

## Known limitations

- `plan` validates structure but is not yet a full strict resolved-payload dry-run.
- `apply --dry-run` is not available yet.
- `update` rollback snapshot restore is not available yet.
- Dedicated `discover` / `upsert` helpers are future work.
- `alarm.content.create/update` write-time template validation is a known hardening item.

## Examples

- `examples/agent-workflows/existing-topic-existing-webhook/bundle.json`
- `examples/agent-workflows/existing-topic-create-webhook/bundle.json`
- `examples/agent-workflows/dry-run-only/bundle.json`
