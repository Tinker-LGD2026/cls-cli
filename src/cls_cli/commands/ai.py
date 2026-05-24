from __future__ import annotations

import typer

from cls_cli.core.ai import GenerateQueryOptions, build_chat_completions_payload, generate_query
from cls_cli.core.config import store_from_obj
from cls_cli.core.errors import CliError
from cls_cli.core.execution import _client, _obj, _resolve_region
from cls_cli.core.input import parse_timestamp_ms
from cls_cli.core.output import emit_data
from cls_cli.core.query_alias_normalizer import normalize_query_aliases

app = typer.Typer(no_args_is_help=True, help="Use CLS AI capabilities.")


@app.command("generate-query")
def generate_query_command(
    ctx: typer.Context,
    prompt: str = typer.Argument(...),
    topic_id: str = typer.Option(..., "--topic-id"),
    topic_region: str = typer.Option(..., "--topic-region"),
    model: str = typer.Option("text2sql", "--model"),
    region: str | None = typer.Option(None, "--region"),
    profile: str | None = typer.Option(None, "--profile"),
    output: str = typer.Option("json", "--output"),
    only_query: bool = typer.Option(False, "--only-query"),
    normalize_aliases: bool = typer.Option(False, "--normalize-aliases"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    validate_query: bool = typer.Option(False, "--validate-query"),
    from_time: str | None = typer.Option(None, "--from"),
    to_time: str | None = typer.Option(None, "--to"),
    limit: int = typer.Option(100, "--limit"),
) -> None:
    try:
        store = store_from_obj(_obj(ctx))
        profile_obj = store.get_profile(profile)
        selected_region = _resolve_region(region or topic_region, profile_obj)
        options = GenerateQueryOptions(
            prompt=prompt,
            topic_id=topic_id,
            topic_region=topic_region,
            model=model,
        )
        if dry_run:
            emit_data(
                {
                    "dry_run": True,
                    "action": "ChatCompletions",
                    "region": selected_region,
                    "payload": build_chat_completions_payload(options),
                },
                output,
            )
            return
        client = _client(ctx, profile_obj)
        result = generate_query(client, selected_region, options)
        if normalize_aliases:
            original_query = str(result.get("query") or "")
            normalization = normalize_query_aliases(original_query)
            result["original_query"] = original_query
            result["query"] = normalization.query
            result["alias_map"] = normalization.alias_map
            result["condition_hints"] = normalization.condition_hints
        if validate_query:
            query = str(result.get("query") or "")
            search_response = client.invoke(
                "SearchLog",
                {
                    "TopicId": topic_id,
                    "QueryString": query,
                    "From": parse_timestamp_ms(from_time, "from"),
                    "To": parse_timestamp_ms(to_time, "to"),
                    "Limit": limit,
                },
                topic_region,
            )
            response = search_response.get("Response", {})
            result["query_validation"] = {
                "passed": bool(response.get("AnalysisRecords") or response.get("Results")),
                "analysis_record_count": len(response.get("AnalysisRecords") or []),
                "result_count": len(response.get("Results") or []),
                "request_id": response.get("RequestId"),
            }
        if only_query:
            typer.echo(result.get("query") or "")
            return
        emit_data(result, output)
    except CliError as exc:
        from cls_cli.core.output import emit_error

        emit_error(exc)
        raise typer.Exit(exc.exit_code) from exc
