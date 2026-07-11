import pytest

from kinnex16s.barcode_validation import parse_sample_sheet


def test_parse_comma_delimited_sample_sheet(tmp_path):
    path = tmp_path / "samples.csv"
    path.write_text(
        " Barcode , Sample Name \n"
        "Kinnex16S_Fwd_01--Kinnex16S_Rev_13,Sample A\n"
    )

    sheet = parse_sample_sheet(path)

    assert sheet.delimiter == ","
    assert sheet.barcode_to_sample["Kinnex16S_Fwd_01--Kinnex16S_Rev_13"] == "Sample A"


def test_parse_tab_delimited_sample_sheet(tmp_path):
    path = tmp_path / "samples.tsv"
    path.write_text(
        "barcode\tsample name\n"
        "Kinnex16S_Fwd_02--Kinnex16S_Rev_14\tSample_B\n"
    )

    sheet = parse_sample_sheet(path)

    assert sheet.delimiter == "\t"
    assert sheet.barcode_to_sample["Kinnex16S_Fwd_02--Kinnex16S_Rev_14"] == "Sample_B"


def test_reject_duplicate_barcodes(tmp_path):
    path = tmp_path / "samples.csv"
    path.write_text(
        "Barcode,Sample Name\n"
        "Kinnex16S_Fwd_01--Kinnex16S_Rev_13,Sample A\n"
        "Kinnex16S_Fwd_01--Kinnex16S_Rev_13,Sample B\n"
    )

    with pytest.raises(ValueError, match="Duplicate barcode"):
        parse_sample_sheet(path)


def test_reject_duplicate_sample_names(tmp_path):
    path = tmp_path / "samples.csv"
    path.write_text(
        "Barcode,Sample Name\n"
        "Kinnex16S_Fwd_01--Kinnex16S_Rev_13,Sample A\n"
        "Kinnex16S_Fwd_02--Kinnex16S_Rev_14,Sample A\n"
    )

    with pytest.raises(ValueError, match="Duplicate sample name"):
        parse_sample_sheet(path)


def test_reject_invalid_kinnex_barcode(tmp_path):
    path = tmp_path / "samples.csv"
    path.write_text("Barcode,Sample Name\nnot-a-barcode,Sample A\n")

    with pytest.raises(ValueError, match="invalid Kinnex barcode"):
        parse_sample_sheet(path)
