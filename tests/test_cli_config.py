from pathlib import Path

from kinnex16s.config import load_config


def test_cli_config_accepts_emu_abundance_mode(tmp_path):
    config = tmp_path / "project.yaml"
    config.write_text(
        "downstream:\n"
        "  mode: emu_abundance\n"
        "  allowed_modes:\n"
        "    - mothur\n"
        "    - pbmm2_mapping\n"
        "    - emu_abundance\n"
        "    - both\n"
        "    - all\n"
        "emu_abundance:\n"
        "  input_fastq: reads.fastq\n"
        "  database_dir: emu_db\n"
        "  output_dir: results/emu\n"
        "  input_assumption: full_length_16s\n"
    )

    loaded = load_config(config)

    assert loaded["downstream"]["mode"] == "emu_abundance"
    assert loaded["emu_abundance"]["input_fastq"] == "reads.fastq"


def test_example_project_config_loads():
    config_path = Path(__file__).resolve().parents[1] / "config" / "project.example.yaml"
    loaded = load_config(config_path)

    assert loaded["downstream"]["mode"] == "mothur"
    assert "emu_abundance" in loaded
