# Downstream Routing

The YAML downstream router supports five modes:

```yaml
downstream:
  mode: mothur
  allowed_modes:
    - mothur
    - pbmm2_mapping
    - emu_abundance
    - comparison
    - validation
    - report
    - both
    - all
```

## Modes

`mothur` runs classical amplicon sequence filtering and taxonomy classification with `summary.seqs`, `screen.seqs`, `classify.seqs`, and optional `remove.lineage`.

The mothur route is YAML-configurable. The conservative default route is `summary.seqs -> screen.seqs length filtering -> classify.seqs`, with optional lineage removal. Additional mothur SOP-inspired steps such as `unique.seqs`, `align.seqs`, `filter.seqs`, `pre.cluster`, and `chimera.vsearch` are available but disabled by default for PacBio Kinnex full-length 16S-ITS-23S data.

`pbmm2_mapping` runs a PacBio-native reference-guided alignment route. Its purpose is sorted/indexed BAM generation, filtered mapping QC, per-reference read-count summaries, and mapping-derived relative signal. It is not a taxonomic abundance estimator.

`emu_abundance` runs Emu for full-length 16S taxonomic relative abundance estimation. It is intended for full-length 16S-compatible reads and is not a general 16S-ITS-23S mapper.

pbmm2 and Emu should not be conflated. Emu remains the abundance-estimation route; pbmm2 reports reference-guided alignment signal.

`both` preserves backward-compatible meaning: `mothur` plus `pbmm2_mapping`.

`all` runs `mothur`, `pbmm2_mapping`, and `emu_abundance`.

When `comparison.enabled` is true, `all` also runs the comparison report. `comparison` can also be selected explicitly to run comparison only.
When `validation.enabled` is true, `all` also runs validation reporting. `validation` can also be selected explicitly to run validation only.
When `report.enabled` is true, `all` also generates the HTML report. `report` can also be selected explicitly to generate only the report.

## Commands

```bash
kinnex16s downstream --config config/project.example.yaml
kinnex16s emu --config config/project.example.yaml
kinnex16s compare --config config/project.example.yaml
kinnex16s validate --config config/project.example.yaml
kinnex16s report --config config/project.example.yaml
```

The original direct commands remain available:

```bash
kinnex16s mothur --combined-fasta results/preprocess/combined.fasta ...
python3 mothur_processing.py --combined-fasta results/preprocess/combined.fasta ...
```
