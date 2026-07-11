# Mock-Community Validation Report

The validation layer compares observed method-specific outputs against a user-provided expected taxa/reference table.

It can use:

- `comparison` cross-mode summary output
- `pbmm2_mapping` reference-count summaries
- `emu_abundance` abundance tables
- conservative mothur taxonomy/classification outputs

Validation can be presence/absence-based or relative-signal aware when `expected_relative_abundance` is supplied. The output is descriptive: recovery_fraction is not a universal sensitivity estimate, missing expected taxa are not automatically false negatives, and unexpected observed taxa are not automatically false positives.

## YAML

```yaml
validation:
  enabled: false
  output_dir: results/validation
  expected_taxa_file: config/expected_taxa.example.tsv
  match_mode: case_insensitive_exact
  observed:
    comparison_summary: results/comparison/cross_mode_summary.tsv
    pbmm2_reference_counts_glob: results/pbmm2_mapping/*/*.reference_counts.tsv
    emu_abundance_file: results/emu_abundance/emu_abundance.tsv
    mothur_taxonomy_file: results/mothur/combined.good.database_reference.knn.taxonomy
```

## Outputs

- `expected_taxa_recovery.tsv`
- `missing_expected_taxa.tsv`
- `unexpected_taxa.tsv`
- `method_validation_summary.tsv`
- `validation_interpretation_checklist.md`
- `validation_manifest.json`

Mock-community validation depends on the quality of the expected table, database, assay design, sequencing depth, and thresholds. It supports review; it does not replace expert interpretation.
