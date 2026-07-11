import pytest

from kinnex16s.emu_runner import build_emu_command, validate_emu_config


def test_emu_command_construction():
    assert build_emu_command(
        "reads.fastq",
        "emu_db",
        "results/emu",
        16,
        emu_path="emu",
        min_abundance=0.0001,
        keep_intermediate=False,
    ) == [
        "emu",
        "abundance",
        "--db",
        "emu_db",
        "--output-dir",
        "results/emu",
        "--threads",
        "16",
        "--min-abundance",
        "0.0001",
        "reads.fastq",
    ]


def test_emu_command_keeps_intermediate_files():
    command = build_emu_command(
        "reads.fastq",
        "emu_db",
        "results/emu",
        4,
        keep_intermediate=True,
    )

    assert "--keep-files" in command


def test_emu_config_validation():
    settings = validate_emu_config(
        {
            "emu_abundance": {
                "input_fastq": "reads.fastq",
                "database_dir": "emu_db",
                "output_dir": "results/emu",
                "threads": 16,
                "input_assumption": "full_length_16s",
                "require_16s_only_input": True,
                "min_abundance": 0.0001,
            }
        }
    )

    assert settings["threads"] == 16
    assert settings["input_assumption"] == "full_length_16s"


def test_emu_config_rejects_non_16s_input_when_required():
    with pytest.raises(ValueError, match="full_length_16s"):
        validate_emu_config(
            {
                "emu_abundance": {
                    "input_fastq": "reads.fastq",
                    "database_dir": "emu_db",
                    "output_dir": "results/emu",
                    "input_assumption": "16s_its_23s_composite",
                    "require_16s_only_input": True,
                }
            }
        )
