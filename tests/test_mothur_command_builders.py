from kinnex16s.mothur_runner import (
    build_align_seqs_expression,
    build_chimera_vsearch_expression,
    build_classify_seqs_expression,
    build_filter_seqs_expression,
    build_precluster_expression,
    build_remove_lineage_expression,
    build_screen_length_expression,
    build_unique_seqs_expression,
    expected_screen_outputs,
    expected_with_tag,
)


def test_screen_seqs_with_maxambig_and_maxhomop():
    assert build_screen_length_expression(
        fasta="combined.fasta",
        group="combined.groups",
        count=None,
        min_length=1000,
        max_length=3000,
        maxambig=0,
        maxhomop=12,
        processors=16,
    ) == (
        "screen.seqs(fasta=combined.fasta, group=combined.groups, minlength=1000, "
        "maxlength=3000, maxambig=0, maxhomop=12, processors=16)"
    )


def test_unique_seqs_command():
    assert build_unique_seqs_expression("combined.good.fasta") == "unique.seqs(fasta=combined.good.fasta)"


def test_align_seqs_command():
    assert build_align_seqs_expression("combined.unique.fasta", "silva.fasta", 16) == (
        "align.seqs(fasta=combined.unique.fasta, reference=silva.fasta, processors=16)"
    )


def test_filter_seqs_command():
    assert build_filter_seqs_expression("combined.align.good.fasta", True, ".", 16) == (
        "filter.seqs(fasta=combined.align.good.fasta, vertical=T, trump=., processors=16)"
    )


def test_precluster_command():
    assert build_precluster_expression(
        "combined.filter.fasta",
        "combined.names",
        None,
        None,
        1,
        16,
    ) == (
        "pre.cluster(fasta=combined.filter.fasta, name=combined.names, "
        "diffs_per_100bp=1, processors=16)"
    )


def test_chimera_vsearch_command():
    assert build_chimera_vsearch_expression(
        "combined.precluster.fasta",
        "combined.precluster.names",
        None,
        True,
        16,
    ) == (
        "chimera.vsearch(fasta=combined.precluster.fasta, name=combined.precluster.names, "
        "dereplicate=T, processors=16)"
    )


def test_classify_seqs_with_optional_cutoff():
    assert build_classify_seqs_expression(
        fasta="combined.good.fasta",
        group="combined.good.groups",
        count=None,
        reference="ref.fna",
        taxonomy="ref.tax",
        method="knn",
        numwanted=1,
        search="blastplus",
        cutoff=80,
        processors=16,
    ) == (
        "classify.seqs(fasta=combined.good.fasta, group=combined.good.groups, "
        "reference=ref.fna, taxonomy=ref.tax, method=knn, numwanted=1, "
        "search=blastplus, cutoff=80, processors=16)"
    )


def test_remove_lineage_command():
    assert build_remove_lineage_expression(
        fasta="combined.good.fasta",
        taxonomy="combined.taxonomy",
        group="combined.good.groups",
        count=None,
        taxon="Chloroplast-Mitochondria",
    ) == (
        "remove.lineage(fasta=combined.good.fasta, taxonomy=combined.taxonomy, "
        "group=combined.good.groups, taxon=Chloroplast-Mitochondria)"
    )


def test_expected_output_naming_assumptions():
    assert expected_screen_outputs("combined.fasta", "combined.groups") == (
        "combined.good.fasta",
        "combined.good.groups",
    )
    assert expected_with_tag("combined.good.fasta", "align") == "combined.good.align.fasta"
    assert expected_with_tag("combined.good.align.fasta", "filter") == "combined.good.align.filter.fasta"
    assert expected_with_tag("combined.good.align.filter.fasta", "precluster") == (
        "combined.good.align.filter.precluster.fasta"
    )
