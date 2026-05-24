# Quickstart

This guide gets `cls-cli` running in a safe, mostly read-only path. Review `docs/SECURITY.md` before real writes.

## 1. Run from source

```bash
cd cls-cli
uv sync
uv run cls --help
```

After package publication, use `docs/INSTALL.md` for `pipx`, `pip`, or `uv tool` installation.

## 2. Configure credentials

Use environment variables. Do not write credentials into payload files or Git.

```bash
export TENCENTCLOUD_SECRET_ID='<set-locally>'
export TENCENTCLOUD_SECRET_KEY='<set-locally>'
```

`CLS_SECRET_ID` and `CLS_SECRET_KEY` are also supported.

## 3. Verify read-only access

```bash
uv run cls logset list --region ap-guangzhou
```

Successful JSON output has this shape:

```json
{"data":{"Response":{"RequestId":"req-xxx"}}}
```

Errors use:

```json
{"error":{"code":"AuthFailure.SecretIdNotFound","message":"...","request_id":"req-xxx","action":"DescribeLogsets","region":"ap-guangzhou","retryable":false}}
```

## 4. Search logs

```bash
uv run cls log search \
  --topic-id topic-xxx \
  --query '*' \
  --start-time 1710000000 \
  --end-time 1710003600 \
  --region ap-guangzhou
```

`--start-time` and `--end-time` accept second-level or millisecond-level Unix timestamps. The CLI sends milliseconds to CLS.

## 5. Generate a query with CLS AI

Dry-run first to inspect the `ChatCompletions` request body:

```bash
uv run cls ai generate-query \
  --topic-id topic-xxx \
  --topic-region ap-guangzhou \
  --dry-run \
  '统计 5xx 错误数'
```

Generate and normalize SQL aliases for alarm conditions:

```bash
uv run cls ai generate-query \
  --topic-id topic-xxx \
  --topic-region ap-guangzhou \
  --normalize-aliases \
  '统计 5xx 错误数并按接口分组'
```

Validate generated query execution when evidence is needed:

```bash
uv run cls ai generate-query \
  --topic-id topic-xxx \
  --topic-region ap-guangzhou \
  --validate-query \
  --from 1710000000 \
  --to 1710003600 \
  '统计 5xx 错误数'
```

## 6. Build an alarm policy payload

```bash
uv run cls alarm policy scaffold \
  --name '支付失败告警' \
  --logset-id logset-xxx \
  --topic-id topic-xxx \
  --query 'service:payment | select count(*) as fail_count' \
  --condition '$1.fail_count > 10' \
  --notice-id notice-xxx
```

Validate before writing:

```bash
uv run cls alarm policy validate --payload @alarm-policy.json
```

## 7. Plan an alarm bundle without writing

Use an example bundle as a starting point:

```bash
uv run cls alarm bundle plan \
  --bundle @examples/agent-workflows/existing-topic-existing-webhook/bundle.json
```

`plan` is local and does not call cloud APIs. Real apply requires explicit confirmation:

```bash
uv run cls alarm bundle apply \
  --bundle @bundle.json \
  --region ap-guangzhou \
  --confirm-real-write
```

Do not run real apply until the plan, target region, resource IDs, and rollback behavior have been reviewed.

## 8. Debug an existing alarm

Use read-only commands first:

```bash
uv run cls alarm debug explain \
  --alarm-id alarm-xxx \
  --from 1710000000 \
  --to 1710003600 \
  --region ap-guangzhou

uv run cls alarm history \
  --alarm-id alarm-xxx \
  --from 1710000000 \
  --to 1710003600 \
  --region ap-guangzhou

uv run cls alarm log \
  --alarm-id alarm-xxx \
  --from 1710000000 \
  --to 1710003600 \
  --use-new-analysis \
  --region ap-guangzhou
```

## 9. Clean up temporary verification resources

Preview cleanup first:

```bash
uv run cls alarm verify cleanup \
  --region ap-shanghai \
  --prefix cls-cli- \
  --dry-run
```

Delete only after review:

```bash
uv run cls alarm verify cleanup \
  --region ap-shanghai \
  --prefix cls-cli- \
  --older-than 24h \
  --force
```

## Safety checklist before real writes

- Confirm the region and account.
- Confirm the target topic, logset, notice, integration, and policy IDs.
- Run validators before write commands.
- Review `bundle plan` before `bundle apply`.
- Use environment variables for webhook URLs and cloud credentials.
- Avoid `--skip-validation` unless performing explicit raw passthrough.
- Remember: bundle rollback deletes resources created in the same apply; it does not restore old snapshots for `update` resources yet.
