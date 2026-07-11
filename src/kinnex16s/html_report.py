"""Portable HTML report generation."""

from __future__ import annotations

import argparse
import html
from glob import glob
from pathlib import Path
from typing import Any

from .config import load_config


def _pandas():
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "pandas is required for HTML report generation. Install pandas or run in an environment that includes it."
        ) from exc
    return pd


def safe_read_table(path: str | Path):
    path = Path(path)
    if not path.is_file():
        return None
    pd = _pandas()
    try:
        if path.suffix.lower() == ".csv":
            return pd.read_csv(path)
        return pd.read_csv(path, sep="\t")
    except Exception as exc:
        raise ValueError(f"Could not parse report table: {path}: {exc}") from exc


def table_to_html(df, max_rows: int = 50) -> str:
    if df is None:
        return "<p class=\"muted\">No table available.</p>"
    truncated = len(df) > max_rows
    shown = df.head(max_rows)
    table = shown.to_html(index=False, escape=True, classes="data-table")
    if truncated:
        table += f"<p class=\"muted\">Table truncated to {max_rows} of {len(df)} rows.</p>"
    return table


def render_status_badge(status: str) -> str:
    labels = {
        "found": "Found",
        "missing": "Missing",
        "warning": "Warning",
        "not_applicable": "Not applicable",
    }
    css_class = status if status in labels else "warning"
    return f"<span class=\"badge {css_class}\">{html.escape(labels.get(status, status))}</span>"


def markdown_to_html(text: str) -> str:
    blocks: list[str] = []
    in_list = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if in_list:
                blocks.append("</ul>")
                in_list = False
            continue
        if line.startswith("### "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            blocks.append(f"<li>{html.escape(line[2:])}</li>")
        else:
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        blocks.append("</ul>")
    return "\n".join(blocks)


def _read_text_if_exists(path: str | Path | None) -> str | None:
    if not path or not Path(path).is_file():
        return None
    return Path(path).read_text()


def collect_report_inputs(config: dict[str, Any]) -> dict[str, Any]:
    report = config.get("report", {})
    if not isinstance(report, dict):
        raise ValueError("report configuration must be a mapping")
    inputs = report.get("inputs", {}) or {}
    options = report.get("options", {}) or {}

    table_keys = [
        "method_presence_summary",
        "cross_mode_summary",
        "validation_summary",
        "expected_taxa_recovery",
        "missing_expected_taxa",
        "unexpected_taxa",
    ]
    markdown_keys = ["interpretation_checklist", "validation_checklist"]
    tables = {}
    markdown = {}
    found = []
    missing = []
    warnings = []

    for key in table_keys:
        path = inputs.get(key)
        df = safe_read_table(path) if path else None
        if df is None:
            missing.append({"key": key, "path": path or ""})
        else:
            found.append({"key": key, "path": str(path)})
            tables[key] = df

    for key in markdown_keys:
        path = inputs.get(key)
        text = _read_text_if_exists(path)
        if text is None:
            missing.append({"key": key, "path": path or ""})
        else:
            found.append({"key": key, "path": str(path)})
            markdown[key] = text

    for key, pattern in [("pbmm2_qc", inputs.get("pbmm2_qc_glob")), ("pbmm2_counts", inputs.get("pbmm2_counts_glob"))]:
        paths = sorted(glob(str(pattern))) if pattern else []
        if not paths:
            missing.append({"key": key, "path": str(pattern or "")})
            continue
        frames = []
        for path in paths:
            df = safe_read_table(path)
            if df is not None:
                frames.append(df)
                found.append({"key": key, "path": path})
        if frames:
            pd = _pandas()
            tables[key] = pd.concat(frames, ignore_index=True)

    if not found:
        warnings.append("No report input files were found; generated report will contain placeholders.")

    return {
        "title": report.get("title", "PacBio Kinnex 16S-ITS-23S Microbiome Analysis Harness Report"),
        "output_dir": report.get("output_dir", "results/report"),
        "report_file": report.get("report_file", "results/report/kinnex16s_report.html"),
        "options": {
            "max_table_rows": int(options.get("max_table_rows", 50)),
            "include_css": bool(options.get("include_css", True)),
        },
        "found": found,
        "missing": missing,
        "tables": tables,
        "markdown": markdown,
        "warnings": warnings,
    }


def _css() -> str:
    return """
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; line-height: 1.45; color: #1f2933; }
      h1, h2, h3 { color: #102a43; }
      section { margin: 2rem 0; }
      .muted { color: #627d98; }
      .badge { border-radius: 4px; padding: 0.15rem 0.4rem; font-size: 0.85rem; font-weight: 600; }
      .found { background: #d9f99d; color: #365314; }
      .missing { background: #fee2e2; color: #7f1d1d; }
      .warning { background: #fef3c7; color: #78350f; }
      .not_applicable { background: #e5e7eb; color: #374151; }
      table.data-table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
      .data-table th, .data-table td { border: 1px solid #d9e2ec; padding: 0.35rem 0.5rem; text-align: left; vertical-align: top; }
      .data-table th { background: #f0f4f8; }
      .note { background: #f8fafc; border-left: 4px solid #829ab1; padding: 1rem; }
    </style>
    """


def _section(title: str, body: str) -> str:
    return f"<section><h2>{html.escape(title)}</h2>\n{body}\n</section>"


def generate_html_report(config: dict[str, Any], force: bool = False) -> dict[str, Any]:
    report = config.get("report", {})
    if not isinstance(report, dict):
        raise ValueError("report configuration must be a mapping")
    if not force and not bool(report.get("enabled", False)):
        return {"mode": "report", "enabled": False, "outputs": {}}

    collected = collect_report_inputs(config)
    max_rows = collected["options"]["max_table_rows"]
    report_file = Path(collected["report_file"])
    report_file.parent.mkdir(parents=True, exist_ok=True)

    inventory_rows = "".join(
        f"<tr><td>{html.escape(item['key'])}</td><td>{html.escape(item['path'])}</td><td>{render_status_badge('found')}</td></tr>"
        for item in collected["found"]
    ) + "".join(
        f"<tr><td>{html.escape(item['key'])}</td><td>{html.escape(item['path'])}</td><td>{render_status_badge('missing')}</td></tr>"
        for item in collected["missing"]
    )

    sections = [
        _section(
            "Architecture summary",
            "<p>PacBio preprocessing -> YAML downstream router -> mothur classification route -> pbmm2 mapping/QC route -> Emu abundance route -> comparison report -> validation report.</p>",
        ),
        _section(
            "Downstream routing summary",
            "<p>mothur performs taxonomy classification, pbmm2_mapping performs reference-guided alignment and mapping QC, Emu performs full-length 16S abundance estimation when input is compatible, comparison organizes method-specific outputs, and validation compares outputs against user-provided expected taxa.</p>",
        ),
        _section("Method presence summary", table_to_html(collected["tables"].get("method_presence_summary"), max_rows)),
        _section("Cross-mode summary", table_to_html(collected["tables"].get("cross_mode_summary"), max_rows)),
        _section("pbmm2 mapping QC summary", table_to_html(collected["tables"].get("pbmm2_qc"), max_rows)),
        _section("pbmm2 reference counts", table_to_html(collected["tables"].get("pbmm2_counts"), max_rows)),
        _section("Validation summary", table_to_html(collected["tables"].get("validation_summary"), max_rows)),
        _section("Expected taxa recovery", table_to_html(collected["tables"].get("expected_taxa_recovery"), max_rows)),
        _section("Missing expected taxa", table_to_html(collected["tables"].get("missing_expected_taxa"), max_rows)),
        _section("Unexpected observed taxa", table_to_html(collected["tables"].get("unexpected_taxa"), max_rows)),
        _section(
            "Interpretation checklist",
            markdown_to_html(collected["markdown"].get("interpretation_checklist", ""))
            + markdown_to_html(collected["markdown"].get("validation_checklist", "")),
        ),
        _section(
            "Limitations",
            "<div class=\"note\"><p>pbmm2 tables report mapping-derived relative signal, not absolute abundance. Validation recovery is descriptive and depends on the user-provided expected taxa table. Unexpected observed taxa are not automatically false positives, and missing expected taxa are not automatically false negatives. Agreement between methods supports review but does not prove correctness.</p></div>",
        ),
        _section(
            "Output file inventory",
            f"<table class=\"data-table\"><thead><tr><th>Input</th><th>Path</th><th>Status</th></tr></thead><tbody>{inventory_rows}</tbody></table>",
        ),
    ]

    warnings = "".join(f"<li>{html.escape(warning)}</li>" for warning in collected["warnings"])
    html_text = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(str(collected['title']))}</title>"
        + (_css() if collected["options"]["include_css"] else "")
        + "</head><body>"
        f"<h1>{html.escape(str(collected['title']))}</h1>"
        "<p class=\"muted\">Portable HTML report generated from available method-specific outputs.</p>"
        + (f"<section><h2>Warnings</h2><ul>{warnings}</ul></section>" if warnings else "")
        + "\n".join(sections)
        + "</body></html>\n"
    )
    report_file.write_text(html_text)
    return {"mode": "report", "enabled": True, "outputs": {"report_file": str(report_file)}}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("Generate portable HTML report from YAML config")
    parser.add_argument("--config", required=True, help="Project YAML config.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    generate_html_report(load_config(args.config), force=True)
