import csv
import sys
import types

import pytest

from kinnex16s import pbmm2_runner


class MockRead:
    def __init__(
        self,
        query_name="read1",
        reference_name="refA",
        mapping_quality=60,
        nm=10,
        query_alignment_length=1000,
        query_length=1000,
        is_unmapped=False,
        is_secondary=False,
        is_supplementary=False,
    ):
        self.query_name = query_name
        self.reference_name = reference_name
        self.mapping_quality = mapping_quality
        self._nm = nm
        self.query_alignment_length = query_alignment_length
        self.query_length = query_length
        self.is_unmapped = is_unmapped
        self.is_secondary = is_secondary
        self.is_supplementary = is_supplementary

    def get_tag(self, tag):
        if tag == "NM" and self._nm is not None:
            return self._nm
        raise KeyError(tag)


def test_pbmm2_index_command_construction():
    assert pbmm2_runner.build_pbmm2_index_command("ref.fasta", "ref.mmi", 16) == [
        "pbmm2",
        "index",
        "ref.fasta",
        "ref.mmi",
        "--num-threads",
        "16",
    ]


def test_pbmm2_align_command_construction():
    assert pbmm2_runner.build_pbmm2_align_command("ref.mmi", "sample.bam", "out.bam") == [
        "pbmm2",
        "align",
        "ref.mmi",
        "sample.bam",
        "out.bam",
        "--preset",
        "CCS",
        "--sort",
        "--num-threads",
        "16",
    ]


def test_samtools_index_command_construction():
    assert pbmm2_runner.build_samtools_index_command("out.bam") == ["samtools", "index", "out.bam"]


def test_identity_calculation_with_nm_tag():
    assert pbmm2_runner.calculate_alignment_identity(MockRead(nm=20, query_alignment_length=1000)) == 0.98


def test_query_coverage_calculation():
    assert pbmm2_runner.calculate_query_coverage(
        MockRead(query_alignment_length=900, query_length=1000)
    ) == 0.9


def test_read_passes_mapping_filters_good_read():
    assert pbmm2_runner.read_passes_mapping_filters(MockRead())


def test_read_passes_mapping_filters_fails_low_mapq():
    assert not pbmm2_runner.read_passes_mapping_filters(MockRead(mapping_quality=10))


def test_read_passes_mapping_filters_fails_low_identity():
    assert not pbmm2_runner.read_passes_mapping_filters(MockRead(nm=100))


def test_read_passes_mapping_filters_fails_low_query_coverage():
    assert not pbmm2_runner.read_passes_mapping_filters(
        MockRead(query_alignment_length=800, query_length=1000)
    )


def test_read_passes_mapping_filters_fails_short_alignment():
    assert not pbmm2_runner.read_passes_mapping_filters(
        MockRead(query_alignment_length=500, query_length=1000)
    )


def test_summarize_filtered_mappings_with_fake_pysam(monkeypatch, tmp_path):
    reads = [
        MockRead(query_name="read1", reference_name="refA", nm=10),
        MockRead(query_name="read2", reference_name="refA", nm=20),
        MockRead(query_name="read3", is_unmapped=True),
        MockRead(query_name="read4", is_secondary=True),
        MockRead(query_name="read5", mapping_quality=5),
    ]

    class FakeAlignmentFile:
        def __init__(self, path, mode):
            self.path = path
            self.mode = mode

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __iter__(self):
            return iter(reads)

    fake_pysam = types.SimpleNamespace(AlignmentFile=FakeAlignmentFile)
    monkeypatch.setitem(sys.modules, "pysam", fake_pysam)

    reference_counts = tmp_path / "reference_counts.tsv"
    mapping_qc = tmp_path / "mapping_qc.tsv"
    assignments = tmp_path / "filtered_assignments.tsv"
    unmapped = tmp_path / "unmapped_read_ids.txt"

    result = pbmm2_runner.summarize_filtered_mappings(
        "sample.bam",
        str(reference_counts),
        str(mapping_qc),
        str(assignments),
        str(unmapped),
        sample_name="sample",
    )

    assert result["reference_counts"] == {"refA": 2}
    with reference_counts.open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows == [{"reference_id": "refA", "read_count": "2", "relative_mapping_signal": "1.000000"}]
    with mapping_qc.open() as handle:
        qc_row = next(csv.DictReader(handle, delimiter="\t"))
    assert qc_row["total_records_seen"] == "5"
    assert qc_row["mapped_primary_records_passing_filter"] == "2"
    assert unmapped.read_text() == "read3\n"


def _pbmm2_config(tmp_path, **overrides):
    config = {
        "pbmm2_mapping": {
            "enabled": True,
            "pbmm2_path": "pbmm2",
            "samtools_path": "samtools",
            "input_bam_dir": str(tmp_path / "inputs"),
            "input_bams": [],
            "reference_fasta": "ref.fasta",
            "reference_index": str(tmp_path / "ref.mmi"),
            "index_reference": True,
            "output_dir": str(tmp_path / "pbmm2"),
            "preset": "CCS",
            "threads": 16,
            "filters": {
                "primary_only": True,
                "min_mapq": 20,
                "min_identity": 0.97,
                "min_query_coverage": 0.90,
                "min_alignment_length": 1000,
                "multimapper_policy": "best_hit",
            },
            "outputs": {
                "sorted_bam": True,
                "bam_index": True,
                "reference_counts": True,
                "relative_abundance": True,
                "mapping_qc": True,
                "filtered_assignments": True,
                "unmapped_read_ids": True,
            },
        }
    }
    config["pbmm2_mapping"].update(overrides)
    return config


def _patch_pbmm2_runtime(monkeypatch):
    commands = []
    monkeypatch.setattr(pbmm2_runner, "resolve_tool", lambda tool, explicit_path=None: explicit_path or tool)
    monkeypatch.setattr(
        pbmm2_runner,
        "run_command",
        lambda command, description: commands.append((command, description)),
    )
    monkeypatch.setattr(
        pbmm2_runner,
        "summarize_filtered_mappings",
        lambda *args, **kwargs: {
            "qc": {
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
        },
    )
    return commands


def test_config_driven_pbmm2_route_discovers_input_bams(monkeypatch, tmp_path):
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    (input_dir / "sampleA.bam").write_text("")
    (input_dir / "sampleB.bam").write_text("")
    commands = _patch_pbmm2_runtime(monkeypatch)

    result = pbmm2_runner.run_pbmm2_mapping_from_config(_pbmm2_config(tmp_path))

    assert [sample["sample_name"] for sample in result["samples"]] == ["sampleA", "sampleB"]
    assert commands[0][0][1] == "index"
    assert [command[0][1] for command in commands if command[0][1] == "align"] == ["align", "align"]


def test_config_driven_pbmm2_route_uses_explicit_input_bams(monkeypatch, tmp_path):
    commands = _patch_pbmm2_runtime(monkeypatch)
    explicit = [str(tmp_path / "explicit.bam")]

    result = pbmm2_runner.run_pbmm2_mapping_from_config(
        _pbmm2_config(tmp_path, input_bams=explicit)
    )

    assert [sample["input_bam"] for sample in result["samples"]] == explicit
    align_commands = [command for command, _ in commands if command[1] == "align"]
    assert align_commands[0][3] == explicit[0]


def test_invalid_multimapper_policy_rejected():
    with pytest.raises(ValueError, match="Invalid multimapper_policy"):
        pbmm2_runner.validate_pbmm2_config(
            {
                "pbmm2_mapping": {
                    "reference_fasta": "ref.fasta",
                    "reference_index": "ref.mmi",
                    "output_dir": "out",
                    "filters": {"multimapper_policy": "em"},
                }
            }
        )
