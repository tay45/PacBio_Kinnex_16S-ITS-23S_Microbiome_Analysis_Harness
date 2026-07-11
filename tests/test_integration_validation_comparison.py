import shutil

import pytest

from kinnex16s.comparison_report import run_comparison_from_config
from kinnex16s.validation_report import run_validation_from_config

pd = pytest.importorskip("pandas")


def test_fixture_comparison_and_validation_integration(tmp_path):
    fixtures = __import__("pathlib").Path(__file__).resolve().parent / "fixtures"
    pbmm2_dir = tmp_path / "pbmm2" / "sample"
    emu_dir = tmp_path / "emu"
    pbmm2_dir.mkdir(parents=True)
    emu_dir.mkdir()
    expected = tmp_path / "expected_taxa.tsv"
    shutil.copy(fixtures / "expected_taxa.example.tsv", expected)
    shutil.copy(fixtures / "pbmm2_reference_counts.example.tsv", pbmm2_dir / "sample.reference_counts.tsv")
    shutil.copy(fixtures / "emu_abundance.example.tsv", emu_dir / "emu_abundance.tsv")

    comparison_dir = tmp_path / "comparison"
    comparison = run_comparison_from_config(
        {
            "comparison": {
                "enabled": True,
                "output_dir": str(comparison_dir),
                "mothur_taxonomy_file": str(tmp_path / "missing_mothur.tsv"),
                "pbmm2_reference_counts_glob": str(pbmm2_dir / "*.reference_counts.tsv"),
                "emu_abundance_file": str(emu_dir / "emu_abundance.tsv"),
                "outputs": {
                    "cross_mode_summary": True,
                    "method_presence_summary": True,
                    "interpretation_checklist": True,
                },
            }
        }
    )

    validation_dir = tmp_path / "validation"
    validation = run_validation_from_config(
        {
            "validation": {
                "enabled": True,
                "output_dir": str(validation_dir),
                "expected_taxa_file": str(expected),
                "match_mode": "case_insensitive_exact",
                "observed": {
                    "comparison_summary": comparison["outputs"]["cross_mode_summary"],
                    "pbmm2_reference_counts_glob": str(pbmm2_dir / "*.reference_counts.tsv"),
                    "emu_abundance_file": str(emu_dir / "emu_abundance.tsv"),
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

    assert (comparison_dir / "cross_mode_summary.tsv").is_file()
    assert (comparison_dir / "interpretation_checklist.md").is_file()
    assert (validation_dir / "validation_interpretation_checklist.md").is_file()
    assert validation["outputs"]["method_validation_summary"]
    summary = pd.read_csv(validation_dir / "method_validation_summary.tsv", sep="\t")
    assert list(summary.columns) == [
        "method",
        "expected_taxa_count",
        "observed_features_count",
        "matched_expected_count",
        "missing_expected_count",
        "unexpected_observed_count",
        "recovery_fraction",
        "notes",
    ]
