from pathlib import Path

from kinnex16s.config import load_config
from kinnex16s.mothur_runner import default_mothur_steps


def test_loading_new_mothur_yaml_section():
    config_path = Path(__file__).resolve().parents[1] / "config" / "project.example.yaml"
    config = load_config(config_path)

    assert config["mothur"]["enabled"] is True
    assert config["mothur"]["processors"] == 16
    assert config["mothur"]["screen_length"]["min_length"] == 1000
    assert config["mothur"]["classify"]["reference_fasta"] == "references/mothur/database_reference.fna"


def test_default_enabled_steps():
    steps = default_mothur_steps({})

    assert steps["summary"] is True
    assert steps["screen_length"] is True
    assert steps["classify"] is True


def test_disabled_optional_steps_are_not_included():
    config_path = Path(__file__).resolve().parents[1] / "config" / "project.example.yaml"
    steps = default_mothur_steps(load_config(config_path)["mothur"])

    assert steps["unique"] is False
    assert steps["align"] is False
    assert steps["precluster"] is False
    assert steps["chimera_vsearch"] is False
    assert steps["make_shared"] is False
