"""Kinnex barcode and sample sheet parsing."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

KINNEX_BARCODE_PATTERN = re.compile(
    r"(Kinnex16S_Fwd_\d+--Kinnex16S_Rev_\d+)"
)
KINNEX_BAM_FILENAME_PATTERN = re.compile(
    rf"{KINNEX_BARCODE_PATTERN.pattern}\.bam$"
)
REQUIRED_SAMPLE_SHEET_COLUMNS = {"barcode": "Barcode", "sample name": "Sample Name"}


@dataclass(frozen=True)
class SampleSheet:
    rows: list[dict[str, str]]
    barcode_to_sample: dict[str, str]
    delimiter: str


def extract_kinnex_barcode(filename: str) -> tuple[str, str]:
    """Extract a Kinnex barcode from a demultiplexed BAM/FASTA filename."""
    match = KINNEX_BAM_FILENAME_PATTERN.search(Path(filename).name)
    if not match:
        return "", "Incorrect filename format"
    barcode = match.group(1)
    if "Fwd" not in barcode or "Rev" not in barcode:
        return barcode, "Incorrect primer directions"
    return barcode, "Valid"


def extract_kinnex_barcode_from_any_path(path: str | Path) -> str | None:
    match = KINNEX_BARCODE_PATTERN.search(str(path))
    return match.group(1) if match else None


def detect_delimiter(sample_sheet: str | Path) -> str:
    text = Path(sample_sheet).read_text()
    sample = "\n".join(text.splitlines()[:10])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t")
        return dialect.delimiter
    except csv.Error:
        first = sample.splitlines()[0] if sample else ""
        return "\t" if "\t" in first else ","


def _normalise_header(header: str) -> str:
    return " ".join(header.strip().lower().split())


def parse_sample_sheet(sample_sheet: str | Path) -> SampleSheet:
    """Parse comma- or tab-delimited sample sheets with tolerant headers."""
    path = Path(sample_sheet)
    if not path.is_file():
        raise FileNotFoundError(f"Sample barcode file not found: {path}")

    delimiter = detect_delimiter(path)
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError(f"Sample barcode file has no header: {path}")

        normalised = {_normalise_header(col): col for col in reader.fieldnames}
        missing = [
            display
            for key, display in REQUIRED_SAMPLE_SHEET_COLUMNS.items()
            if key not in normalised
        ]
        if missing:
            raise ValueError(
                f"Sample barcode file must contain columns: {', '.join(missing)}"
            )

        barcode_col = normalised["barcode"]
        sample_col = normalised["sample name"]
        rows: list[dict[str, str]] = []
        barcode_to_sample: dict[str, str] = {}
        seen_samples: set[str] = set()

        for line_number, row in enumerate(reader, start=2):
            barcode = (row.get(barcode_col) or "").strip()
            sample_name = (row.get(sample_col) or "").strip()
            if not barcode or not sample_name:
                raise ValueError(
                    f"Sample barcode file line {line_number} has an empty Barcode or Sample Name"
                )
            if not KINNEX_BARCODE_PATTERN.fullmatch(barcode):
                raise ValueError(
                    f"Sample barcode file line {line_number} has invalid Kinnex barcode: {barcode}"
                )
            if barcode in barcode_to_sample:
                raise ValueError(f"Duplicate barcode in sample sheet: {barcode}")
            if sample_name in seen_samples:
                raise ValueError(f"Duplicate sample name in sample sheet: {sample_name}")
            seen_samples.add(sample_name)
            barcode_to_sample[barcode] = sample_name
            rows.append({"Barcode": barcode, "Sample Name": sample_name})

    return SampleSheet(rows=rows, barcode_to_sample=barcode_to_sample, delimiter=delimiter)


def write_normalised_sample_sheet(sheet: SampleSheet, output_path: str | Path) -> None:
    with Path(output_path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Barcode", "Sample Name"], delimiter="\t")
        writer.writeheader()
        writer.writerows(sheet.rows)
