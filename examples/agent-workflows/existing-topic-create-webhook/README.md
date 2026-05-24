# Existing Topic + New Webhook

Use this workflow when the customer already has a CLS topic but needs a new reusable webhook integration.

Do not put the webhook URL into `bundle.json`. Store it in an environment variable and create the integration first.

## Steps

1. Set webhook URL in an environment variable:

```bash
export CLS_ALARM_WEBHOOK_URL='<set locally; do not paste into docs or chat>'
```

2. Create integration:

```bash
cls alarm integration create \
  --name prod-wecom \
  --type wecom \
  --webhook-env CLS_ALARM_WEBHOOK_URL \
  --region ap-guangzhou
```

3. Copy the returned `WebCallbackId` into `bundle.json` as `integration.web_callback_id`.

4. Plan:

```bash
cls alarm bundle plan --bundle @examples/agent-workflows/existing-topic-create-webhook/bundle.json
```

5. Apply only after confirmation:

```bash
cls alarm bundle apply --bundle @examples/agent-workflows/existing-topic-create-webhook/bundle.json --region ap-guangzhou --confirm-real-write
```

## Security note

The example bundle intentionally contains no webhook URL, token, or robot key.
