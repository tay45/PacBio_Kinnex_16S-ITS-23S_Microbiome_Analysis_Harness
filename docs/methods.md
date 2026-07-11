# Methods

## PacBio Preprocessing

The preprocessing command accepts a PacBio HiFi BAM and optional Kinnex adapter FASTA. When Skera is enabled, the harness runs `skera split` before Lima demultiplexing. Lima is then run with the supplied Kinnex barcode FASTA and either symmetric or asymmetric barcode mode.

Demultiplexed BAM files are validated against the Kinnex barcode filename pattern:

```text
Kinnex16S_Fwd_XX--Kinnex16S_Rev_YY.bam
```

Files with invalid names, zero file size, or barcodes absent from the sample sheet are moved into `invalid_files/` and recorded in `invalid_files_report.csv`.

## Sample Tracking

The sample sheet may be comma- or tab-delimited. Required `Barcode` and `Sample Name` columns are matched case-insensitively after trimming whitespace. Duplicate barcodes and duplicate sample names are rejected.

## FASTA and Group Generation

For FASTA conversion runs, the harness indexes each FASTA with `samtools faidx`, then builds:

- `combined.fasta`
- `combined.groups`

Sequence IDs are rewritten with sample names to keep mothur group assignments unique and traceable.

## mothur Processing

The direct mothur command preserves the simple route:

1. `summary.seqs`
2. `screen.seqs` with default length bounds of 1000-3000 bp and `maxambig=0`
3. `classify.seqs` using the filtered `*.good.fasta` and `*.good.groups`
4. optional `remove.lineage`

The runner checks that expected filtered FASTA, group, and taxonomy outputs exist before continuing.

The YAML-configured mothur route can additionally toggle `unique.seqs`, `align.seqs`, alignment-coordinate screening, `filter.seqs`, `pre.cluster`, `chimera.vsearch`, `make.shared`, and `classify.otu`. These steps are disabled by default because PacBio Kinnex full-length 16S-ITS-23S assays require parameter choices appropriate to the assay, reference database, and read structure. The defaults are not Illumina MiSeq SOP defaults.

## Downstream Routing

The harness now separates downstream strategies into three scientific routes:

- `mothur`: sequence filtering and taxonomy classification.
- `pbmm2_mapping`: PacBio-native reference-guided alignment, sorted/indexed BAM generation, mapping QC, per-reference read counts, and mapping-derived relative signal.
- `emu_abundance`: full-length 16S taxonomic relative abundance estimation using Emu.

`pbmm2_mapping` and `emu_abundance` are not interchangeable. pbmm2 creates reference-guided alignments; Emu estimates relative abundance from full-length 16S-compatible reads using an expectation-maximization approach.

## pbmm2 Filtered Mapping QC

The pbmm2 route aligns each input BAM to a configured reference index and summarizes filtered primary alignments. Filters include MAPQ, identity from the `NM` tag, query coverage, and alignment length. Per-reference counts are converted to mapping-derived relative signal by dividing each filtered reference count by the total filtered assigned reads.

This route does not infer absolute abundance and does not overclaim species or strain certainty from mapping alone.

## Cross-Mode Comparison

The comparison route normalizes available mothur, pbmm2_mapping, and Emu outputs into comparison-ready tables. It is intended for side-by-side review, not for proving biological truth. Missing method outputs are recorded in a method-presence table rather than treated as failures.

## Mock-Community Validation

The validation route compares observed method-specific outputs against a user-provided expected taxa/reference table. It reports expected taxa recovery, missing expected taxa, unexpected observed taxa, and method-level descriptive summaries. Recovery_fraction is descriptive and should not be interpreted as universal sensitivity without a validated truth set.

## Reproducible Packaging

The repository includes a lightweight Dockerfile, Python requirements, Conda environment file, Snakemake scaffold, and tiny synthetic text fixtures. These support reproducible testing and portfolio review without distributing large sequencing files or private infrastructure details.

## HTML Report

The report route renders available method-specific outputs, comparison summaries, validation summaries, and interpretation notes into a portable HTML file. It is a human-readable summary layer and does not replace expert interpretation.
