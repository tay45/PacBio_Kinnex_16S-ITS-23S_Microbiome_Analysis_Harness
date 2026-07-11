import pytest

from kinnex16s.barcode_validation import extract_kinnex_barcode


def test_extract_valid_kinnex_barcode():
    barcode, status = extract_kinnex_barcode(
        "lima_output.Kinnex16S_Fwd_01--Kinnex16S_Rev_13.bam"
    )

    assert barcode == "Kinnex16S_Fwd_01--Kinnex16S_Rev_13"
    assert status == "Valid"


def test_detect_invalid_barcode_filename():
    barcode, status = extract_kinnex_barcode("lima_output.not_a_kinnex_barcode.bam")

    assert barcode == ""
    assert status == "Incorrect filename format"


@pytest.mark.parametrize(
    "filename",
    [
        "sample.Kinnex16S_Fwd_1--Kinnex16S_Rev_2.bam",
        "prefix.Kinnex16S_Fwd_001--Kinnex16S_Rev_384.bam",
    ],
)
def test_extract_barcode_accepts_numeric_widths(filename):
    barcode, status = extract_kinnex_barcode(filename)

    assert barcode.startswith("Kinnex16S_Fwd_")
    assert status == "Valid"
