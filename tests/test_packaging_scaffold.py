import json
from pathlib import Path

from kinnex16s.config import load_config


ROOT = Path(__file__).resolve().parents[1]


def test_requirements_files_exist():
    assert (ROOT / "requirements.txt").is_file()
    assert (ROOT / "environment.yml").is_file()


def test_dockerfile_exists_and_installs_package_or_runs_tests():
    text = (ROOT / "Dockerfile").read_text()

    assert "pip install" in text
    assert "pytest" in text


def test_snakefile_has_required_rules():
    text = (ROOT / "workflows" / "Snakefile").read_text()

    for rule in ["all", "downstream", "compare", "validate"]:
        assert f"rule {rule}:" in text


def test_project_example_yaml_includes_comparison_and_validation_sections():
    config = load_config(ROOT / "config" / "project.example.yaml")

    assert "comparison" in config
    assert "validation" in config


def test_release_manifest_version_is_current():
    manifest = json.loads((ROOT / "release_manifest.json").read_text())

    assert manifest["version"] == "1.7.0"
