import sys

import pytest

from kinnex16s import comparison_report, downstream_router

pd = pytest.importorskip("pandas")


def test_safe_read_tsv_returns_none_for_missing_file(tmp_path):
    assert comparison_report.safe_read_tsv(tmp_path / "missing.tsv") is None


def test_load_pbmm2_reference_counts_normalizes_small_tsv(tmp_path):
    path = tmp_path / "sample.reference_counts.tsv"
    path.write_text(
        "reference_id\tread_count\trelative_mapping_signal\n"
        "refA\t10\t0.75\n"
    )

    normalized = comparison_report.load_pbmm2_reference_counts(path)

    assert list(normalized.columns) == comparison_report.NORMALIZED_COLUMNS
    assert normalized.iloc[0]["method"] == "pbmm2_mapping"
    assert normalized.iloc[0]["feature_id"] == "refA"
    assert normalized.iloc[0]["count_or_signal"] == 0.75
    assert normalized.iloc[0]["raw_count"] == 10


def test_load_emu_abundance_normalizes_species_abundance(tmp_path):
    path = tmp_path / "emu_abundance.tsv"
    path.write_text("tax_id\tspecies\tabundance\n123\tSpecies alpha\t0.42\n")

    normalized, note = comparison_report.load_emu_abundance(path)

    assert note == "normalized"
    assert normalized.iloc[0]["method"] == "emu_abundance"
    assert normalized.iloc[0]["feature_id"] == "123"
    assert normalized.iloc[0]["taxon"] == "Species alpha"
    assert normalized.iloc[0]["count_or_signal"] == 0.42


def test_write_cross_mode_summary_combines_pbmm2_and_emu(tmp_path):
    pbmm2 = pd.DataFrame(
        [
            {
                "method": "pbmm2_mapping",
                "feature_id": "refA",
                "taxon": "refA",
                "count_or_signal": 0.7,
                "raw_count": 7,
                "source_file": "pbmm2.tsv",
            }
        ]
    )
    emu = pd.DataFrame(
        [
            {
                "method": "emu_abundance",
                "feature_id": "123",
                "taxon": "Species alpha",
                "count_or_signal": 0.3,
                "raw_count": None,
                "source_file": "emu.tsv",
            }
        ]
    )
    output = tmp_path / "cross_mode_summary.tsv"

    comparison_report.write_cross_mode_summary([pbmm2, emu], output)

    rows = pd.read_csv(output, sep="\t")
    assert rows["method"].tolist() == ["pbmm2_mapping", "emu_abundance"]


def test_write_method_presence_summary_reports_found_and_missing(tmp_path):
    output = tmp_path / "method_presence_summary.tsv"
    comparison_report.write_method_presence_summary(
        [
            {
                "method": "pbmm2_mapping",
                "expected_file": "found.tsv",
                "found": True,
                "normalized": True,
                "notes": "normalized",
            },
            {
                "method": "emu_abundance",
                "expected_file": "missing.tsv",
                "found": False,
                "normalized": False,
                "notes": "missing",
            },
        ],
        output,
    )

    rows = pd.read_csv(output, sep="\t")
    assert rows["found"].tolist() == [True, False]
    assert rows["normalized"].tolist() == [True, False]


def test_write_interpretation_checklist_contains_required_language(tmp_path):
    output = tmp_path / "interpretation_checklist.md"

    comparison_report.write_interpretation_checklist(output)

    text = output.read_text()
    assert "mapping-derived relative signal" in text
    assert "full-length 16S" in text
    assert "not absolute abundance" in text


def test_run_comparison_from_config_with_pbmm2_only(tmp_path):
    pbmm2_dir = tmp_path / "pbmm2" / "sampleA"
    pbmm2_dir.mkdir(parents=True)
    (pbmm2_dir / "sampleA.reference_counts.tsv").write_text(
        "reference_id\tread_count\trelative_mapping_signal\n"
        "refA\t5\t1.0\n"
    )
    output_dir = tmp_path / "comparison"

    result = comparison_report.run_comparison_from_config(
        {
            "comparison": {
                "enabled": True,
                "output_dir": str(output_dir),
                "mothur_taxonomy_file": str(tmp_path / "missing.taxonomy"),
                "pbmm2_reference_counts_glob": str(tmp_path / "pbmm2" / "*" / "*.reference_counts.tsv"),
                "emu_abundance_file": str(tmp_path / "missing_emu.tsv"),
                "outputs": {
                    "cross_mode_summary": True,
                    "method_presence_summary": True,
                    "interpretation_checklist": True,
                },
            }
        }
    )

    assert result["enabled"] is True
    assert (output_dir / "cross_mode_summary.tsv").is_file()
    assert (output_dir / "method_presence_summary.tsv").is_file()
    assert (output_dir / "interpretation_checklist.md").is_file()
    summary = pd.read_csv(output_dir / "cross_mode_summary.tsv", sep="\t")
    assert summary["method"].tolist() == ["pbmm2_mapping"]


def test_downstream_router_supports_comparison_mode(monkeypatch):
    calls = []
    monkeypatch.setattr(
        downstream_router,
        "run_comparison_from_config",
        lambda config, force=False: calls.append(("comparison", force)) or {"mode": "comparison"},
    )

    result = downstream_router.route_downstream(
        {"downstream": {"mode": "comparison", "allowed_modes": ["comparison"]}}
    )

    assert calls == [("comparison", True)]
    assert result == [{"mode": "comparison"}]


def test_cli_accepts_compare_subcommand(monkeypatch):
    from kinnex16s import cli

    monkeypatch.setattr(sys, "argv", ["kinnex16s", "compare", "--help"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
