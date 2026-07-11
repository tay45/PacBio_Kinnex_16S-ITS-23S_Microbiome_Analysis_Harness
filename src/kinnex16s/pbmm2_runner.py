"""pbmm2 reference-guided alignment and filtered mapping QC."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .commands import run_command
from .validators import resolve_tool

VALID_MULTIMAPPER_POLICIES = {"best_hit"}


def build_pbmm2_index_command(
    reference_fasta: str,
    reference_index: str,
    threads: int,
    pbmm2_path: str = "pbmm2",
) -> list[str]:
    return [
        pbmm2_path,
        "index",
        reference_fasta,
        reference_index,
        "--num-threads",
        str(threads),
    ]


def build_pbmm2_align_command(
    reference_index: str,
    input_bam: str,
    output_bam: str,
    preset: str = "CCS",
    threads: int = 16,
    pbmm2_path: str = "pbmm2",
) -> list[str]:
    return [
        pbmm2_path,
        "align",
        reference_index,
        input_bam,
        output_bam,
        "--preset",
        preset,
        "--sort",
        "--num-threads",
        str(threads),
    ]


def build_samtools_index_command(output_bam: str, samtools_path: str = "samtools") -> list[str]:
    return [samtools_path, "index", output_bam]


def _aligned_query_length(read: Any) -> int | None:
    value = getattr(read, "query_alignment_length", None)
    if value is not None:
        return int(value)
    start = getattr(read, "query_alignment_start", None)
    end = getattr(read, "query_alignment_end", None)
    if start is not None and end is not None and end >= start:
        return int(end - start)
    return None


def calculate_alignment_identity(read: Any) -> float | None:
    aligned_length = _aligned_query_length(read)
    if not aligned_length:
        return None
    try:
        nm = read.get_tag("NM")
    except (KeyError, AttributeError):
        return None
    if nm is None:
        return None
    return 1 - (float(nm) / float(aligned_length))


def calculate_query_coverage(read: Any) -> float | None:
    aligned_length = _aligned_query_length(read)
    query_length = getattr(read, "query_length", None)
    if query_length is None and hasattr(read, "infer_query_length"):
        query_length = read.infer_query_length()
    if not aligned_length or not query_length:
        return None
    return float(aligned_length) / float(query_length)


def get_alignment_length(read: Any) -> int | None:
    return _aligned_query_length(read)


def read_passes_mapping_filters(
    read: Any,
    min_mapq: int = 20,
    min_identity: float | None = 0.97,
    min_query_coverage: float | None = 0.90,
    min_alignment_length: int | None = 1000,
    primary_only: bool = True,
) -> bool:
    return _mapping_filter_failure(
        read,
        min_mapq=min_mapq,
        min_identity=min_identity,
        min_query_coverage=min_query_coverage,
        min_alignment_length=min_alignment_length,
        primary_only=primary_only,
    ) is None


def _mapping_filter_failure(
    read: Any,
    min_mapq: int = 20,
    min_identity: float | None = 0.97,
    min_query_coverage: float | None = 0.90,
    min_alignment_length: int | None = 1000,
    primary_only: bool = True,
) -> str | None:
    if getattr(read, "is_unmapped", False):
        return "unmapped"
    if primary_only and getattr(read, "is_secondary", False):
        return "secondary"
    if primary_only and getattr(read, "is_supplementary", False):
        return "supplementary"
    if getattr(read, "mapping_quality", 0) < min_mapq:
        return "low_mapq"

    identity = calculate_alignment_identity(read)
    if min_identity is not None and (identity is None or identity < min_identity):
        return "failed_identity"

    coverage = calculate_query_coverage(read)
    if min_query_coverage is not None and (coverage is None or coverage < min_query_coverage):
        return "failed_query_coverage"

    alignment_length = get_alignment_length(read)
    if min_alignment_length is not None and (
        alignment_length is None or alignment_length < min_alignment_length
    ):
        return "failed_alignment_length"

    return None


def _read_reference_name(read: Any, bam: Any) -> str:
    reference_name = getattr(read, "reference_name", None)
    if reference_name:
        return str(reference_name)
    reference_id = getattr(read, "reference_id", None)
    if reference_id is not None and hasattr(bam, "get_reference_name"):
        return str(bam.get_reference_name(reference_id))
    return "unknown_reference"


def _candidate_sort_key(candidate: dict[str, Any]) -> tuple[float, float, float, int]:
    return (
        float(candidate["mapq"]),
        float(candidate["identity"] or 0),
        float(candidate["query_coverage"] or 0),
        int(candidate["alignment_length"] or 0),
    )


def summarize_filtered_mappings(
    bam_path: str,
    reference_counts_tsv: str,
    mapping_qc_tsv: str,
    filtered_assignments_tsv: str | None = None,
    unmapped_read_ids_txt: str | None = None,
    sample_name: str | None = None,
    min_mapq: int = 20,
    min_identity: float | None = 0.97,
    min_query_coverage: float | None = 0.90,
    min_alignment_length: int | None = 1000,
    primary_only: bool = True,
    multimapper_policy: str = "best_hit",
) -> dict[str, Any]:
    if multimapper_policy not in VALID_MULTIMAPPER_POLICIES:
        raise ValueError(
            f"Invalid multimapper_policy '{multimapper_policy}'. Supported policies: best_hit"
        )

    try:
        import pysam  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "pysam is required for pbmm2 filtered mapping QC. Install pysam or run in an environment that includes it."
        ) from exc

    qc = {
        "total_records_seen": 0,
        "unmapped_records": 0,
        "secondary_records": 0,
        "supplementary_records": 0,
        "low_mapq_records": 0,
        "failed_identity_records": 0,
        "failed_query_coverage_records": 0,
        "failed_alignment_length_records": 0,
        "mapped_primary_records_passing_filter": 0,
        "number_of_references_detected": 0,
    }
    candidates_by_read: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unmapped_read_ids: list[str] = []

    with pysam.AlignmentFile(bam_path, "rb") as bam:
        for read in bam:
            qc["total_records_seen"] += 1
            read_id = str(getattr(read, "query_name", "unknown_read"))
            failure = _mapping_filter_failure(
                read,
                min_mapq=min_mapq,
                min_identity=min_identity,
                min_query_coverage=min_query_coverage,
                min_alignment_length=min_alignment_length,
                primary_only=primary_only,
            )
            if failure:
                if failure == "unmapped":
                    qc["unmapped_records"] += 1
                    unmapped_read_ids.append(read_id)
                elif failure == "secondary":
                    qc["secondary_records"] += 1
                elif failure == "supplementary":
                    qc["supplementary_records"] += 1
                elif failure == "low_mapq":
                    qc["low_mapq_records"] += 1
                elif failure == "failed_identity":
                    qc["failed_identity_records"] += 1
                elif failure == "failed_query_coverage":
                    qc["failed_query_coverage_records"] += 1
                elif failure == "failed_alignment_length":
                    qc["failed_alignment_length_records"] += 1
                continue

            candidate = {
                "read_id": read_id,
                "reference_id": _read_reference_name(read, bam),
                "mapq": int(getattr(read, "mapping_quality", 0)),
                "identity": calculate_alignment_identity(read),
                "query_coverage": calculate_query_coverage(read),
                "alignment_length": get_alignment_length(read),
            }
            candidates_by_read[read_id].append(candidate)

    selected_assignments = [
        sorted(candidates, key=_candidate_sort_key, reverse=True)[0]
        for candidates in candidates_by_read.values()
        if candidates
    ]
    qc["mapped_primary_records_passing_filter"] = len(selected_assignments)

    reference_counts: dict[str, int] = defaultdict(int)
    for assignment in selected_assignments:
        reference_counts[assignment["reference_id"]] += 1
    qc["number_of_references_detected"] = len(reference_counts)

    total_passing = sum(reference_counts.values())
    Path(reference_counts_tsv).parent.mkdir(parents=True, exist_ok=True)
    with Path(reference_counts_tsv).open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["reference_id", "read_count", "relative_mapping_signal"],
            delimiter="\t",
        )
        writer.writeheader()
        for reference_id in sorted(reference_counts):
            read_count = reference_counts[reference_id]
            relative_signal = read_count / total_passing if total_passing else 0
            writer.writerow(
                {
                    "reference_id": reference_id,
                    "read_count": read_count,
                    "relative_mapping_signal": f"{relative_signal:.6f}",
                }
            )

    Path(mapping_qc_tsv).parent.mkdir(parents=True, exist_ok=True)
    with Path(mapping_qc_tsv).open("w", newline="") as handle:
        fieldnames = [
            "sample_name",
            "total_records_seen",
            "unmapped_records",
            "secondary_records",
            "supplementary_records",
            "low_mapq_records",
            "failed_identity_records",
            "failed_query_coverage_records",
            "failed_alignment_length_records",
            "mapped_primary_records_passing_filter",
            "number_of_references_detected",
            "min_mapq",
            "min_identity",
            "min_query_coverage",
            "min_alignment_length",
            "primary_only",
            "multimapper_policy",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerow(
            {
                "sample_name": sample_name or Path(bam_path).stem,
                **qc,
                "min_mapq": min_mapq,
                "min_identity": min_identity,
                "min_query_coverage": min_query_coverage,
                "min_alignment_length": min_alignment_length,
                "primary_only": primary_only,
                "multimapper_policy": multimapper_policy,
            }
        )

    if filtered_assignments_tsv:
        Path(filtered_assignments_tsv).parent.mkdir(parents=True, exist_ok=True)
        with Path(filtered_assignments_tsv).open("w", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "read_id",
                    "reference_id",
                    "mapq",
                    "identity",
                    "query_coverage",
                    "alignment_length",
                ],
                delimiter="\t",
            )
            writer.writeheader()
            for assignment in sorted(selected_assignments, key=lambda item: item["read_id"]):
                writer.writerow(
                    {
                        **assignment,
                        "identity": f"{assignment['identity']:.6f}",
                        "query_coverage": f"{assignment['query_coverage']:.6f}",
                    }
                )

    if unmapped_read_ids_txt:
        Path(unmapped_read_ids_txt).parent.mkdir(parents=True, exist_ok=True)
        Path(unmapped_read_ids_txt).write_text("\n".join(unmapped_read_ids) + ("\n" if unmapped_read_ids else ""))

    return {
        "reference_counts": dict(reference_counts),
        "qc": qc,
        "selected_assignments": selected_assignments,
        "unmapped_read_ids": unmapped_read_ids,
    }


def validate_pbmm2_config(config: dict[str, Any]) -> dict[str, Any]:
    pbmm2 = config.get("pbmm2_mapping", {})
    if not isinstance(pbmm2, dict):
        raise ValueError("pbmm2_mapping configuration must be a mapping")
    required = ["reference_fasta", "reference_index", "output_dir"]
    missing = [key for key in required if not pbmm2.get(key)]
    if missing:
        raise ValueError(f"Missing required pbmm2 config field(s): {', '.join(missing)}")
    threads = int(pbmm2.get("threads", 16))
    if threads < 1:
        raise ValueError("pbmm2_mapping.threads must be >= 1")
    filters = pbmm2.get("filters", {}) or {}
    outputs = pbmm2.get("outputs", {}) or {}
    multimapper_policy = str(filters.get("multimapper_policy", "best_hit"))
    if multimapper_policy not in VALID_MULTIMAPPER_POLICIES:
        raise ValueError(
            f"Invalid multimapper_policy '{multimapper_policy}'. Supported policies: best_hit"
        )
    return {
        "enabled": bool(pbmm2.get("enabled", False)),
        "pbmm2_path": str(pbmm2.get("pbmm2_path", "pbmm2")),
        "samtools_path": str(pbmm2.get("samtools_path", "samtools")),
        "input_bam_dir": str(pbmm2.get("input_bam_dir", "results/preprocess")),
        "input_bams": list(pbmm2.get("input_bams", []) or []),
        "reference_fasta": str(pbmm2["reference_fasta"]),
        "reference_index": str(pbmm2["reference_index"]),
        "index_reference": bool(pbmm2.get("index_reference", True)),
        "output_dir": str(pbmm2["output_dir"]),
        "preset": str(pbmm2.get("preset", "CCS")),
        "threads": threads,
        "filters": {
            "primary_only": bool(filters.get("primary_only", True)),
            "min_mapq": int(filters.get("min_mapq", 20)),
            "min_identity": float(filters.get("min_identity", 0.97)) if filters.get("min_identity", 0.97) is not None else None,
            "min_query_coverage": float(filters.get("min_query_coverage", 0.90)) if filters.get("min_query_coverage", 0.90) is not None else None,
            "min_alignment_length": int(filters.get("min_alignment_length", 1000)) if filters.get("min_alignment_length", 1000) is not None else None,
            "multimapper_policy": multimapper_policy,
        },
        "outputs": {
            "sorted_bam": bool(outputs.get("sorted_bam", True)),
            "bam_index": bool(outputs.get("bam_index", True)),
            "reference_counts": bool(outputs.get("reference_counts", True)),
            "relative_abundance": bool(outputs.get("relative_abundance", True)),
            "mapping_qc": bool(outputs.get("mapping_qc", True)),
            "filtered_assignments": bool(outputs.get("filtered_assignments", True)),
            "unmapped_read_ids": bool(outputs.get("unmapped_read_ids", True)),
        },
    }


def discover_input_bams(input_bam_dir: str) -> list[str]:
    return sorted(str(path) for path in Path(input_bam_dir).glob("*.bam") if path.is_file())


def sample_name_from_bam(input_bam: str) -> str:
    name = Path(input_bam).name
    return name[:-4] if name.endswith(".bam") else Path(input_bam).stem


def write_pbmm2_manifest(settings: dict[str, Any], results: list[dict[str, Any]]) -> Path:
    output_dir = Path(settings["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "runner": "pbmm2_mapping",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "reference_fasta": settings["reference_fasta"],
        "reference_index": settings["reference_index"],
        "preset": settings["preset"],
        "filters": settings["filters"],
        "samples": results,
        "notes": (
            "pbmm2 mode performs reference-guided alignment and filtered mapping QC. "
            "Reference-count summaries report mapping-derived relative signal, not absolute abundance."
        ),
    }
    manifest_path = output_dir / "pbmm2_mapping_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest_path


def run_pbmm2_mapping_from_config(config: dict[str, Any]) -> dict[str, Any]:
    settings = validate_pbmm2_config(config)
    Path(settings["output_dir"]).mkdir(parents=True, exist_ok=True)
    pbmm2_path = resolve_tool("pbmm2", settings["pbmm2_path"])
    samtools_path = resolve_tool("samtools", settings["samtools_path"])

    index_command = None
    if settings["index_reference"]:
        index_command = build_pbmm2_index_command(
            settings["reference_fasta"],
            settings["reference_index"],
            settings["threads"],
            pbmm2_path=pbmm2_path,
        )
        run_command(index_command, "pbmm2 reference indexing")
    elif not Path(settings["reference_index"]).is_file():
        raise FileNotFoundError(
            f"pbmm2 reference index not found and index_reference is false: {settings['reference_index']}"
        )

    input_bams = settings["input_bams"] or discover_input_bams(settings["input_bam_dir"])
    if not input_bams:
        raise FileNotFoundError(
            f"No input BAM files found for pbmm2_mapping in {settings['input_bam_dir']}"
        )

    sample_results: list[dict[str, Any]] = []
    for input_bam in input_bams:
        sample_name = sample_name_from_bam(input_bam)
        sample_dir = Path(settings["output_dir"]) / sample_name
        sample_dir.mkdir(parents=True, exist_ok=True)
        output_bam = sample_dir / f"{sample_name}.pbmm2.sorted.bam"
        align_command = build_pbmm2_align_command(
            settings["reference_index"],
            input_bam,
            str(output_bam),
            preset=settings["preset"],
            threads=settings["threads"],
            pbmm2_path=pbmm2_path,
        )
        run_command(align_command, f"pbmm2 reference-guided mapping for {sample_name}")

        index_bam_command = None
        if settings["outputs"]["bam_index"]:
            index_bam_command = build_samtools_index_command(str(output_bam), samtools_path=samtools_path)
            run_command(index_bam_command, f"samtools index for {sample_name}")

        reference_counts_tsv = sample_dir / f"{sample_name}.reference_counts.tsv"
        mapping_qc_tsv = sample_dir / f"{sample_name}.mapping_qc.tsv"
        filtered_assignments_tsv = (
            sample_dir / f"{sample_name}.filtered_assignments.tsv"
            if settings["outputs"]["filtered_assignments"]
            else None
        )
        unmapped_read_ids_txt = (
            sample_dir / f"{sample_name}.unmapped_read_ids.txt"
            if settings["outputs"]["unmapped_read_ids"]
            else None
        )
        summary = summarize_filtered_mappings(
            str(output_bam),
            str(reference_counts_tsv),
            str(mapping_qc_tsv),
            str(filtered_assignments_tsv) if filtered_assignments_tsv else None,
            str(unmapped_read_ids_txt) if unmapped_read_ids_txt else None,
            sample_name=sample_name,
            **settings["filters"],
        )
        sample_results.append(
            {
                "sample_name": sample_name,
                "input_bam": input_bam,
                "output_bam": str(output_bam),
                "align_command": align_command,
                "index_command": index_bam_command,
                "reference_counts_tsv": str(reference_counts_tsv),
                "mapping_qc_tsv": str(mapping_qc_tsv),
                "filtered_assignments_tsv": str(filtered_assignments_tsv) if filtered_assignments_tsv else None,
                "unmapped_read_ids_txt": str(unmapped_read_ids_txt) if unmapped_read_ids_txt else None,
                "qc": summary["qc"],
            }
        )

    manifest_path = write_pbmm2_manifest(settings, sample_results)
    return {
        "mode": "pbmm2_mapping",
        "index_command": index_command,
        "samples": sample_results,
        "manifest": str(manifest_path),
    }
