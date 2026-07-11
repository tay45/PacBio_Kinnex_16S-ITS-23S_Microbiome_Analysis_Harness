"""Build combined FASTA and mothur group files."""

from __future__ import annotations

import logging
from pathlib import Path

from .barcode_validation import extract_kinnex_barcode_from_any_path


def clean_sample_name(sample_name: str) -> str:
    return "_".join(sample_name.strip().split())


def build_group_header() -> str:
    return "sequenceID\tgroup\n"


def combine_fasta_files(
    combined_fasta: str | Path,
    group_file: str | Path,
    barcode_to_sample: dict[str, str],
    fasta_files: list[str | Path],
) -> None:
    """Combine per-barcode FASTA files and emit a mothur group file."""
    if not fasta_files:
        raise ValueError("No FASTA files were provided for combined FASTA/group generation.")

    combined_path = Path(combined_fasta)
    group_path = Path(group_file)
    combined_path.parent.mkdir(parents=True, exist_ok=True)
    group_path.parent.mkdir(parents=True, exist_ok=True)

    with combined_path.open("w") as fasta_out, group_path.open("w") as group_out:
        group_out.write(build_group_header())
        for fasta_file in fasta_files:
            path = Path(fasta_file)
            if not path.is_file():
                raise FileNotFoundError(f"FASTA file not found during combine step: {path}")
            barcode = extract_kinnex_barcode_from_any_path(path)
            if not barcode:
                logging.warning("Could not extract Kinnex barcode from FASTA filename: %s", path)
                sample_name = "Unknown"
            else:
                sample_name = barcode_to_sample.get(barcode, "Unknown")
            if sample_name == "Unknown":
                logging.warning("No sample mapping found for FASTA file: %s", path)

            sample_name_clean = clean_sample_name(sample_name)
            seq_counter = 1
            with path.open() as fasta_in:
                for line in fasta_in:
                    if line.startswith(">"):
                        original_id = line[1:].strip()
                        unique_id = f"{original_id}_{sample_name_clean}_seq{seq_counter}"
                        fasta_out.write(f">{unique_id}\n")
                        group_out.write(f"{unique_id}\t{sample_name}\n")
                        seq_counter += 1
                    else:
                        fasta_out.write(line)

    for output in (combined_path, group_path):
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError(f"Expected output was not created or is empty: {output}")
