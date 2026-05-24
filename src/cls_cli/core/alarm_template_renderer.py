from __future__ import annotations

import json
import re
from typing import Any


def render_notice_template(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    def render_value(value: Any) -> Any:
        if isinstance(value, str):
            return render_template_string(value, context)
        if isinstance(value, dict):
            return {key: render_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [render_value(item) for item in value]
        return value

    rendered = render_value(payload)
    return rendered if isinstance(rendered, dict) else {}


def render_template_string(
    template: str, context: dict[str, Any], current: Any | None = None
) -> str:
    rendered = _render_defines(template, context, current)
    rendered = _render_ifs(rendered, context, current)
    rendered = _render_ranges(rendered, context, current)
    return _render_actions(rendered, context, current)


def _render_actions(template: str, context: dict[str, Any], current: Any | None) -> str:
    output: list[str] = []
    index = 0
    while index < len(template):
        start = template.find("{{", index)
        if start < 0:
            output.append(template[index:])
            break
        output.append(template[index:start])
        end = _find_action_end(template, start + 2)
        if end < 0:
            output.append(template[start:])
            break
        action = template[start + 2 : end].strip()
        action = action.removeprefix("-").removesuffix("-").strip()
        output.append(_render_action(action, context, current))
        index = end + 2
    return "".join(output)


def _find_action_end(template: str, start: int) -> int:
    in_quote = False
    escaped = False
    index = start
    while index < len(template) - 1:
        char = template[index]
        if escaped:
            escaped = False
        elif char == "\\" and in_quote:
            escaped = True
        elif char == '"':
            in_quote = not in_quote
        elif not in_quote and template[index : index + 2] == "}}":
            return index
        index += 1
    return -1


def _render_action(action: str, context: dict[str, Any], current: Any | None) -> str:
    if action.startswith("toPrettyJson "):
        return json.dumps(
            _resolve_expr(action.removeprefix("toPrettyJson "), context, current),
            ensure_ascii=False,
            indent=2,
        )
    if action.startswith("escape_markdown_html "):
        return _escape_markdown_html(
            _resolve_expr(action.removeprefix("escape_markdown_html "), context, current)
        )
    if action.startswith("escape_markdown "):
        return _escape_markdown(
            _resolve_expr(action.removeprefix("escape_markdown "), context, current)
        )
    if action.startswith("escape "):
        return _escape_json_string(_resolve_expr(action.removeprefix("escape "), context, current))
    return _stringify(_resolve_expr(action, context, current))


def _render_defines(template: str, context: dict[str, Any], current: Any | None) -> str:
    definitions: dict[str, str] = {}
    define_pattern = re.compile(
        r"{{-?\s*define\s+\"([^\"]+)\"\s*-?}}(.*?){{-\s*end\s*-}}",
        re.DOTALL,
    )

    def collect(match: re.Match[str]) -> str:
        definitions[match.group(1)] = match.group(2)
        return ""

    rendered = define_pattern.sub(collect, template)
    render_pattern = re.compile(
        r"{{-?\s*substr\s+\(renderTemplate\s+\"([^\"]+)\"(?:\s+\.)?\)\s+(\d+)\s+(\d+)\s*-?}}"
    )

    def replace(match: re.Match[str]) -> str:
        body = definitions.get(match.group(1), "")
        start = int(match.group(2))
        length = int(match.group(3))
        return render_template_string(body, context, current)[start : start + length]

    return render_pattern.sub(replace, rendered)


def _render_ifs(template: str, context: dict[str, Any], current: Any | None) -> str:
    pattern = re.compile(r"{{-?\s*if\s+([^}]+?)\s*-?}}(.*?){{-?\s*end\s*-?}}", re.DOTALL)

    def replace(match: re.Match[str]) -> str:
        return match.group(2) if bool(_resolve_expr(match.group(1), context, current)) else ""

    previous = None
    rendered = template
    while previous != rendered:
        previous = rendered
        rendered = pattern.sub(replace, rendered)
    return rendered


def _render_ranges(template: str, context: dict[str, Any], current: Any | None) -> str:
    pattern = re.compile(r"{{-?\s*range\s+([^}]+)\s*-?}}(.*?){{-?\s*end\s*-?}}", re.DOTALL)

    def replace(match: re.Match[str]) -> str:
        rows = _resolve_expr(match.group(1), context, current)
        if not isinstance(rows, list):
            return ""
        return "".join(render_template_string(match.group(2), context, row) for row in rows)

    previous = None
    rendered = template
    while previous != rendered:
        previous = rendered
        rendered = pattern.sub(replace, rendered)
    return rendered


def _resolve_expr(expr: str, context: dict[str, Any], current: Any | None) -> Any:
    expr = _strip_wrapping_parens(expr.strip())
    if expr == ".":
        return current if current is not None else context
    if expr.startswith("splitList "):
        args = _split_template_args(expr.removeprefix("splitList "))
        if len(args) != 2:
            return []
        separator = _literal_or_resolved(args[0], context, current)
        value = _literal_or_resolved(args[1], context, current)
        return _stringify(value).split(_stringify(separator)) if value != "" else []
    if expr.startswith("regexReplaceAll "):
        args = _split_template_args(expr.removeprefix("regexReplaceAll "))
        if len(args) != 3:
            return ""
        pattern = _stringify(_literal_or_resolved(args[0], context, current))
        value = _stringify(_literal_or_resolved(args[1], context, current))
        replacement = _go_regex_replacement(
            _stringify(_literal_or_resolved(args[2], context, current))
        )
        return re.sub(pattern, replacement, value)
    if _is_quoted(expr):
        return _unquote(expr)
    if not expr.startswith("."):
        return ""
    tokens = _path_tokens(expr[1:])
    root: Any = current if current is not None else context
    value = _resolve_tokens(root, tokens)
    if value == "" and current is not None:
        value = _resolve_tokens(context, tokens)
    return value


def _literal_or_resolved(expr: str, context: dict[str, Any], current: Any | None) -> Any:
    return _unquote(expr) if _is_quoted(expr) else _resolve_expr(expr, context, current)


def _strip_wrapping_parens(expr: str) -> str:
    while expr.startswith("(") and expr.endswith(")"):
        depth = 0
        in_quote = False
        escaped = False
        wraps = True
        for index, char in enumerate(expr):
            if escaped:
                escaped = False
                continue
            if char == "\\" and in_quote:
                escaped = True
                continue
            if char == '"':
                in_quote = not in_quote
                continue
            if in_quote:
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and index != len(expr) - 1:
                    wraps = False
                    break
        if not wraps:
            break
        expr = expr[1:-1].strip()
    return expr


def _split_template_args(text: str) -> list[str]:
    args: list[str] = []
    start = 0
    depth = 0
    in_quote = False
    escaped = False
    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_quote:
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if char == "(":
            depth += 1
            continue
        if char == ")":
            depth -= 1
            continue
        if char.isspace() and depth == 0:
            if start < index:
                args.append(text[start:index].strip())
            start = index + 1
    if start < len(text):
        args.append(text[start:].strip())
    return args


def _is_quoted(value: str) -> bool:
    return len(value) >= 2 and value[0] == '"' and value[-1] == '"'


def _unquote(value: str) -> str:
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return value[1:-1]
    return loaded if isinstance(loaded, str) else value[1:-1]


def _go_regex_replacement(value: str) -> str:
    return re.sub(r"\$\{(\d+)}", lambda match: f"\\g<{match.group(1)}>", value)


def _path_tokens(path: str) -> list[str | int]:
    tokens: list[str | int] = []
    index = 0
    while index < len(path):
        if path[index] == ".":
            index += 1
            continue
        if path[index] == "[":
            end = path.find("]", index)
            if end < 0:
                break
            raw = path[index + 1 : end]
            tokens.append(int(raw) if raw.isdigit() else raw.strip('"'))
            index = end + 1
            continue
        end = index
        while end < len(path) and path[end] not in ".[":
            end += 1
        tokens.append(path[index:end])
        index = end
    return tokens


def _resolve_tokens(value: Any, tokens: list[str | int]) -> Any:
    current = value
    for token in tokens:
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                return ""
            current = current[token]
            continue
        if not isinstance(current, dict) or token not in current:
            return ""
        current = current[token]
    return current


def _escape_json_string(value: Any) -> str:
    return json.dumps(_stringify(value), ensure_ascii=False)[1:-1]


def _escape_markdown(value: Any) -> str:
    text = _stringify(value)
    for char in ("\\", "`", "*", "_", "[", "]", "(", ")", "#"):
        text = text.replace(char, f"\\{char}")
    return text


def _escape_markdown_html(value: Any) -> str:
    return (
        _escape_markdown(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, int | float | bool):
        return str(value)
    return json.dumps(value, ensure_ascii=False)
