import json
import sys
from pathlib import Path

import pytest

from kinnex16s import downstream_router, html_report

pd = pytest.importorskip("pandas")


def test_safe_read_table_returns_none_for_missing_file(tmp_path):
    assert html_report.safe_read_table(tmp_path / "missing.tsv") is None


def test_table_to_html_renders_and_truncates():
    df = pd.DataFrame({"col": [1, 2, 3]})

    rendered = html_report.table_to_html(df, max_rows=2)

    assert "<table" in rendered
    assert "Table truncated to 2 of 3 rows" in rendered


def test_markdown_to_html_handles_headings_bullets_and_paragraphs():
    rendered = html_report.markdown_to_html("# Title\n\n- item\n\nParagraph")

    assert "<h1>Title</h1>" in rendered
    assert "<li>item</li>" in rendered
    assert "<p>Paragraph</p>" in rendered


def test_collect_report_inputs_detects_found_and_missing(tmp_path):
    found = tmp_path / "found.tsv"
    found.write_text("a\tb\n1\t2\n")

    collected = html_report.collect_report_inputs(
        {
            "report": {
                "inputs": {
                    "method_presence_summary": str(found),
                    "cross_mode_summary": str(tmp_path / "missing.tsv"),
                }
            }
        }
    )

    assert any(item["key"] == "method_presence_summary" for item in collected["found"])
    assert any(item["key"] == "cross_mode_summary" for item in collected["missing"])


def test_generate_html_report_from_fixture_tables(tmp_path):
    fixtures = Path(__file__).resolve().parent / "fixtures"
    output = tmp_path / "report" / "kinnex16s_report.html"

    result = html_report.generate_html_report(
        {
            "report": {
                "enabled": True,
                "report_file": str(output),
                "title": "PacBio Kinnex 16S-ITS-23S Microbiome Analysis Harness Report",
                "inputs": {
                    "method_presence_summary": str(fixtures / "method_presence_summary.example.tsv"),
                    "cross_mode_summary": str(fixtures / "cross_mode_summary.example.tsv"),
                    "interpretation_checklist": str(fixtures / "missing_interpretation.md"),
                    "validation_summary": str(fixtures / "method_validation_summary.example.tsv"),
                    "expected_taxa_recovery": str(fixtures / "expected_taxa_recovery.example.tsv"),
                    "missing_expected_taxa": str(fixtures / "missing_expected_taxa.example.tsv"),
                    "unexpected_taxa": str(fixtures / "unexpected_taxa.example.tsv"),
                    "validation_checklist": str(fixtures / "missing_validation.md"),
                    "pbmm2_qc_glob": str(fixtures / "mapping_qc.example.tsv"),
                    "pbmm2_counts_glob": str(fixtures / "pbmm2_reference_counts.example.tsv"),
                },
                "options": {"max_table_rows": 50, "include_css": True},
            }
        }
    )

    assert result["outputs"]["report_file"] == str(output)
    text = output.read_text()
    assert "PacBio Kinnex" in text
    assert "Architecture summary" in text
    assert "mapping-derived relative signal" in text
    assert "not absolute abundance" in text
    assert "Expected taxa recovery" in text


def test_downstream_router_supports_report_mode(monkeypatch):
    calls = []
    monkeypatch.setattr(
        downstream_router,
        "generate_html_report",
        lambda config, force=False: calls.append(("report", force)) or {"mode": "report"},
    )

    result = downstream_router.route_downstream(
        {"downstream": {"mode": "report", "allowed_modes": ["report"]}}
    )

    assert calls == [("report", True)]
    assert result == [{"mode": "report"}]


def test_cli_accepts_report_subcommand(monkeypatch):
    from kinnex16s import cli

    monkeypatch.setattr(sys, "argv", ["kinnex16s", "report", "--help"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0


def test_snakefile_contains_rule_report():
    snakefile = Path(__file__).resolve().parents[1] / "workflows" / "Snakefile"

    assert "rule report:" in snakefile.read_text()


def test_release_manifest_version_is_v170():
    manifest = json.loads((Path(__file__).resolve().parents[1] / "release_manifest.json").read_text())

    assert manifest["version"] == "1.7.0"
