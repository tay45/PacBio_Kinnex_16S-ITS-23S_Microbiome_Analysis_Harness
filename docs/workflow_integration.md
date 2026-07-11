# Workflow Integration

`workflows/Snakefile` is a reproducible scaffold for tying the harness CLI into a workflow manager.

Rules:

- `preprocess`
- `downstream`
- `compare`
- `validate`
- `report`
- `all`

The scaffold is dry-run friendly and intentionally does not claim to be a complete production workflow. Production runs require real PacBio input files, route-specific reference databases, and installed external tools.

The suggested command for inspection is:

```bash
snakemake -s workflows/Snakefile -n
```

Use this scaffold as the starting point for site-specific Snakemake or Nextflow deployment.
