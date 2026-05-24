# Existing Topic + Existing Webhook

Use this workflow when the customer already provides:

- `logset_id`
- `topic_id`
- `web_callback_id`

The bundle reuses the topic and webhook integration, then creates notice content, notice group, and policy.

## Steps

1. Replace placeholder IDs in `bundle.json`.
2. Plan locally:

```bash
cls alarm bundle plan --bundle @examples/agent-workflows/existing-topic-existing-webhook/bundle.json
```

3. Review the plan with the customer.
4. Apply only after confirmation:

```bash
cls alarm bundle apply --bundle @examples/agent-workflows/existing-topic-existing-webhook/bundle.json --region ap-guangzhou --confirm-real-write
```

5. Save the returned manifest for rollback.

## Rollback

```bash
cls alarm bundle rollback --manifest @manifest.json --region ap-guangzhou --force
```

Rollback deletes resources created by this bundle. It does not delete existing topic or integration resources.
