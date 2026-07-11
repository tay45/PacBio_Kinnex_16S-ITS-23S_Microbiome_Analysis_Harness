# Automated HTML Report

The HTML report is a human-readable summary layer. It summarizes available outputs from method-specific routes, comparison reports, and validation reports in one portable HTML file.

It does not replace expert interpretation and does not prove biological truth. Missing sections are allowed when a method was not run.

## YAML

```yaml
report:
  enabled: false
  output_dir: results/report
  report_file: results/report/kinnex16s_report.html
  title: PacBio Kinnex 16S-ITS-23S Microbiome Analysis Harness Report
```

## Command

```bash
PYTHONPATH=src python -m kinnex16s report --config config/project.example.yaml
```

The report is self-contained with embedded CSS and no external JavaScript or internet dependency. pbmm2 tables report mapping-derived relative signal, not absolute abundance. Validation recovery is descriptive and depends on the user-provided expected taxa table.
