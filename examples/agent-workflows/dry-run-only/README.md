# Dry-run Only Bundle Example

Use this workflow to demonstrate bundle planning without creating cloud resources.

## Steps

```bash
cls alarm bundle plan --bundle @examples/agent-workflows/dry-run-only/bundle.json
```

`bundle plan` is local and does not call cloud APIs.

Do not run `bundle apply` with this file until all placeholder IDs and payloads are replaced with real customer-approved values.

## Purpose

This example is suitable for:

- Agent demonstrations;
- documentation tests;
- showing resource mode semantics;
- explaining how IDs flow through bundle tokens.
