import sys

import pytest

from kinnex16s import downstream_router, validation_report

pd = pytest.importorskip("pandas")


def test_safe_read_table_handles_missing_file(tmp_path):
    assert validation_report.safe_read_table(tmp_path / "missing.tsv") is None


def test_load_expected_taxa_normalizes_id_and_name(tmp_path):
    path = tmp_path / "expected.tsv"
    path.write_text("reference_id\tspecies\tnotes\nrefA\tSpecies A\texpected\n")

    df = validation_report.load_expected_taxa(path)

    assert df.iloc[0]["expected_id"] == "refA"
    assert df.iloc[0]["expected_name"] == "Species A"


def test_load_expected_taxa_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "expected.tsv"
    path.write_text("expected_id\texpected_name\nrefA\tA\nrefA\tA duplicate\n")

    with pytest.raises(ValueError, match="Duplicate expected IDs"):
        validation_report.load_expected_taxa(path)


def test_normalize_observed_table_pbmm2(tmp_path):
    path = tmp_path / "counts.tsv"
    path.write_text("reference_id\tread_count\trelative_mapping_signal\nrefA\t10\t0.8\n")

    df = validation_report.normalize_observed_table(path, "pbmm2_mapping")

    assert df.iloc[0]["method"] == "pbmm2_mapping"
    assert df.iloc[0]["observed_id"] == "refA"
    assert df.iloc[0]["observed_signal"] == 0.8


def test_normalize_observed_table_emu(tmp_path):
    path = tmp_path / "emu.tsv"
    path.write_text("tax_id\tspecies\tabundance\n123\tSpecies A\t0.4\n")

    df = validation_report.normalize_observed_table(path, "emu_abundance")

    assert df.iloc[0]["method"] == "emu_abundance"
    assert df.iloc[0]["observed_name"] == "Species A"


def test_normalize_observed_table_comparison(tmp_path):
    path = tmp_path / "cross.tsv"
    path.write_text(
        "method\tfeature_id\ttaxon\tcount_or_signal\traw_count\tsource_file\n"
        "pbmm2_mapping\trefA\trefA\t0.8\t10\tcounts.tsv\n"
    )

    df = validation_report.normalize_observed_table(path, "comparison")

    assert df.iloc[0]["observed_id"] == "refA"
    assert df.iloc[0]["method"] == "pbmm2_mapping"


def test_match_expected_to_observed_case_insensitive_exact():
    expected = pd.DataFrame(
        [{"expected_id": "RefA", "expected_name": "Species A", "expected_relative_abundance": None, "expected_group": None, "notes": None, "source_file": "expected"}]
    )
    observed = pd.DataFrame(
        [{"method": "pbmm2_mapping", "observed_id": "refa", "observed_name": "refa", "observed_signal": 1.0, "raw_count": 5, "source_file": "observed"}]
    )

    recovery = validation_report.match_expected_to_observed(expected, observed)

    assert bool(recovery.iloc[0]["matched"]) is True


def test_detect_unexpected_observed_identifies_not_expected():
    expected = pd.DataFrame(
        [{"expected_id": "refA", "expected_name": "Species A", "expected_relative_abundance": None, "expected_group": None, "notes": None, "source_file": "expected"}]
    )
    observed = pd.DataFrame(
        [{"method": "pbmm2_mapping", "observed_id": "refB", "observed_name": "Species B", "observed_signal": 0.2, "raw_count": 1, "source_file": "observed"}]
    )

    unexpected = validation_report.detect_unexpected_observed(expected, observed)

    assert unexpected.iloc[0]["observed_id"] == "refB"
    assert unexpected.iloc[0]["reason"] == "observed_not_in_expected_table"


def test_method_validation_summary_recovery_fraction():
    expected = pd.DataFrame(
        [
            {"expected_id": "refA", "expected_name": "A"},
            {"expected_id": "refB", "expected_name": "B"},
        ]
    )
    observed = pd.DataFrame(
        [{"method": "pbmm2_mapping", "observed_id": "refA", "observed_name": "A", "observed_signal": 1.0, "raw_count": 1, "source_file": "obs"}]
    )
    recovery = pd.DataFrame(
        [
            {"method": "pbmm2_mapping", "matched": True},
            {"method": "pbmm2_mapping", "matched": False},
        ]
    )
    unexpected = pd.DataFrame(columns=["method"])

    summary = validation_report.build_method_validation_summary(expected, observed, recovery, unexpected)

    assert summary.iloc[0]["recovery_fraction"] == 0.5


def test_write_validation_interpretation_checklist_contains_required_language(tmp_path):
    output = tmp_path / "checklist.md"

    validation_report.write_validation_interpretation_checklist(output)

    text = output.read_text()
    assert "mapping-derived relative signal" in text
    assert "not absolute abundance" in text
    assert "full-length 16S" in text
    assert "not automatically false positives" in text


def test_run_validation_from_config_creates_outputs_with_expected_and_pbmm2(tmp_path):
    expected = tmp_path / "expected.tsv"
    expected.write_text("expected_id\texpected_name\nrefA\trefA\nrefB\trefB\n")
    pbmm2_dir = tmp_path / "pbmm2" / "sample"
    pbmm2_dir.mkdir(parents=True)
    (pbmm2_dir / "sample.reference_counts.tsv").write_text(
        "reference_id\tread_count\trelative_mapping_signal\nrefA\t10\t1.0\n"
    )
    output_dir = tmp_path / "validation"

    result = validation_report.run_validation_from_config(
        {
            "validation": {
                "enabled": True,
                "output_dir": str(output_dir),
                "expected_taxa_file": str(expected),
                "match_mode": "case_insensitive_exact",
                "observed": {
                    "comparison_summary": str(tmp_path / "missing_comparison.tsv"),
                    "pbmm2_reference_counts_glob": str(tmp_path / "pbmm2" / "*" / "*.reference_counts.tsv"),
                    "emu_abundance_file": str(tmp_path / "missing_emu.tsv"),
                    "mothur_taxonomy_file": str(tmp_path / "missing_mothur.tsv"),
                },
                "outputs": {
                    "expected_taxa_recovery": True,
                    "missing_expected_taxa": True,
                    "unexpected_taxa": True,
                    "method_validation_summary": True,
                    "interpretation_checklist": True,
                    "validation_manifest": True,
                },
            }
        }
    )

    assert result["enabled"] is True
    assert (output_dir / "expected_taxa_recovery.tsv").is_file()
    assert (output_dir / "missing_expected_taxa.tsv").is_file()
    assert (output_dir / "method_validation_summary.tsv").is_file()
    assert (output_dir / "validation_manifest.json").is_file()


def test_downstream_router_supports_validation_mode(monkeypatch):
    calls = []
    monkeypatch.setattr(
        downstream_router,
        "run_validation_from_config",
        lambda config, force=False: calls.append(("validation", force)) or {"mode": "validation"},
    )

    result = downstream_router.route_downstream(
        {"downstream": {"mode": "validation", "allowed_modes": ["validation"]}}
    )

    assert calls == [("validation", True)]
    assert result == [{"mode": "validation"}]


def test_cli_accepts_validate_subcommand(monkeypatch):
    from kinnex16s import cli

    monkeypatch.setattr(sys, "argv", ["kinnex16s", "validate", "--help"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
