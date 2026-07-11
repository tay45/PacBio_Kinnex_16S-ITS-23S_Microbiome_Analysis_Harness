"""Route configured downstream analysis modes."""

from __future__ import annotations

import argparse
from typing import Any

from .comparison_report import run_comparison_from_config as _run_comparison_from_config
from .config import load_config
from .emu_runner import run_emu_from_config as _run_emu_from_config
from .html_report import generate_html_report as _generate_html_report
from .mothur_runner import run_configured_mothur
from .pbmm2_runner import run_pbmm2_mapping_from_config as _run_pbmm2_mapping_from_config
from .validation_report import run_validation_from_config as _run_validation_from_config

ALLOWED_DOWNSTREAM_MODES = {
    "mothur",
    "pbmm2_mapping",
    "emu_abundance",
    "comparison",
    "validation",
    "report",
    "both",
    "all",
}


def expand_downstream_mode(mode: str) -> list[str]:
    if mode not in ALLOWED_DOWNSTREAM_MODES:
        allowed = ", ".join(sorted(ALLOWED_DOWNSTREAM_MODES))
        raise ValueError(f"Invalid downstream mode '{mode}'. Allowed modes: {allowed}")
    if mode == "both":
        return ["mothur", "pbmm2_mapping"]
    if mode == "all":
        return ["mothur", "pbmm2_mapping", "emu_abundance"]
    return [mode]


def get_downstream_mode(config: dict[str, Any]) -> str:
    downstream = config.get("downstream", {})
    if not isinstance(downstream, dict):
        raise ValueError("downstream configuration must be a mapping")
    mode = str(downstream.get("mode", "mothur"))
    allowed_modes = downstream.get("allowed_modes", sorted(ALLOWED_DOWNSTREAM_MODES))
    if mode not in allowed_modes:
        raise ValueError(f"Downstream mode '{mode}' is not listed in downstream.allowed_modes")
    return mode


def run_mothur_from_config(config: dict[str, Any]) -> dict[str, Any]:
    return run_configured_mothur(config)


def run_pbmm2_mapping_from_config(config: dict[str, Any]) -> dict[str, Any]:
    return _run_pbmm2_mapping_from_config(config)


def run_emu_from_config(config: dict[str, Any]) -> dict[str, Any]:
    return _run_emu_from_config(config)


def run_comparison_from_config(config: dict[str, Any], force: bool = False) -> dict[str, Any]:
    return _run_comparison_from_config(config, force=force)


def run_validation_from_config(config: dict[str, Any], force: bool = False) -> dict[str, Any]:
    return _run_validation_from_config(config, force=force)


def generate_html_report(config: dict[str, Any], force: bool = False) -> dict[str, Any]:
    return _generate_html_report(config, force=force)


def route_downstream(config: dict[str, Any]) -> list[dict[str, Any]]:
    mode = get_downstream_mode(config)
    results: list[dict[str, Any]] = []
    for route in expand_downstream_mode(mode):
        if route == "mothur":
            results.append(run_mothur_from_config(config))
        elif route == "pbmm2_mapping":
            results.append(run_pbmm2_mapping_from_config(config))
        elif route == "emu_abundance":
            results.append(run_emu_from_config(config))
        elif route == "comparison":
            results.append(run_comparison_from_config(config, force=True))
        elif route == "validation":
            results.append(run_validation_from_config(config, force=True))
        elif route == "report":
            results.append(generate_html_report(config, force=True))
        else:
            raise ValueError(f"Unhandled downstream route: {route}")
    if mode == "all" and bool((config.get("comparison", {}) or {}).get("enabled", False)):
        results.append(run_comparison_from_config(config))
    if mode == "all" and bool((config.get("validation", {}) or {}).get("enabled", False)):
        results.append(run_validation_from_config(config))
    if mode == "all" and bool((config.get("report", {}) or {}).get("enabled", False)):
        results.append(generate_html_report(config))
    return results


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("Route downstream analyses from YAML config")
    parser.add_argument("--config", required=True, help="Project YAML config.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    config = load_config(args.config)
    route_downstream(config)
