# Configurable mothur Options

The YAML-driven mothur route is a sequence filtering and taxonomy classification route. It is not an abundance estimator.

Defaults are conservative for PacBio Kinnex full-length 16S-ITS-23S data:

```yaml
mothur:
  enabled: true
  steps:
    summary: true
    screen_length: true
    classify: true
```

Additional mothur SOP-inspired steps are available but disabled by default:

- `unique.seqs`
- `align.seqs`
- alignment-coordinate `screen.seqs`
- `filter.seqs`
- `pre.cluster`
- `chimera.vsearch`
- `make.shared`
- `classify.otu`

These options are not blindly copied from Illumina MiSeq SOP defaults. Users must tune length, alignment, precluster, chimera, OTU, and reference-database parameters for their assay, reference database, and read structure.

## Conservative Route

```yaml
mothur:
  enabled: true
  mothur_path: mothur
  processors: 16
  combined_fasta: results/preprocess/combined.fasta
  combined_group: results/preprocess/combined.groups
  output_dir: results/mothur
  log_file: results/mothur/mothur_processing.log
  steps:
    summary: true
    screen_length: true
    unique: false
    align: false
    screen_alignment: false
    filter_alignment: false
    precluster: false
    chimera_vsearch: false
    classify: true
    remove_lineage: false
    make_shared: false
    classify_otu: false
  screen_length:
    min_length: 1000
    max_length: 3000
    maxambig: 0
    maxhomop: null
  classify:
    reference_fasta: references/mothur/database_reference.fna
    taxonomy_file: references/mothur/database_reference.tax
    method: knn
    numwanted: 1
    search: blastplus
    cutoff: null
```

## Expanded Route

This example enables dereplication, alignment, alignment screening, filtering, preclustering, and chimera checking. The numeric values are placeholders and must be tuned.

```yaml
mothur:
  enabled: true
  mothur_path: mothur
  processors: 16
  combined_fasta: results/preprocess/combined.fasta
  combined_group: results/preprocess/combined.groups
  output_dir: results/mothur_expanded
  log_file: results/mothur_expanded/mothur_processing.log
  steps:
    summary: true
    screen_length: true
    unique: true
    align: true
    screen_alignment: true
    filter_alignment: true
    precluster: true
    chimera_vsearch: true
    classify: true
    remove_lineage: true
    make_shared: false
    classify_otu: false
  screen_length:
    min_length: 1000
    max_length: 3000
    maxambig: 0
    maxhomop: null
  align:
    reference_fasta: references/mothur/alignment_reference.fasta
  screen_alignment:
    start: 100
    end: 25000
    maxhomop: null
  filter_alignment:
    vertical: true
    trump: "."
  precluster:
    diffs: null
    diffs_per_100bp: 1
  chimera_vsearch:
    dereplicate: true
  classify:
    reference_fasta: references/mothur/database_reference.fna
    taxonomy_file: references/mothur/database_reference.tax
    method: knn
    numwanted: 1
    search: blastplus
    cutoff: null
  remove_lineage:
    taxon: Chloroplast-Mitochondria
```

## Output Naming Assumptions

The runner checks expected mothur output paths after each enabled step. Because mothur output naming can vary by command and version, the harness fails with a clear message if an expected file is absent. Adjust `mothur_runner.py` if your mothur version emits different names.
