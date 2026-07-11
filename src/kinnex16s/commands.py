"""External command builders and runners."""

from __future__ import annotations

import logging
import subprocess


def run_command(cmd: list[str], description: str) -> subprocess.CompletedProcess[str]:
    """Run an external command without shell interpolation and log output."""
    logging.info("Starting: %s", description)
    logging.debug("Command: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Executable not found while running {description}: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        stdout = exc.stdout.strip() if exc.stdout else ""
        detail = stderr or stdout or f"exit code {exc.returncode}"
        raise RuntimeError(f"Failed during {description}: {detail}") from exc

    if result.stdout.strip():
        logging.info(result.stdout.strip())
    if result.stderr.strip():
        logging.warning(result.stderr.strip())
    logging.info("Completed: %s", description)
    return result


def build_skera_split_command(input_bam: str, adapters_fasta: str, output_bam: str) -> list[str]:
    return ["skera", "split", input_bam, adapters_fasta, output_bam]


def build_lima_command(
    input_bam: str,
    barcodes_fasta: str,
    output_bam: str,
    barcode_type: str,
) -> list[str]:
    option = "--same" if barcode_type.lower() == "symmetric" else "--different"
    return [
        "lima",
        input_bam,
        barcodes_fasta,
        output_bam,
        option,
        "--split-bam-named",
        "--min-score",
        "26",
    ]


def build_bam2fastx_command(
    tool: str,
    output_prefix: str,
    bam: str,
    compression_level: int,
    uncompressed: bool,
) -> list[str]:
    cmd = [tool, "-o", output_prefix, bam]
    cmd.append("-u" if uncompressed else "-c")
    if not uncompressed:
        cmd.append(str(compression_level))
    return cmd


def build_samtools_faidx_command(fasta: str) -> list[str]:
    return ["samtools", "faidx", fasta]


def build_mothur_command(mothur: str, mothur_expression: str) -> list[str]:
    return [mothur, f"#{mothur_expression}"]
