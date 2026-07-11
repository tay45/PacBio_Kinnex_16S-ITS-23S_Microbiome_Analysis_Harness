from kinnex16s.mothur_runner import build_arg_parser


def test_direct_cli_parser_still_accepts_existing_arguments():
    parser = build_arg_parser()

    args = parser.parse_args(
        [
            "--combined-fasta",
            "combined.fasta",
            "--combined-group",
            "combined.groups",
            "--output-dir",
            "results/mothur",
            "--reference-fasta",
            "ref.fna",
            "--taxonomy-file",
            "ref.tax",
            "--log-file",
            "results/mothur/mothur.log",
        ]
    )

    assert args.combined_fasta == "combined.fasta"
    assert args.combined_group == "combined.groups"
    assert args.reference_fasta == "ref.fna"
    assert args.taxonomy_file == "ref.tax"
    assert args.min_length == 1000
    assert args.max_length == 3000
