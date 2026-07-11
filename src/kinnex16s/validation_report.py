"""Mock-community / expected-taxa validation reports."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from glob import glob
from pathlib import Path
from typing import Any

from .config import load_config

EXPECTED_COLUMNS = [
    "expected_id",
    "expected_name",
    "expected_relative_abundance",
    "expected_group",
    "notes",
    "source_file",
]
OBSERVED_COLUMNS = ["method", "observed_id", "observed_name", "observed_signal", "raw_count", "source_file"]
RECOVERY_COLUMNS = [
    "expected_id",
    "expected_name",
    "method",
    "matched",
    "matched_observed_id",
    "matched_observed_name",
    "observed_signal",
    "raw_count",
    "match_mode",
]


def _pandas():
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "pandas is required for validation reporting. Install pandas or run in an environment that includes it."
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
        if path.suffix.lower() in {".tsv", ".txt"}:
            return pd.read_csv(path, sep="\t")
        with path.open(newline="") as handle:
            sample = handle.read(4096)
            delimiter = csv.Sniffer().sniff(sample, delimiters=",\t").delimiter if sample else "\t"
        return pd.read_csv(path, sep=delimiter)
    except Exception as exc:
        raise ValueError(f"Could not parse table file: {path}: {exc}") from exc


def _first_present(columns: list[str], candidates: list[str]) -> str | None:
    lower_to_original = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate.lower() in lower_to_original:
            return lower_to_original[candidate.lower()]
    return None


def load_expected_taxa(path: str | Path):
    df = safe_read_table(path)
    if df is None:
        raise FileNotFoundError(f"Expected taxa file not found: {path}")
    pd = _pandas()
    columns = list(df.columns)
    id_col = _first_present(columns, ["expected_id", "taxon", "reference_id", "species"])
    name_col = _first_present(columns, ["expected_name", "taxon_name", "species", "reference_id", "taxon"])
    if not id_col or not name_col:
        raise ValueError("Expected taxa table must include an expected_id/taxon/reference_id/species field and a name field")
    abundance_col = _first_present(columns, ["expected_relative_abundance"])
    group_col = _first_present(columns, ["expected_group"])
    notes_col = _first_present(columns, ["notes"])
    normalized = pd.DataFrame(
        {
            "expected_id": df[id_col].astype(str),
            "expected_name": df[name_col].astype(str),
            "expected_relative_abundance": df[abundance_col] if abundance_col else None,
            "expected_group": df[group_col] if group_col else None,
            "notes": df[notes_col] if notes_col else None,
            "source_file": str(path),
        }
    )
    duplicates = normalized["expected_id"][normalized["expected_id"].duplicated()].unique().tolist()
    if duplicates:
        raise ValueError(f"Duplicate expected IDs found: {', '.join(map(str, duplicates))}")
    return normalized[EXPECTED_COLUMNS]


def normalize_observed_table(path: str | Path, method: str):
    df = safe_read_table(path)
    pd = _pandas()
    if df is None:
        return pd.DataFrame(columns=OBSERVED_COLUMNS)
    columns = list(df.columns)

    if method == "pbmm2_mapping":
        id_col = _first_present(columns, ["reference_id"])
        signal_col = _first_present(columns, ["relative_mapping_signal"])
        raw_col = _first_present(columns, ["read_count"])
        if not id_col or not signal_col:
            raise ValueError("pbmm2 observed table must include reference_id and relative_mapping_signal")
        normalized = pd.DataFrame(
            {
                "method": method,
                "observed_id": df[id_col].astype(str),
                "observed_name": df[id_col].astype(str),
                "observed_signal": df[signal_col],
                "raw_count": df[raw_col] if raw_col else None,
                "source_file": str(path),
            }
        )
        return normalized[OBSERVED_COLUMNS]

    if method == "emu_abundance":
        id_col = _first_present(columns, ["tax_id", "taxid", "species", "genus"])
        name_col = _first_present(columns, ["species", "taxon", "genus", "tax_id", "taxid"])
        signal_col = _first_present(columns, ["abundance", "estimated_abundance", "relative_abundance"])
        if not id_col or not name_col or not signal_col:
            raise ValueError("Emu observed table must include tax_id/species/genus and an abundance column")
        normalized = pd.DataFrame(
            {
                "method": method,
                "observed_id": df[id_col].astype(str),
                "observed_name": df[name_col].astype(str),
                "observed_signal": df[signal_col],
                "raw_count": None,
                "source_file": str(path),
            }
        )
        return normalized[OBSERVED_COLUMNS]

    if method == "comparison":
        required = {"method", "feature_id", "taxon", "count_or_signal", "source_file"}
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(f"comparison summary missing columns: {', '.join(sorted(missing))}")
        raw_col = "raw_count" if "raw_count" in df.columns else None
        normalized = pd.DataFrame(
            {
                "method": df["method"].astype(str),
                "observed_id": df["feature_id"].astype(str),
                "observed_name": df["taxon"].astype(str),
                "observed_signal": df["count_or_signal"],
                "raw_count": df[raw_col] if raw_col else None,
                "source_file": df["source_file"].astype(str),
            }
        )
        return normalized[OBSERVED_COLUMNS]

    if method == "mothur":
        id_col = _first_present(columns, ["feature_id", "taxon", "taxonomy", "name", columns[0]])
        name_col = _first_present(columns, ["taxon", "taxonomy", "name", id_col or columns[0]])
        signal_col = _first_present(columns, ["count", "abundance", "read_count", "count_or_signal"])
        normalized = pd.DataFrame(
            {
                "method": method,
                "observed_id": df[id_col].astype(str) if id_col else None,
                "observed_name": df[name_col].astype(str) if name_col else None,
                "observed_signal": df[signal_col] if signal_col else None,
                "raw_count": df[signal_col] if signal_col else None,
                "source_file": str(path),
            }
        )
        return normalized[OBSERVED_COLUMNS]

    raise ValueError(f"Unsupported observed method: {method}")


def _norm(value: Any) -> str:
    return str(value).strip().lower()


def _matches(expected_id: str, expected_name: str, observed_id: str, observed_name: str, match_mode: str) -> bool:
    pairs = [(expected_id, observed_id), (expected_id, observed_name), (expected_name, observed_id), (expected_name, observed_name)]
    if match_mode == "case_insensitive_exact":
        return any(_norm(left) == _norm(right) for left, right in pairs)
    if match_mode == "exact":
        return any(str(left).strip() == str(right).strip() for left, right in pairs)
    if match_mode == "substring":
        return any(_norm(left) in _norm(right) or _norm(right) in _norm(left) for left, right in pairs if _norm(left) and _norm(right))
    raise ValueError(f"Unsupported match_mode: {match_mode}")


def match_expected_to_observed(expected_df, observed_df, match_mode: str = "case_insensitive_exact"):
    pd = _pandas()
    rows = []
    methods = sorted(observed_df["method"].dropna().unique().tolist()) if observed_df is not None and not observed_df.empty else ["observed"]
    for method in methods:
        method_observed = observed_df[observed_df["method"] == method] if observed_df is not None and not observed_df.empty else pd.DataFrame(columns=OBSERVED_COLUMNS)
        for expected in expected_df.itertuples(index=False):
            match = None
            for observed in method_observed.itertuples(index=False):
                if _matches(expected.expected_id, expected.expected_name, observed.observed_id, observed.observed_name, match_mode):
                    match = observed
                    break
            rows.append(
                {
                    "expected_id": expected.expected_id,
                    "expected_name": expected.expected_name,
                    "method": method,
                    "matched": match is not None,
                    "matched_observed_id": getattr(match, "observed_id", None) if match else None,
                    "matched_observed_name": getattr(match, "observed_name", None) if match else None,
                    "observed_signal": getattr(match, "observed_signal", None) if match else None,
                    "raw_count": getattr(match, "raw_count", None) if match else None,
                    "match_mode": match_mode,
                }
            )
    return pd.DataFrame(rows, columns=RECOVERY_COLUMNS)


def detect_unexpected_observed(expected_df, observed_df, match_mode: str = "case_insensitive_exact"):
    pd = _pandas()
    columns = ["method", "observed_id", "observed_name", "observed_signal", "raw_count", "reason", "source_file"]
    if observed_df is None or observed_df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for observed in observed_df.itertuples(index=False):
        matched = any(
            _matches(expected.expected_id, expected.expected_name, observed.observed_id, observed.observed_name, match_mode)
            for expected in expected_df.itertuples(index=False)
        )
        if not matched:
            rows.append(
                {
                    "method": observed.method,
                    "observed_id": observed.observed_id,
                    "observed_name": observed.observed_name,
                    "observed_signal": observed.observed_signal,
                    "raw_count": observed.raw_count,
                    "reason": "observed_not_in_expected_table",
                    "source_file": observed.source_file,
                }
            )
    return pd.DataFrame(rows, columns=columns)


def write_expected_taxa_recovery(recovery_df, output_tsv: str | Path) -> None:
    Path(output_tsv).parent.mkdir(parents=True, exist_ok=True)
    recovery_df.to_csv(output_tsv, sep="\t", index=False)


def write_missing_expected_taxa(recovery_df, output_tsv: str | Path) -> None:
    Path(output_tsv).parent.mkdir(parents=True, exist_ok=True)
    recovery_df[~recovery_df["matched"]].to_csv(output_tsv, sep="\t", index=False)


def write_unexpected_taxa(unexpected_df, output_tsv: str | Path) -> None:
    Path(output_tsv).parent.mkdir(parents=True, exist_ok=True)
    unexpected_df.to_csv(output_tsv, sep="\t", index=False)


def build_method_validation_summary(expected_df, observed_df, recovery_df, unexpected_df):
    pd = _pandas()
    methods = sorted(set(recovery_df["method"].dropna().tolist()) | set(unexpected_df["method"].dropna().tolist()))
    rows = []
    expected_count = len(expected_df)
    for method in methods:
        method_recovery = recovery_df[recovery_df["method"] == method]
        method_observed = observed_df[observed_df["method"] == method] if observed_df is not None and not observed_df.empty else pd.DataFrame()
        method_unexpected = unexpected_df[unexpected_df["method"] == method] if not unexpected_df.empty else pd.DataFrame()
        matched_count = int(method_recovery["matched"].sum()) if not method_recovery.empty else 0
        missing_count = expected_count - matched_count
        recovery_fraction = matched_count / expected_count if expected_count else None
        rows.append(
            {
                "method": method,
                "expected_taxa_count": expected_count,
                "observed_features_count": len(method_observed),
                "matched_expected_count": matched_count,
                "missing_expected_count": missing_count,
                "unexpected_observed_count": len(method_unexpected),
                "recovery_fraction": recovery_fraction,
                "notes": "Descriptive recovery against user-provided expected table; not a universal sensitivity estimate.",
            }
        )
    return pd.DataFrame(rows)


def write_method_validation_summary(summary_df, output_tsv: str | Path) -> None:
    Path(output_tsv).parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(output_tsv, sep="\t", index=False)


def write_validation_interpretation_checklist(output_md: str | Path) -> None:
    Path(output_md).parent.mkdir(parents=True, exist_ok=True)
    Path(output_md).write_text(
        "# Validation Interpretation Checklist\n\n"
        "- Validation is against a user-provided expected taxa/reference table.\n"
        "- Recovery does not prove biological truth.\n"
        "- Missing expected taxa may reflect sequencing depth, primer bias, database mismatch, thresholding, or method limitations.\n"
        "- Unexpected taxa are not automatically false positives; they may reflect contamination, barcode bleed-through, database ambiguity, multi-mapping, classification artifacts, or true unexpected signal.\n"
        "- pbmm2_mapping reports mapping-derived relative signal, not absolute abundance.\n"
        "- Emu estimates relative abundance for full-length 16S-compatible input.\n"
        "- mothur results depend on selected filtering and classification parameters.\n"
        "- For 16S-ITS-23S constructs, Emu input compatibility must be verified.\n"
    )


def write_validation_manifest(
    output_json: str | Path,
    expected_taxa_file: str,
    observed_files: list[str],
    match_mode: str,
    outputs_written: dict[str, str],
) -> None:
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).write_text(
        json.dumps(
            {
                "version": "1.5.0",
                "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "expected_taxa_file": expected_taxa_file,
                "observed_files": observed_files,
                "match_mode": match_mode,
                "outputs_written": outputs_written,
                "limitations": [
                    "Validation is descriptive against a user-provided expected table.",
                    "Unexpected taxa are not automatically false positives.",
                    "Missing expected taxa are not automatically false negatives.",
                ],
            },
            indent=2,
        )
        + "\n"
    )


def _load_observed_from_config(validation: dict[str, Any]):
    pd = _pandas()
    observed_cfg = validation.get("observed", {}) or {}
    tables = []
    observed_files = []
    comparison = observed_cfg.get("comparison_summary")
    if comparison and Path(comparison).is_file():
        tables.append(normalize_observed_table(comparison, "comparison"))
        observed_files.append(str(comparison))
    else:
        pbmm2_glob = observed_cfg.get("pbmm2_reference_counts_glob", "")
        for path in sorted(glob(str(pbmm2_glob))) if pbmm2_glob else []:
            tables.append(normalize_observed_table(path, "pbmm2_mapping"))
            observed_files.append(path)
        emu = observed_cfg.get("emu_abundance_file")
        if emu and Path(emu).is_file():
            tables.append(normalize_observed_table(emu, "emu_abundance"))
            observed_files.append(str(emu))
        mothur = observed_cfg.get("mothur_taxonomy_file")
        if mothur and Path(mothur).is_file():
            tables.append(normalize_observed_table(mothur, "mothur"))
            observed_files.append(str(mothur))
    observed_df = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame(columns=OBSERVED_COLUMNS)
    return observed_df, observed_files


def run_validation_from_config(config: dict[str, Any], force: bool = False) -> dict[str, Any]:
    validation = config.get("validation", {})
    if not isinstance(validation, dict):
        raise ValueError("validation configuration must be a mapping")
    if not force and not bool(validation.get("enabled", False)):
        return {"mode": "validation", "enabled": False, "outputs": {}}
    output_dir = Path(str(validation.get("output_dir", "results/validation")))
    output_dir.mkdir(parents=True, exist_ok=True)
    expected_file = str(validation.get("expected_taxa_file", "config/expected_taxa.example.tsv"))
    match_mode = str(validation.get("match_mode", "case_insensitive_exact"))
    outputs_cfg = validation.get("outputs", {}) or {}
    expected_df = load_expected_taxa(expected_file)
    observed_df, observed_files = _load_observed_from_config(validation)
    recovery_df = match_expected_to_observed(expected_df, observed_df, match_mode=match_mode)
    unexpected_df = detect_unexpected_observed(expected_df, observed_df, match_mode=match_mode)
    summary_df = build_method_validation_summary(expected_df, observed_df, recovery_df, unexpected_df)
    outputs_written: dict[str, str] = {}
    if outputs_cfg.get("expected_taxa_recovery", True):
        path = output_dir / "expected_taxa_recovery.tsv"
        write_expected_taxa_recovery(recovery_df, path)
        outputs_written["expected_taxa_recovery"] = str(path)
    if outputs_cfg.get("missing_expected_taxa", True):
        path = output_dir / "missing_expected_taxa.tsv"
        write_missing_expected_taxa(recovery_df, path)
        outputs_written["missing_expected_taxa"] = str(path)
    if outputs_cfg.get("unexpected_taxa", True):
        path = output_dir / "unexpected_taxa.tsv"
        write_unexpected_taxa(unexpected_df, path)
        outputs_written["unexpected_taxa"] = str(path)
    if outputs_cfg.get("method_validation_summary", True):
        path = output_dir / "method_validation_summary.tsv"
        write_method_validation_summary(summary_df, path)
        outputs_written["method_validation_summary"] = str(path)
    if outputs_cfg.get("interpretation_checklist", True):
        path = output_dir / "validation_interpretation_checklist.md"
        write_validation_interpretation_checklist(path)
        outputs_written["interpretation_checklist"] = str(path)
    if outputs_cfg.get("validation_manifest", True):
        path = output_dir / "validation_manifest.json"
        write_validation_manifest(path, expected_file, observed_files, match_mode, outputs_written)
        outputs_written["validation_manifest"] = str(path)
    return {"mode": "validation", "enabled": True, "outputs": outputs_written}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("Build validation report from YAML config")
    parser.add_argument("--config", required=True, help="Project YAML config.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    run_validation_from_config(load_config(args.config), force=True)
