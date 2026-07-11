"""Input and executable validation helpers."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path


def require_files(paths: list[str | Path], label: str = "input file") -> None:
    """Raise FileNotFoundError when any required file is missing."""
    missing = [str(Path(path)) for path in paths if not Path(path).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing required {label}(s): {', '.join(missing)}")


def require_optional_file(path: str | Path | None, label: str) -> None:
    if path:
        require_files([path], label)


def require_directory(path: str | Path, label: str = "directory") -> None:
    if not Path(path).is_dir():
        raise NotADirectoryError(f"Missing required {label}: {path}")


def resolve_tool(tool: str, explicit_path: str | None = None) -> str:
    """Resolve an executable from an explicit path or PATH."""
    if explicit_path:
        explicit = Path(explicit_path)
        if explicit.is_absolute() or explicit.parent != Path("."):
            if not explicit.is_file():
                raise FileNotFoundError(f"Required executable does not exist: {explicit_path}")
            candidate = str(explicit)
        else:
            candidate = shutil.which(explicit_path)
    else:
        candidate = shutil.which(tool)
    if not candidate:
        wanted = explicit_path or tool
        raise FileNotFoundError(f"Required executable not found on PATH: {wanted}")
    logging.debug("Resolved %s to %s", tool, candidate)
    return str(candidate)


def validate_required_tools(tools: list[str]) -> dict[str, str]:
    """Return a mapping of tool name to executable path after validation."""
    return {tool: resolve_tool(tool) for tool in tools}
