"""YAML configuration loading with a small dependency-free fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _strip_comment(line: str) -> str:
    in_quote = False
    quote_char = ""
    for index, char in enumerate(line):
        if char in {"'", '"'} and (index == 0 or line[index - 1] != "\\"):
            if not in_quote:
                in_quote = True
                quote_char = char
            elif quote_char == char:
                in_quote = False
        if char == "#" and not in_quote:
            return line[:index]
    return line


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _prepare_lines(text: str) -> list[tuple[int, str]]:
    prepared: list[tuple[int, str]] = []
    for raw in text.splitlines():
        cleaned = _strip_comment(raw).rstrip()
        if not cleaned.strip():
            continue
        indent = len(cleaned) - len(cleaned.lstrip(" "))
        prepared.append((indent, cleaned.strip()))
    return prepared


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index
    if lines[index][1].startswith("- "):
        items: list[Any] = []
        while index < len(lines):
            current_indent, content = lines[index]
            if current_indent != indent or not content.startswith("- "):
                break
            item = content[2:].strip()
            if item:
                items.append(_parse_scalar(item))
                index += 1
            else:
                value, index = _parse_block(lines, index + 1, indent + 2)
                items.append(value)
        return items, index

    mapping: dict[str, Any] = {}
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ValueError(f"Unexpected indentation near: {content}")
        if ":" not in content:
            raise ValueError(f"Expected key/value YAML line near: {content}")
        key, value = content.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            mapping[key] = _parse_scalar(value)
            index += 1
        else:
            if index + 1 >= len(lines) or lines[index + 1][0] <= current_indent:
                mapping[key] = {}
                index += 1
            else:
                mapping[key], index = _parse_block(lines, index + 1, lines[index + 1][0])
    return mapping, index


def _fallback_load_yaml(text: str) -> dict[str, Any]:
    lines = _prepare_lines(text)
    if not lines:
        return {}
    parsed, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise ValueError("Could not parse complete YAML document")
    if not isinstance(parsed, dict):
        raise ValueError("Top-level YAML document must be a mapping")
    return parsed


def load_config(config_path: str | Path) -> dict[str, Any]:
    """Load a YAML config file.

    PyYAML is used when available. The fallback parser intentionally supports
    only the simple mapping/list/scalar shape used by the example configs.
    """
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")
    text = path.read_text()
    try:
        import yaml  # type: ignore
    except ImportError:
        return _fallback_load_yaml(text)

    loaded = yaml.safe_load(text) or {}
    if not isinstance(loaded, dict):
        raise ValueError("Top-level YAML document must be a mapping")
    return loaded
