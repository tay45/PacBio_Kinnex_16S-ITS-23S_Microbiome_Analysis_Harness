# Reproducible Execution

This project is packaged as a Python harness with lightweight test fixtures and workflow scaffolds. The repository does not include large sequencing files or private infrastructure paths.

## Local Python

```bash
python -m compileall -q .
PYTHONPATH=src pytest -q
```

## CLI

```bash
PYTHONPATH=src python -m kinnex16s downstream --config config/project.example.yaml
PYTHONPATH=src python -m kinnex16s compare --config config/project.example.yaml
PYTHONPATH=src python -m kinnex16s validate --config config/project.example.yaml
PYTHONPATH=src python -m kinnex16s report --config config/project.example.yaml
```

## Snakemake Dry Run

```bash
snakemake -s workflows/Snakefile -n
```

Production workflow execution requires real input files and the external tools required by the selected route.

## Docker

```bash
docker build -t kinnex16s-harness .
docker run --rm kinnex16s-harness
```

The Dockerfile installs Python dependencies and the harness in editable mode. It does not automatically install PacBio or other external bioinformatics tools such as Skera, Lima, pbmm2, samtools, mothur, or Emu.
