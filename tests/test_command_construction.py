from kinnex16s.commands import (
    build_bam2fastx_command,
    build_lima_command,
    build_mothur_command,
    build_samtools_faidx_command,
    build_skera_split_command,
)


def test_skera_command_construction():
    assert build_skera_split_command("in.bam", "adapters.fasta", "out.bam") == [
        "skera",
        "split",
        "in.bam",
        "adapters.fasta",
        "out.bam",
    ]


def test_lima_command_construction_for_asymmetric_barcodes():
    assert build_lima_command("in.bam", "barcodes.fasta", "out.bam", "asymmetric") == [
        "lima",
        "in.bam",
        "barcodes.fasta",
        "out.bam",
        "--different",
        "--split-bam-named",
        "--min-score",
        "26",
    ]


def test_bam2fastx_command_construction_with_compression():
    assert build_bam2fastx_command("bam2fasta", "out/sample", "in.bam", 1, False) == [
        "bam2fasta",
        "-o",
        "out/sample",
        "in.bam",
        "-c",
        "1",
    ]


def test_bam2fastx_command_construction_uncompressed():
    assert build_bam2fastx_command("bam2fastq", "out/sample", "in.bam", 1, True) == [
        "bam2fastq",
        "-o",
        "out/sample",
        "in.bam",
        "-u",
    ]


def test_samtools_command_construction():
    assert build_samtools_faidx_command("sample.fasta") == ["samtools", "faidx", "sample.fasta"]


def test_mothur_command_construction():
    assert build_mothur_command("mothur", "summary.seqs(fasta=combined.fasta)") == [
        "mothur",
        "#summary.seqs(fasta=combined.fasta)",
    ]
