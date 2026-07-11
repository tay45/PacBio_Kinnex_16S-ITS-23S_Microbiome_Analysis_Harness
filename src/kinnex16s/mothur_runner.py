"""mothur-based sequence filtering and taxonomy classification."""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .commands import build_mothur_command, run_command
from .validators import require_files, resolve_tool


def setup_logging(log_file: str | Path) -> None:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.handlers.clear()
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )


def _run_mothur(mothur: str, expression: str, label: str) -> None:
    run_command(build_mothur_command(mothur, expression), f"mothur {label}")


def _mothur_value(value: Any) -> str:
    if isinstance(value, bool):
        return "T" if value else "F"
    return str(value)


def build_mothur_expression(command: str, **params: Any) -> str:
    rendered = [
        f"{key}={_mothur_value(value)}"
        for key, value in params.items()
        if value is not None
    ]
    return f"{command}({', '.join(rendered)})"


def expected_with_tag(path: str, tag: str, suffix: str = ".fasta") -> str:
    # Assumes mothur's common pattern: input basename + command tag + output suffix,
    # e.g. align.seqs -> *.align.fasta, filter.seqs -> *.filter.fasta,
    # pre.cluster -> *.precluster.fasta.
    return f"{Path(path).with_suffix('')}.{tag}{suffix}"


def expected_screen_outputs(fasta: str, group: str | None = None) -> tuple[str, str | None]:
    # screen.seqs convention used by the direct and YAML routes:
    # *.good.fasta and, when a group file is supplied, *.good.groups.
    good_fasta = expected_with_tag(fasta, "good")
    good_group = expected_with_tag(group, "good", ".groups") if group else None
    return good_fasta, good_group


def build_summary_seqs_expression(fasta: str, processors: int) -> str:
    return build_mothur_expression("summary.seqs", fasta=fasta, processors=processors)


def build_screen_length_expression(
    fasta: str,
    group: str | None,
    count: str | None,
    min_length: int,
    max_length: int,
    maxambig: int | None,
    maxhomop: int | None,
    processors: int,
) -> str:
    return build_mothur_expression(
        "screen.seqs",
        fasta=fasta,
        group=group,
        count=count,
        minlength=min_length,
        maxlength=max_length,
        maxambig=maxambig,
        maxhomop=maxhomop,
        processors=processors,
    )


def build_unique_seqs_expression(fasta: str) -> str:
    return build_mothur_expression("unique.seqs", fasta=fasta)


def build_align_seqs_expression(fasta: str, reference_fasta: str, processors: int) -> str:
    return build_mothur_expression(
        "align.seqs",
        fasta=fasta,
        reference=reference_fasta,
        processors=processors,
    )


def build_screen_alignment_expression(
    fasta: str,
    group: str | None,
    count: str | None,
    start: int | None,
    end: int | None,
    maxhomop: int | None,
    processors: int,
) -> str:
    return build_mothur_expression(
        "screen.seqs",
        fasta=fasta,
        group=group,
        count=count,
        start=start,
        end=end,
        maxhomop=maxhomop,
        processors=processors,
    )


def build_filter_seqs_expression(fasta: str, vertical: bool, trump: str, processors: int) -> str:
    return build_mothur_expression(
        "filter.seqs",
        fasta=fasta,
        vertical=vertical,
        trump=trump,
        processors=processors,
    )


def build_precluster_expression(
    fasta: str,
    name: str | None,
    count: str | None,
    diffs: int | None,
    diffs_per_100bp: int | None,
    processors: int,
) -> str:
    return build_mothur_expression(
        "pre.cluster",
        fasta=fasta,
        name=name,
        count=count,
        diffs=diffs,
        diffs_per_100bp=diffs_per_100bp,
        processors=processors,
    )


def build_chimera_vsearch_expression(
    fasta: str,
    name: str | None,
    count: str | None,
    dereplicate: bool,
    processors: int,
) -> str:
    return build_mothur_expression(
        "chimera.vsearch",
        fasta=fasta,
        name=name,
        count=count,
        dereplicate=dereplicate,
        processors=processors,
    )


def build_classify_seqs_expression(
    fasta: str,
    group: str | None,
    count: str | None,
    reference: str,
    taxonomy: str,
    method: str,
    numwanted: int,
    search: str,
    cutoff: int | None,
    processors: int,
) -> str:
    return build_mothur_expression(
        "classify.seqs",
        fasta=fasta,
        group=group,
        count=count,
        reference=reference,
        taxonomy=taxonomy,
        method=method,
        numwanted=numwanted,
        search=search,
        cutoff=cutoff,
        processors=processors,
    )


def build_remove_lineage_expression(
    fasta: str,
    taxonomy: str,
    group: str | None,
    count: str | None,
    taxon: str,
) -> str:
    return build_mothur_expression(
        "remove.lineage",
        fasta=fasta,
        taxonomy=taxonomy,
        group=group,
        count=count,
        taxon=taxon,
    )


def build_make_shared_expression(list_file: str, group: str | None, count: str | None, label: str) -> str:
    return build_mothur_expression("make.shared", list=list_file, group=group, count=count, label=label)


def build_classify_otu_expression(list_file: str, taxonomy: str, label: str) -> str:
    return build_mothur_expression("classify.otu", list=list_file, taxonomy=taxonomy, label=label)


def summary_seqs(mothur: str, fasta: str, processors: int) -> None:
    _run_mothur(mothur, build_summary_seqs_expression(fasta, processors), "summary.seqs")


def screen_seqs(
    mothur: str,
    fasta: str,
    group: str,
    min_length: int,
    max_length: int,
    processors: int,
) -> tuple[str, str]:
    _run_mothur(
        mothur,
        build_screen_length_expression(
            fasta=fasta,
            group=group,
            count=None,
            min_length=min_length,
            max_length=max_length,
            maxambig=0,
            maxhomop=None,
            processors=processors,
        ),
        "screen.seqs",
    )
    good_fasta, good_group = expected_screen_outputs(fasta, group)
    require_files([good_fasta, good_group], "screen.seqs output")
    return good_fasta, str(good_group)


def classify_seqs(
    mothur: str,
    fasta: str,
    group: str,
    reference: str,
    taxonomy: str,
    method: str,
    numwanted: int,
    search: str,
    processors: int,
) -> str:
    _run_mothur(
        mothur,
        build_classify_seqs_expression(
            fasta=fasta,
            group=group,
            count=None,
            reference=reference,
            taxonomy=taxonomy,
            method=method,
            numwanted=numwanted,
            search=search,
            cutoff=None,
            processors=processors,
        ),
        "classify.seqs",
    )
    taxonomy_out = f"{Path(fasta).with_suffix('')}.{Path(taxonomy).stem}.{method}.taxonomy"
    require_files([taxonomy_out], "classify.seqs output")
    return taxonomy_out


def build_taxon_arg(lineage_exclude: str) -> str:
    path = Path(lineage_exclude)
    if not path.is_file():
        return lineage_exclude
    taxa = [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not taxa:
        raise ValueError(f"Lineage exclude file is empty: {lineage_exclude}")
    return "-".join(taxa)


def remove_lineage(mothur: str, fasta: str, taxonomy: str, lineage_exclude: str) -> None:
    taxon_arg = build_taxon_arg(lineage_exclude)
    _run_mothur(
        mothur,
        build_remove_lineage_expression(
            fasta=fasta,
            taxonomy=taxonomy,
            group=None,
            count=None,
            taxon=taxon_arg,
        ),
        "remove.lineage",
    )


@dataclass
class MothurState:
    fasta: str
    group: str | None
    count: str | None = None
    name: str | None = None
    taxonomy: str | None = None
    list_file: str | None = None


def _require_existing(paths: list[str | None], label: str) -> None:
    require_files([path for path in paths if path], label)


def _ensure_output(path: str | None, step: str) -> None:
    if path and not Path(path).is_file():
        raise FileNotFoundError(
            f"Expected mothur output for {step} was not found: {path}. "
            "The harness assumes mothur's standard output naming; check the step log "
            "or adjust the runner if your mothur version names this file differently."
        )


def default_mothur_steps(config: dict[str, Any]) -> dict[str, bool]:
    steps = {
        "summary": True,
        "screen_length": True,
        "unique": False,
        "align": False,
        "screen_alignment": False,
        "filter_alignment": False,
        "precluster": False,
        "chimera_vsearch": False,
        "classify": True,
        "remove_lineage": False,
        "make_shared": False,
        "classify_otu": False,
    }
    steps.update(config.get("steps", {}) or {})
    return {key: bool(value) for key, value in steps.items()}


def _mothur_section(config: dict[str, Any]) -> dict[str, Any]:
    mothur_config = config.get("mothur", {})
    if not isinstance(mothur_config, dict):
        raise ValueError("mothur configuration must be a mapping")
    return mothur_config


def _section(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"mothur.{name} configuration must be a mapping")
    return value


def run_pipeline(args: argparse.Namespace) -> None:
    """Preserve the original direct CLI route."""
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    setup_logging(args.log_file)
    require_files(
        [args.combined_fasta, args.combined_group, args.reference_fasta, args.taxonomy_file],
        "mothur input",
    )
    mothur = resolve_tool("mothur", args.mothur_path)
    logging.info("Using mothur: %s", mothur)
    logging.info("Length filtering range: %d-%d bp", args.min_length, args.max_length)

    summary_seqs(mothur, args.combined_fasta, args.processors)
    good_fasta, good_group = screen_seqs(
        mothur,
        args.combined_fasta,
        args.combined_group,
        args.min_length,
        args.max_length,
        args.processors,
    )
    taxonomy_out = classify_seqs(
        mothur,
        good_fasta,
        good_group,
        args.reference_fasta,
        args.taxonomy_file,
        args.method,
        args.numwanted,
        args.search,
        args.processors,
    )
    if args.remove_lineage:
        remove_lineage(mothur, good_fasta, taxonomy_out, args.lineage_exclude)
    logging.info("mothur processing completed successfully.")


def run_configured_mothur_steps(config: dict[str, Any]) -> dict[str, Any]:
    mothur_config = _mothur_section(config)
    if not bool(mothur_config.get("enabled", True)):
        return {"mode": "mothur", "enabled": False, "steps_run": []}

    output_dir = str(mothur_config.get("output_dir", "results/mothur"))
    log_file = str(mothur_config.get("log_file", f"{output_dir}/mothur_processing.log"))
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    setup_logging(log_file)

    processors = int(mothur_config.get("processors", 16))
    mothur_path = resolve_tool("mothur", str(mothur_config.get("mothur_path", "mothur")))
    state = MothurState(
        fasta=str(mothur_config.get("combined_fasta", "results/preprocess/combined.fasta")),
        group=str(mothur_config.get("combined_group", "results/preprocess/combined.groups")),
    )
    _require_existing([state.fasta, state.group], "mothur input")
    steps = default_mothur_steps(mothur_config)
    steps_run: list[str] = []

    if steps["summary"]:
        _run_mothur(mothur_path, build_summary_seqs_expression(state.fasta, processors), "summary.seqs")
        steps_run.append("summary")

    if steps["screen_length"]:
        cfg = _section(mothur_config, "screen_length")
        _run_mothur(
            mothur_path,
            build_screen_length_expression(
                fasta=state.fasta,
                group=state.group,
                count=state.count,
                min_length=int(cfg.get("min_length", 1000)),
                max_length=int(cfg.get("max_length", 3000)),
                maxambig=cfg.get("maxambig", 0),
                maxhomop=cfg.get("maxhomop"),
                processors=processors,
            ),
            "screen.seqs length",
        )
        good_fasta, good_group = expected_screen_outputs(state.fasta, state.group)
        _ensure_output(good_fasta, "screen_length")
        _ensure_output(good_group, "screen_length")
        state.fasta = good_fasta
        state.group = good_group
        steps_run.append("screen_length")

    if steps["unique"]:
        _run_mothur(mothur_path, build_unique_seqs_expression(state.fasta), "unique.seqs")
        state.name = expected_with_tag(state.fasta, "names", ".names")
        state.fasta = expected_with_tag(state.fasta, "unique")
        _ensure_output(state.fasta, "unique")
        _ensure_output(state.name, "unique")
        steps_run.append("unique")

    if steps["align"]:
        cfg = _section(mothur_config, "align")
        reference = cfg.get("reference_fasta")
        if not reference:
            raise ValueError("mothur.align.reference_fasta is required when align is enabled")
        _require_existing([str(reference)], "align.seqs reference")
        _run_mothur(
            mothur_path,
            build_align_seqs_expression(state.fasta, str(reference), processors),
            "align.seqs",
        )
        state.fasta = expected_with_tag(state.fasta, "align")
        _ensure_output(state.fasta, "align")
        steps_run.append("align")

    if steps["screen_alignment"]:
        cfg = _section(mothur_config, "screen_alignment")
        if cfg.get("start") is None and cfg.get("end") is None and cfg.get("maxhomop") is None:
            raise ValueError("screen_alignment is enabled but no start, end, or maxhomop parameter is set")
        _run_mothur(
            mothur_path,
            build_screen_alignment_expression(
                fasta=state.fasta,
                group=state.group,
                count=state.count,
                start=cfg.get("start"),
                end=cfg.get("end"),
                maxhomop=cfg.get("maxhomop"),
                processors=processors,
            ),
            "screen.seqs alignment",
        )
        good_fasta, good_group = expected_screen_outputs(state.fasta, state.group)
        _ensure_output(good_fasta, "screen_alignment")
        _ensure_output(good_group, "screen_alignment")
        state.fasta = good_fasta
        state.group = good_group
        steps_run.append("screen_alignment")

    if steps["filter_alignment"]:
        cfg = _section(mothur_config, "filter_alignment")
        _run_mothur(
            mothur_path,
            build_filter_seqs_expression(
                state.fasta,
                vertical=bool(cfg.get("vertical", True)),
                trump=str(cfg.get("trump", ".")),
                processors=processors,
            ),
            "filter.seqs",
        )
        state.fasta = expected_with_tag(state.fasta, "filter")
        _ensure_output(state.fasta, "filter_alignment")
        steps_run.append("filter_alignment")

    if steps["precluster"]:
        cfg = _section(mothur_config, "precluster")
        if not state.name and not state.count:
            raise ValueError("precluster requires a name or count file; enable unique first or provide count tracking")
        _run_mothur(
            mothur_path,
            build_precluster_expression(
                fasta=state.fasta,
                name=state.name,
                count=state.count,
                diffs=cfg.get("diffs"),
                diffs_per_100bp=cfg.get("diffs_per_100bp", 1),
                processors=processors,
            ),
            "pre.cluster",
        )
        state.fasta = expected_with_tag(state.fasta, "precluster")
        if state.name:
            state.name = expected_with_tag(state.name, "precluster", ".names")
        _ensure_output(state.fasta, "precluster")
        steps_run.append("precluster")

    if steps["chimera_vsearch"]:
        cfg = _section(mothur_config, "chimera_vsearch")
        if not state.name and not state.count:
            raise ValueError("chimera_vsearch requires a name or count file; enable unique/precluster or provide count tracking")
        _run_mothur(
            mothur_path,
            build_chimera_vsearch_expression(
                fasta=state.fasta,
                name=state.name,
                count=state.count,
                dereplicate=bool(cfg.get("dereplicate", True)),
                processors=processors,
            ),
            "chimera.vsearch",
        )
        state.fasta = expected_with_tag(state.fasta, "denovo.vsearch.pick")
        _ensure_output(state.fasta, "chimera_vsearch")
        steps_run.append("chimera_vsearch")

    if steps["classify"]:
        cfg = _section(mothur_config, "classify")
        reference = cfg.get("reference_fasta")
        taxonomy = cfg.get("taxonomy_file")
        if not reference or not taxonomy:
            raise ValueError("mothur.classify.reference_fasta and mothur.classify.taxonomy_file are required when classify is enabled")
        _require_existing([str(reference), str(taxonomy)], "classify.seqs reference")
        method = str(cfg.get("method", "knn"))
        _run_mothur(
            mothur_path,
            build_classify_seqs_expression(
                fasta=state.fasta,
                group=state.group,
                count=state.count,
                reference=str(reference),
                taxonomy=str(taxonomy),
                method=method,
                numwanted=int(cfg.get("numwanted", 1)),
                search=str(cfg.get("search", "blastplus")),
                cutoff=cfg.get("cutoff"),
                processors=processors,
            ),
            "classify.seqs",
        )
        # classify.seqs convention assumed here: *.{taxonomy_stem}.{method}.taxonomy.
        state.taxonomy = f"{Path(state.fasta).with_suffix('')}.{Path(str(taxonomy)).stem}.{method}.taxonomy"
        _ensure_output(state.taxonomy, "classify")
        steps_run.append("classify")

    if steps["remove_lineage"]:
        cfg = _section(mothur_config, "remove_lineage")
        if not state.taxonomy:
            raise ValueError("remove_lineage requires taxonomy output; enable classify first")
        taxon = build_taxon_arg(str(cfg.get("taxon", "Chloroplast-Mitochondria")))
        _run_mothur(
            mothur_path,
            build_remove_lineage_expression(
                fasta=state.fasta,
                taxonomy=state.taxonomy,
                group=state.group,
                count=state.count,
                taxon=taxon,
            ),
            "remove.lineage",
        )
        steps_run.append("remove_lineage")

    if steps["make_shared"]:
        cfg = _section(mothur_config, "make_shared")
        if not state.list_file:
            raise ValueError("make_shared requires a list file from an upstream clustering step")
        _run_mothur(
            mothur_path,
            build_make_shared_expression(
                state.list_file,
                group=state.group,
                count=state.count,
                label=str(cfg.get("label", "0.03")),
            ),
            "make.shared",
        )
        steps_run.append("make_shared")

    if steps["classify_otu"]:
        cfg = _section(mothur_config, "classify_otu")
        if not state.list_file or not state.taxonomy:
            raise ValueError("classify_otu requires both list and taxonomy files")
        _run_mothur(
            mothur_path,
            build_classify_otu_expression(
                state.list_file,
                taxonomy=state.taxonomy,
                label=str(cfg.get("label", "0.03")),
            ),
            "classify.otu",
        )
        steps_run.append("classify_otu")

    logging.info("Configured mothur processing completed successfully.")
    return {
        "mode": "mothur",
        "enabled": True,
        "steps_run": steps_run,
        "final_fasta": state.fasta,
        "final_group": state.group,
        "taxonomy": state.taxonomy,
        "output_dir": output_dir,
    }


def run_configured_mothur(config: dict[str, Any]) -> dict[str, Any]:
    """Run mothur mode from YAML configuration."""
    return run_configured_mothur_steps(config)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("PacBio Kinnex mothur processing")
    parser.add_argument("--combined-fasta", required=True)
    parser.add_argument("--combined-group", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--reference-fasta", required=True)
    parser.add_argument("--taxonomy-file", required=True)
    parser.add_argument("--method", default="knn")
    parser.add_argument("--numwanted", type=int, default=1)
    parser.add_argument("--search", default="blastplus")
    parser.add_argument("--processors", type=int, default=8)
    parser.add_argument("--remove-lineage", action="store_true")
    parser.add_argument("--lineage-exclude", default="Chloroplast-Mitochondria")
    parser.add_argument("--min-length", type=int, default=1000)
    parser.add_argument("--max-length", type=int, default=3000)
    parser.add_argument("--log-file", required=True)
    parser.add_argument("--mothur-path")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        run_pipeline(args)
    except Exception as exc:
        logging.error("mothur pipeline failed: %s", exc)
        sys.exit(1)
