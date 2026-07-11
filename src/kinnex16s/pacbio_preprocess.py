"""PacBio Kinnex preprocessing workflow."""

from __future__ import annotations

import argparse
import csv
import glob
import logging
import shutil
import sys
from pathlib import Path

from .barcode_validation import (
    extract_kinnex_barcode,
    parse_sample_sheet,
    write_normalised_sample_sheet,
)
from .commands import (
    build_bam2fastx_command,
    build_lima_command,
    build_samtools_faidx_command,
    build_skera_split_command,
    run_command,
)
from .fasta_group_builder import combine_fasta_files
from .validators import require_files, require_optional_file, validate_required_tools

PACBIO_TOOLS = ["lima"]


def setup_logging(log_file: str | Path) -> None:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.handlers.clear()
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )


def _move_related_files(bam: str, target_dir: str | Path) -> None:
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    for suffix in ("", ".pbi"):
        related = Path(f"{bam}{suffix}")
        if related.exists():
            shutil.move(str(related), str(target / related.name))
            logging.info("Moved %s to %s", related, target)
    for xml in glob.glob(f"{bam.replace('.bam', '')}*.xml"):
        xml_path = Path(xml)
        if xml_path.exists():
            shutil.move(str(xml_path), str(target / xml_path.name))
            logging.info("Moved %s to %s", xml_path, target)


def move_invalid_files(bam_files: list[str], invalid_dir: str, report_file: str) -> list[str]:
    valid_bams: list[str] = []
    Path(invalid_dir).mkdir(parents=True, exist_ok=True)
    with open(report_file, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["BAM File", "Issue"])
        writer.writeheader()
        for bam in bam_files:
            barcode, status = extract_kinnex_barcode(Path(bam).name)
            issues: list[str] = []
            if status != "Valid":
                issues.append(status)
            if Path(bam).stat().st_size == 0:
                issues.append("Zero file size")
            if issues:
                writer.writerow({"BAM File": bam, "Issue": "; ".join(issues)})
                target_dir = Path(invalid_dir) / "_".join(issue.replace(" ", "_") for issue in issues)
                _move_related_files(bam, target_dir)
            else:
                logging.info("Valid BAM file for barcode %s: %s", barcode, bam)
                valid_bams.append(bam)
    return valid_bams


def quarantine_unmapped_barcodes(
    valid_bams: list[str],
    barcode_to_sample: dict[str, str],
    invalid_dir: str,
    report_file: str,
) -> list[str]:
    final_valid: list[str] = []
    with open(report_file, "a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["BAM File", "Issue"])
        for bam in valid_bams:
            barcode, _ = extract_kinnex_barcode(Path(bam).name)
            if barcode in barcode_to_sample:
                final_valid.append(bam)
            else:
                reason = "Barcode not in sample sheet"
                logging.warning("%s: %s (%s)", reason, barcode, bam)
                writer.writerow({"BAM File": bam, "Issue": reason})
                _move_related_files(bam, Path(invalid_dir) / "Barcode_not_in_sample_sheet")
    return final_valid


def convert_bam_to_fastx(
    bam_files: list[str],
    output_dir: str,
    convert_types: list[str],
    compression_level: int,
    uncompressed: bool,
) -> None:
    for bam in bam_files:
        prefix = str(Path(output_dir) / Path(bam).with_suffix("").name)
        if "fastq" in convert_types:
            run_command(
                build_bam2fastx_command("bam2fastq", prefix, bam, compression_level, uncompressed),
                f"Converting {bam} to FASTQ",
            )
        if "fasta" in convert_types:
            run_command(
                build_bam2fastx_command("bam2fasta", prefix, bam, compression_level, uncompressed),
                f"Converting {bam} to FASTA",
            )


def generate_fasta_indexes(fasta_files: list[Path]) -> None:
    for fasta in fasta_files:
        if not fasta.is_file():
            raise FileNotFoundError(f"FASTA file not found before indexing: {fasta}")
        if fasta.stat().st_size == 0:
            raise RuntimeError(f"FASTA file is empty before indexing: {fasta}")
        run_command(build_samtools_faidx_command(str(fasta)), f"Indexing {fasta}")


def validate_preprocess_inputs(args: argparse.Namespace) -> None:
    tools = list(PACBIO_TOOLS)
    if not args.skip_skera:
        tools.append("skera")
    if "fastq" in args.convert_types:
        tools.append("bam2fastq")
    if "fasta" in args.convert_types:
        tools.extend(["bam2fasta", "samtools"])
    validate_required_tools(sorted(set(tools)))
    require_files([args.input_bam, args.barcodes_fasta, args.sample_barcode_csv])
    if not args.skip_skera:
        require_optional_file(args.adapters_fasta, "adapters FASTA")
    if args.athena_db and not Path(args.athena_db).is_dir():
        raise NotADirectoryError(f"--athena-db was provided but does not exist: {args.athena_db}")


def run_pipeline(args: argparse.Namespace) -> None:
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    setup_logging(Path(args.output_dir) / "pipeline.log")
    validate_preprocess_inputs(args)

    sheet = parse_sample_sheet(args.sample_barcode_csv)
    converted_sheet = Path(args.output_dir) / "sample-barcode.normalized.tsv"
    write_normalised_sample_sheet(sheet, converted_sheet)
    logging.info(
        "Loaded %d sample barcode mappings from %s-delimited sample sheet.",
        len(sheet.barcode_to_sample),
        "tab" if sheet.delimiter == "\t" else "comma",
    )

    if args.adapters_fasta and not args.skip_skera:
        skera_out = str(Path(args.output_dir) / "skera_split.bam")
        run_command(build_skera_split_command(args.input_bam, args.adapters_fasta, skera_out), "Skera split")
        input_bam = skera_out
    else:
        input_bam = args.input_bam
        logging.info("Skera split skipped.")

    lima_output_bam = str(Path(args.output_dir) / "lima_output.bam")
    run_command(
        build_lima_command(input_bam, args.barcodes_fasta, lima_output_bam, args.barcode_type),
        "Lima demultiplexing",
    )

    lima_prefix = str(Path(args.output_dir) / "lima_output")
    demux_bams = sorted(glob.glob(f"{lima_prefix}.*.bam"))
    if not demux_bams:
        raise RuntimeError(f"No demultiplexed BAM files found using prefix: {lima_prefix}")

    invalid_dir = str(Path(args.output_dir) / "invalid_files")
    report_file = str(Path(args.output_dir) / "invalid_files_report.csv")
    valid_bams = move_invalid_files(demux_bams, invalid_dir, report_file)
    valid_bams = quarantine_unmapped_barcodes(valid_bams, sheet.barcode_to_sample, invalid_dir, report_file)

    if not valid_bams:
        logging.warning("No valid BAM files to process after barcode validation.")
        return

    convert_bam_to_fastx(
        valid_bams,
        output_dir=args.output_dir,
        convert_types=args.convert_types,
        compression_level=args.compression_level,
        uncompressed=args.uncompressed,
    )

    if "fasta" not in args.convert_types:
        logging.info("FASTQ-only conversion requested; skipping combined FASTA/group generation.")
        return

    fasta_files = [Path(args.output_dir) / f"{Path(bam).with_suffix('').name}.fasta" for bam in valid_bams]
    existing_fasta_files = [fasta for fasta in fasta_files if fasta.is_file()]
    if not existing_fasta_files:
        raise RuntimeError("FASTA conversion was requested, but no FASTA outputs were found.")

    generate_fasta_indexes(existing_fasta_files)
    combine_fasta_files(
        Path(args.output_dir) / "combined.fasta",
        Path(args.output_dir) / "combined.groups",
        sheet.barcode_to_sample,
        existing_fasta_files,
    )
    logging.info("Preprocessing pipeline completed successfully.")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PacBio Kinnex 16S-ITS-23S preprocessing harness"
    )
    parser.add_argument("--input-bam", required=True, help="Input PacBio HiFi BAM file.")
    parser.add_argument("--adapters-fasta", help="Adapters FASTA for Skera split.")
    parser.add_argument("--barcodes-fasta", required=True, help="Kinnex barcode FASTA for Lima.")
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    parser.add_argument(
        "--athena-db",
        help="Optional Athena database directory retained for compatibility; validated if provided.",
    )
    parser.add_argument("--barcode-type", choices=["symmetric", "asymmetric"], required=True)
    parser.add_argument("--skip-skera", action="store_true", help="Skip Skera split.")
    parser.add_argument(
        "--convert-types",
        nargs="+",
        choices=["fasta", "fastq"],
        default=["fasta", "fastq"],
        help="Output conversion types. FASTQ-only runs skip combined FASTA/group generation.",
    )
    parser.add_argument("--compression-level", type=int, choices=range(1, 10), default=1)
    parser.add_argument("--uncompressed", action="store_true")
    parser.add_argument(
        "--sample-barcode-csv",
        required=True,
        help="Comma- or tab-delimited sample sheet with Barcode and Sample Name columns.",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        run_pipeline(args)
    except Exception as exc:
        logging.error("Pipeline failed: %s", exc)
        sys.exit(1)
