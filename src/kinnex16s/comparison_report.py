"""Cross-mode comparison-ready summaries for downstream outputs."""

from __future__ import annotations

import argparse
from glob import glob
from pathlib import Path
from typing import Any

from .config import load_config

NORMALIZED_COLUMNS = [
    "method",
    "feature_id",
    "taxon",
    "count_or_signal",
    "raw_count",
    "source_file",
]


def _pandas():
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "pandas is required for cross-mode comparison reporting. Install pandas or run in an environment that includes it."
        ) from exc
    return pd


def safe_read_tsv(path: str | Path):
    path = Path(path)
    if not path.is_file():
        return None
    pd = _pandas()
    try:
        return pd.read_csv(path, sep="\t")
    except Exception as exc:
        raise ValueError(f"Could not parse TSV file: {path}: {exc}") from exc


def _empty_normalized():
    pd = _pandas()
    return pd.DataFrame(columns=NORMALIZED_COLUMNS)


def _first_present(columns: list[str], candidates: list[str]) -> str | None:
    lower_to_original = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate.lower() in lower_to_original:
            return lower_to_original[candidate.lower()]
    return None


def load_mothur_taxonomy_summary(path: str | Path) -> tuple[Any | None, str]:
    df = safe_read_tsv(path)
    if df is None:
        return None, "missing"
    if df.empty:
        return _empty_normalized(), "present but empty"

    pd = _pandas()
    columns = list(df.columns)
    feature_col = _first_present(columns, ["feature_id", "sequence_id", "sequenceID", "read_id", columns[0]])
    taxon_col = _first_present(columns, ["taxon", "taxonomy", "Taxonomy", columns[1] if len(columns) > 1 else columns[0]])
    count_col = _first_present(columns, ["count", "read_count", "num_seqs", "count_or_signal"])
    if not feature_col or not taxon_col:
        return None, "present but not normalized: unrecognized mothur columns"

    normalized = pd.DataFrame(
        {
            "method": "mothur",
            "feature_id": df[feature_col].astype(str),
            "taxon": df[taxon_col].astype(str),
            "count_or_signal": df[count_col] if count_col else None,
            "raw_count": df[count_col] if count_col else None,
            "source_file": str(path),
        }
    )
    return normalized[NORMALIZED_COLUMNS], "normalized"


def load_pbmm2_reference_counts(path: str | Path):
    df = safe_read_tsv(path)
    if df is None:
        return None
    required = {"reference_id", "read_count", "relative_mapping_signal"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"pbmm2 reference counts missing required columns: {', '.join(sorted(missing))}")
    pd = _pandas()
    normalized = pd.DataFrame(
        {
            "method": "pbmm2_mapping",
            "feature_id": df["reference_id"].astype(str),
            "taxon": df["reference_id"].astype(str),
            "count_or_signal": df["relative_mapping_signal"],
            "raw_count": df["read_count"],
            "source_file": str(path),
        }
    )
    return normalized[NORMALIZED_COLUMNS]


def load_emu_abundance(path: str | Path) -> tuple[Any | None, str]:
    df = safe_read_tsv(path)
    if df is None:
        return None, "missing"
    if df.empty:
        return _empty_normalized(), "present but empty"

    pd = _pandas()
    columns = list(df.columns)
    feature_col = _first_present(columns, ["tax_id", "taxid", "feature_id", "species", "genus"])
    taxon_col = _first_present(columns, ["species", "taxon", "genus", "tax_id", "taxid"])
    signal_col = _first_present(columns, ["abundance", "estimated_abundance", "relative_abundance"])
    if not feature_col or not taxon_col or not signal_col:
        return None, "present but not normalized: unrecognized Emu abundance columns"

    normalized = pd.DataFrame(
        {
            "method": "emu_abundance",
            "feature_id": df[feature_col].astype(str),
            "taxon": df[taxon_col].astype(str),
            "count_or_signal": df[signal_col],
            "raw_count": None,
            "source_file": str(path),
        }
    )
    return normalized[NORMALIZED_COLUMNS], "normalized"


def write_cross_mode_summary(tables: list[Any], output_tsv: str | Path) -> None:
    pd = _pandas()
    Path(output_tsv).parent.mkdir(parents=True, exist_ok=True)
    usable = [table[NORMALIZED_COLUMNS] for table in tables if table is not None and not table.empty]
    combined = pd.concat(usable, ignore_index=True) if usable else pd.DataFrame(columns=NORMALIZED_COLUMNS)
    combined.to_csv(output_tsv, sep="\t", index=False)


def write_method_presence_summary(inputs: list[dict[str, Any]], output_tsv: str | Path) -> None:
    pd = _pandas()
    Path(output_tsv).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(inputs, columns=["method", "expected_file", "found", "normalized", "notes"]).to_csv(
        output_tsv, sep="\t", index=False
    )


def write_interpretation_checklist(output_md: str | Path) -> None:
    Path(output_md).parent.mkdir(parents=True, exist_ok=True)
    Path(output_md).write_text(
        "# Cross-Mode Interpretation Checklist\n\n"
        "- mothur, pbmm2_mapping, and Emu answer different questions.\n"
        "- Agreement between modes is supportive but not definitive.\n"
        "- Disagreement can arise from database differences, reference incompleteness, multi-mapping, PCR/primer bias, rRNA copy-number variation, and 16S-ITS-23S input compatibility.\n"
        "- pbmm2 mapping-derived relative signal is not absolute abundance.\n"
        "- Emu abundance estimates require full-length 16S-compatible input.\n"
        "- mothur outputs depend on selected filtering/classification parameters.\n",
    )


def run_comparison_from_config(config: dict[str, Any], force: bool = False) -> dict[str, Any]:
    comparison = config.get("comparison", {})
    if not isinstance(comparison, dict):
        raise ValueError("comparison configuration must be a mapping")
    if not force and not bool(comparison.get("enabled", False)):
        return {"mode": "comparison", "enabled": False, "outputs": {}}

    output_dir = Path(str(comparison.get("output_dir", "results/comparison")))
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = comparison.get("outputs", {}) or {}

    tables = []
    presence: list[dict[str, Any]] = []

    mothur_path = comparison.get("mothur_taxonomy_file")
    mothur_table, mothur_note = load_mothur_taxonomy_summary(mothur_path) if mothur_path else (None, "not configured")
    tables.append(mothur_table)
    presence.append(
        {
            "method": "mothur",
            "expected_file": mothur_path or "",
            "found": bool(mothur_path and Path(mothur_path).is_file()),
            "normalized": mothur_table is not None,
            "notes": mothur_note,
        }
    )

    pbmm2_pattern = comparison.get("pbmm2_reference_counts_glob", "")
    pbmm2_paths = sorted(glob(str(pbmm2_pattern))) if pbmm2_pattern else []
    if pbmm2_paths:
        for path in pbmm2_paths:
            table = load_pbmm2_reference_counts(path)
            tables.append(table)
            presence.append(
                {
                    "method": "pbmm2_mapping",
                    "expected_file": path,
                    "found": True,
                    "normalized": table is not None,
                    "notes": "normalized",
                }
            )
    else:
        presence.append(
            {
                "method": "pbmm2_mapping",
                "expected_file": str(pbmm2_pattern),
                "found": False,
                "normalized": False,
                "notes": "missing",
            }
        )

    emu_path = comparison.get("emu_abundance_file")
    emu_table, emu_note = load_emu_abundance(emu_path) if emu_path else (None, "not configured")
    tables.append(emu_table)
    presence.append(
        {
            "method": "emu_abundance",
            "expected_file": emu_path or "",
            "found": bool(emu_path and Path(emu_path).is_file()),
            "normalized": emu_table is not None,
            "notes": emu_note,
        }
    )

    output_paths = {}
    if outputs.get("cross_mode_summary", True):
        path = output_dir / "cross_mode_summary.tsv"
        write_cross_mode_summary(tables, path)
        output_paths["cross_mode_summary"] = str(path)
    if outputs.get("method_presence_summary", True):
        path = output_dir / "method_presence_summary.tsv"
        write_method_presence_summary(presence, path)
        output_paths["method_presence_summary"] = str(path)
    if outputs.get("interpretation_checklist", True):
        path = output_dir / "interpretation_checklist.md"
        write_interpretation_checklist(path)
        output_paths["interpretation_checklist"] = str(path)

    return {"mode": "comparison", "enabled": True, "outputs": output_paths}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("Build cross-mode comparison report from YAML config")
    parser.add_argument("--config", required=True, help="Project YAML config.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    config = load_config(args.config)
    run_comparison_from_config(config, force=True)
