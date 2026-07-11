# Cross-Mode Comparison Report

The comparison layer organizes outputs from mothur, pbmm2_mapping, and emu_abundance for side-by-side review. It does not prove biological truth and does not require all three methods to be present.

Each route answers a different question:

- `mothur`: sequence filtering and taxonomy classification.
- `pbmm2_mapping`: reference-guided alignment, mapping QC, and mapping-derived relative signal.
- `emu_abundance`: full-length 16S abundance estimation when input is compatible.

Agreement between routes can be supportive, but disagreement can arise from database differences, reference incompleteness, multi-mapping, PCR/primer bias, rRNA copy-number variation, and 16S-ITS-23S input compatibility.

## YAML

```yaml
comparison:
  enabled: false
  output_dir: results/comparison
  mothur_taxonomy_file: results/mothur/combined.good.database_reference.knn.taxonomy
  pbmm2_reference_counts_glob: results/pbmm2_mapping/*/*.reference_counts.tsv
  emu_abundance_file: results/emu_abundance/emu_abundance.tsv
  outputs:
    cross_mode_summary: true
    method_presence_summary: true
    interpretation_checklist: true
```

## Outputs

- `cross_mode_summary.tsv`: normalized comparison-ready rows from any available methods.
- `method_presence_summary.tsv`: which expected method outputs were found and normalized.
- `interpretation_checklist.md`: cautious interpretation guidance.

The comparison layer does not fabricate abundance values or infer taxonomic agreement. It preserves method labels so reviewers can compare assumptions explicitly.

The validation layer can consume `cross_mode_summary.tsv` for expected taxa recovery checks against a user-provided expected table.
