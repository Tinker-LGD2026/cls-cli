# Debug Existing Alarm

Use this workflow when the customer asks why an existing alarm did not trigger or did not send notifications.

This workflow is read-only. Do not create, update, apply, rollback, or cleanup resources while diagnosing.

## Commands

```bash
cls alarm debug explain \
  --alarm-id alarm-xxx \
  --from 1710000000 \
  --to 1710003600 \
  --region ap-guangzhou

cls alarm history \
  --alarm-id alarm-xxx \
  --from 1710000000 \
  --to 1710003600 \
  --region ap-guangzhou

cls alarm log \
  --alarm-id alarm-xxx \
  --from 1710000000 \
  --to 1710003600 \
  --use-new-analysis \
  --region ap-guangzhou
```

## What to inspect

- Policy exists in the expected region and account.
- Alarm history contains records for the selected time window.
- Execution log contains `QueryResultUnmatch`, `SendFail`, `SendPartFail`, or `SendSuccess`.
- Query aliases match condition fields.
- Notice group binds the expected `NoticeContentId` and `WebCallbackId`.

## Next action

Only after diagnosis should an Agent propose a change plan. Real writes require validation, plan review, and explicit user confirmation.
