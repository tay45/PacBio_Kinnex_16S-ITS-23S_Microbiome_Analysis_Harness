from kinnex16s.fasta_group_builder import build_group_header, combine_fasta_files


def test_group_file_header_generation():
    assert build_group_header() == "sequenceID\tgroup\n"


def test_combine_fasta_files_builds_group_file(tmp_path):
    fasta = tmp_path / "lima_output.Kinnex16S_Fwd_01--Kinnex16S_Rev_13.fasta"
    fasta.write_text(">read1\nACGT\n>read2\nTGCA\n")
    combined = tmp_path / "combined.fasta"
    groups = tmp_path / "combined.groups"

    combine_fasta_files(
        combined,
        groups,
        {"Kinnex16S_Fwd_01--Kinnex16S_Rev_13": "Sample A"},
        [fasta],
    )

    assert combined.read_text() == (
        ">read1_Sample_A_seq1\nACGT\n"
        ">read2_Sample_A_seq2\nTGCA\n"
    )
    assert groups.read_text() == (
        "sequenceID\tgroup\n"
        "read1_Sample_A_seq1\tSample A\n"
        "read2_Sample_A_seq2\tSample A\n"
    )
