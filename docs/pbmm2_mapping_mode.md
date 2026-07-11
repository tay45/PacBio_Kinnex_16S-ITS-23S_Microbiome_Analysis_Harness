# pbmm2 Mapping Mode

`pbmm2_mapping` is a PacBio-native reference-guided alignment and QC route. It is not a taxonomic abundance estimator.

The route can:

- build a pbmm2 reference index
- align each input BAM against a curated reference index
- write sorted/indexed BAM outputs
- filter alignments by MAPQ, identity, query coverage, alignment length, and primary-alignment status
- generate per-reference read-count summaries
- report mapping-derived relative signal
- write filtered assignment and unmapped-read tables

## Example

```yaml
pbmm2_mapping:
  enabled: false
  pbmm2_path: pbmm2
  samtools_path: samtools
  input_bam_dir: results/preprocess
  input_bams: []
  reference_fasta: references/curated_16s_its_23s_reference.fasta
  reference_index: references/curated_16s_its_23s_reference.mmi
  index_reference: true
  output_dir: results/pbmm2_mapping
  preset: CCS
  threads: 16
  filters:
    primary_only: true
    min_mapq: 20
    min_identity: 0.97
    min_query_coverage: 0.90
    min_alignment_length: 1000
    multimapper_policy: best_hit
  outputs:
    sorted_bam: true
    bam_index: true
    reference_counts: true
    relative_abundance: true
    mapping_qc: true
    filtered_assignments: true
    unmapped_read_ids: true
```

## Outputs

For each sample, the route writes:

- `<sample>.pbmm2.sorted.bam`
- `<sample>.pbmm2.sorted.bam.bai`
- `<sample>.reference_counts.tsv`
- `<sample>.mapping_qc.tsv`
- `<sample>.filtered_assignments.tsv`
- `<sample>.unmapped_read_ids.txt`

`reference_counts.tsv` reports `relative_mapping_signal`, which is the fraction of filtered assigned reads mapping to each reference. It is not absolute abundance.

## Filtering

Identity is calculated from the `NM` tag when available:

```text
identity = 1 - NM / aligned_query_length
```

If `NM` or aligned query length is missing, identity is not fabricated and the read fails identity filtering when `min_identity` is set.

Query coverage is:

```text
aligned_query_length / query_length
```

Filtering thresholds must be interpreted with the reference database, amplicon design, and read structure in mind.

## Multi-Mapping

v1.3 implements only `best_hit`. It does not implement probabilistic multi-mapper resolution or EM assignment. Emu remains the full-length 16S abundance-estimation route; pbmm2 and Emu should not be conflated.

The pbmm2_mapping route implements reference-guided alignment and filtered mapping QC, but it does not perform probabilistic multi-mapper resolution or taxonomic abundance estimation. Reference-count summaries report mapping-derived relative signal, not absolute abundance.
