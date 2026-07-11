# Emu Abundance Mode

`emu_abundance` is a full-length 16S taxonomic relative abundance route using Emu. It is intentionally separate from `pbmm2_mapping`.

Emu is intended here for full-length 16S-compatible reads. For PacBio Kinnex 16S-ITS-23S composite constructs, users should provide a validated full-length 16S-compatible input or a trimmed input before using this route.

## Assumed Command Syntax

The harness isolates Emu command construction in `src/kinnex16s/emu_runner.py`. This pass assumes the following conservative syntax:

```bash
emu abundance \
  --db references/emu_database \
  --output-dir results/emu_abundance \
  --threads 16 \
  --min-abundance 0.0001 \
  results/preprocess/combined.fastq
```

If your installed Emu version uses different flags, update `build_emu_command` and its tests in one place.

## Outputs

The harness runs Emu and writes:

- `results/emu_abundance/emu_run_manifest.json`
- expected Emu output paths in the manifest

It does not fabricate Emu results and does not interpret biological output tables in this pass.

## Limitations

- Emu relative abundance estimates are not absolute abundance.
- Estimates depend on database completeness and input compatibility.
- Emu is not a replacement for pbmm2 BAM alignment.
- Emu should not be treated as a general 16S-ITS-23S mapper.
