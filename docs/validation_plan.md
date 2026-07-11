# Validation Plan

## Unit Tests

- Barcode extraction from Kinnex-formatted filenames.
- Invalid barcode filename detection.
- Sample sheet parsing for comma- and tab-delimited files.
- Duplicate barcode and sample name rejection.
- Group file header and combined FASTA/group generation.
- External command construction for Skera, Lima, BAM conversion, samtools, and mothur.

## Dry Runs

Use mock text fixtures for sample sheets and FASTA files. Avoid requiring real PacBio BAM files in unit tests.

## Integration Testing

Future integration tests should use a small synthetic or public fixture set with known barcode/sample assignments. The run should verify:

- Invalid file quarantine behavior.
- Expected FASTA/FASTQ outputs.
- `combined.fasta` and `combined.groups` integrity.
- mothur output presence after each stage.

## v1.1 Validation

pbmm2 mapping and Emu routes should add tests for route selection, command construction, manifest writing, and clear separation from the mothur taxonomy workflow.

## Downstream Router Tests

- Accept `emu_abundance`.
- Accept `all`.
- Reject invalid modes.
- Verify `emu_abundance` routes only to Emu.
- Verify `all` routes to mothur, pbmm2 mapping, and Emu.
- Verify CLI config subcommands parse without requiring real external tools.
