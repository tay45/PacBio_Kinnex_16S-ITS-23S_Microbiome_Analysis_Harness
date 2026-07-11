# Latest Release Notes

## 1.7.0

Adds automated portable HTML report generation.

Highlights:

- Adds `kinnex16s report --config ...`.
- Adds `report` downstream mode.
- Summarizes method presence, cross-mode output, pbmm2 QC, validation summaries, expected taxa recovery, missing expected taxa, unexpected observed taxa, interpretation notes, limitations, and file inventory.
- Keeps the report self-contained with embedded CSS and no external JavaScript.
- Preserves careful language around mapping-derived relative signal, validation recovery, and method-specific assumptions.

## 1.6.0

Adds reproducible packaging and workflow integration scaffolds.

Highlights:

- Adds Dockerfile and `.dockerignore`.
- Adds `requirements.txt` and updates `environment.yml`.
- Adds Snakemake scaffold under `workflows/`.
- Adds small synthetic comparison/validation fixtures.
- Adds integration-style tests for comparison and validation report generation.
- Adds reproducibility and workflow integration documentation.

## 1.5.0

Adds mock-community / expected-taxa validation reporting.

Highlights:

- Adds `kinnex16s validate --config ...`.
- Adds `validation` downstream mode.
- Compares observed method-specific outputs against a user-provided expected taxa/reference table.
- Writes expected taxa recovery, missing expected taxa, unexpected taxa, method validation summary, interpretation checklist, and manifest outputs.
- Keeps recovery_fraction descriptive and avoids sensitivity/false-positive claims unless users provide and define a truth set.

## 1.4.0

Adds cross-mode comparison reporting for available mothur, pbmm2_mapping, and Emu outputs.

Highlights:

- Adds `kinnex16s compare --config ...`.
- Adds `comparison` downstream mode.
- Produces `cross_mode_summary.tsv`, `method_presence_summary.tsv`, and `interpretation_checklist.md`.
- Gracefully handles missing method outputs.
- Keeps method assumptions separate for side-by-side review.

## 1.3.1

Documentation hotfix for stale pbmm2 wording.

Highlights:

- Replaces outdated statements that pbmm2 reference mapping is not implemented.
- Clarifies that pbmm2_mapping implements reference-guided alignment and filtered mapping QC.
- Reiterates that pbmm2 does not perform probabilistic multi-mapper resolution or taxonomic abundance estimation.

## 1.3.0

Adds robust pbmm2 filtered mapping QC and per-reference assignment summaries.

Highlights:

- Adds pbmm2 index, align, and samtools index command builders.
- Adds pysam-based alignment identity, query coverage, alignment length, and filter helpers.
- Adds per-sample `reference_counts.tsv`, `mapping_qc.tsv`, `filtered_assignments.tsv`, and `unmapped_read_ids.txt` outputs.
- Reports mapping-derived relative signal, not absolute abundance.
- Implements only `best_hit` multi-mapper handling in this version.
- Keeps Emu as the abundance-estimation route and pbmm2 as the reference-guided alignment/QC route.

## 1.2.1

Hotfix for configured mothur runtime correctness and regression coverage.

Highlights:

- Verifies the YAML-configured `classify.seqs` route calls `_run_mothur(mothur, expression, label)` with exactly the expected argument shape.
- Adds regression coverage for classify-only configured mothur routing.
- Adds regression coverage for the conservative configured route: `summary -> screen_length -> classify`.
- Pins expected mothur output naming assumptions for `screen.seqs`, `align.seqs`, `filter.seqs`, `pre.cluster`, and `classify.seqs`.

## 1.2.0

Adds YAML-configurable mothur step routing while preserving the direct mothur CLI route.

Highlights:

- Adds toggles and parameters for `summary.seqs`, length `screen.seqs`, `unique.seqs`, `align.seqs`, alignment screening, `filter.seqs`, `pre.cluster`, `chimera.vsearch`, `classify.seqs`, `remove.lineage`, `make.shared`, and `classify.otu`.
- Keeps conservative PacBio Kinnex full-length 16S-ITS-23S defaults: summary, length screening, classification.
- Keeps optional SOP-inspired mothur steps disabled by default.
- Preserves the fixed behavior where filtered `*.good.groups` is passed to `classify.seqs`.

## 1.1.0

Adds YAML-configurable downstream routing for `mothur`, `pbmm2_mapping`, `emu_abundance`, `both`, and `all`.

Highlights:

- Keeps mothur as the classical sequence filtering and taxonomy classification route.
- Adds pbmm2 mapping scaffolding as a PacBio-native reference-guided alignment route.
- Adds Emu abundance mode for full-length 16S-compatible taxonomic relative abundance estimation.
- Keeps pbmm2 and Emu scientifically distinct in code and documentation.
- Adds `kinnex16s downstream --config ...` and `kinnex16s emu --config ...`.
- Adds route and Emu command/config tests.

## 1.0.0

First professionalized harness release for the PacBio Kinnex 16S-ITS-23S Microbiome Analysis Harness.

Highlights:

- Preserves existing Skera, Lima, BAM-to-FASTA/FASTQ, combined FASTA/group, and mothur workflow behavior.
- Adds reusable Python modules under `src/kinnex16s`.
- Replaces practical shell-based subprocess calls with list-based command execution.
- Adds sample sheet delimiter detection for comma- and tab-delimited files.
- Adds case-insensitive required column matching for `Barcode` and `Sample Name`.
- Rejects duplicate barcodes and duplicate sample names.
- Skips combined FASTA/group generation for FASTQ-only conversion.
- Validates expected mothur outputs after `screen.seqs` and `classify.seqs`.
- Documents pbmm2 mapping as planned v1.1 work.
