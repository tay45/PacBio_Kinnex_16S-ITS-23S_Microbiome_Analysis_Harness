from kinnex16s import mothur_runner


def _base_config(tmp_path, steps):
    return {
        "mothur": {
            "enabled": True,
            "mothur_path": "mothur",
            "processors": 16,
            "combined_fasta": "results/preprocess/combined.fasta",
            "combined_group": "results/preprocess/combined.groups",
            "output_dir": str(tmp_path / "mothur"),
            "log_file": str(tmp_path / "mothur" / "mothur.log"),
            "steps": steps,
            "screen_length": {
                "min_length": 1000,
                "max_length": 3000,
                "maxambig": 0,
                "maxhomop": None,
            },
            "classify": {
                "reference_fasta": "references/mothur/database_reference.fna",
                "taxonomy_file": "references/mothur/database_reference.tax",
                "method": "knn",
                "numwanted": 1,
                "search": "blastplus",
                "cutoff": None,
            },
        }
    }


def _patch_runtime_checks(monkeypatch):
    monkeypatch.setattr(mothur_runner, "resolve_tool", lambda tool, explicit_path=None: explicit_path or tool)
    monkeypatch.setattr(mothur_runner, "_require_existing", lambda paths, label: None)
    monkeypatch.setattr(mothur_runner, "_ensure_output", lambda path, step: None)


def test_configured_classify_route_no_extra_run_mothur_argument(monkeypatch, tmp_path):
    calls = []
    _patch_runtime_checks(monkeypatch)
    monkeypatch.setattr(
        mothur_runner,
        "_run_mothur",
        lambda mothur, expression, label: calls.append((mothur, expression, label)),
    )

    result = mothur_runner.run_configured_mothur_steps(
        _base_config(
            tmp_path,
            {
                "summary": False,
                "screen_length": False,
                "unique": False,
                "align": False,
                "screen_alignment": False,
                "filter_alignment": False,
                "precluster": False,
                "chimera_vsearch": False,
                "classify": True,
                "remove_lineage": False,
                "make_shared": False,
                "classify_otu": False,
            },
        )
    )

    assert result["steps_run"] == ["classify"]
    assert len(calls) == 1
    assert calls[0][2] == "classify.seqs"
    assert calls[0][1].startswith("classify.seqs(")
    assert "fasta=results/preprocess/combined.fasta" in calls[0][1]


def test_conservative_configured_route_uses_screen_outputs_for_classify(monkeypatch, tmp_path):
    calls = []
    _patch_runtime_checks(monkeypatch)
    monkeypatch.setattr(
        mothur_runner,
        "_run_mothur",
        lambda mothur, expression, label: calls.append((mothur, expression, label)),
    )

    result = mothur_runner.run_configured_mothur_steps(
        _base_config(
            tmp_path,
            {
                "summary": True,
                "screen_length": True,
                "unique": False,
                "align": False,
                "screen_alignment": False,
                "filter_alignment": False,
                "precluster": False,
                "chimera_vsearch": False,
                "classify": True,
                "remove_lineage": False,
                "make_shared": False,
                "classify_otu": False,
            },
        )
    )

    assert result["steps_run"] == ["summary", "screen_length", "classify"]
    assert [call[2] for call in calls] == ["summary.seqs", "screen.seqs length", "classify.seqs"]
    classify_expression = calls[-1][1]
    assert "fasta=results/preprocess/combined.good.fasta" in classify_expression
    assert "group=results/preprocess/combined.good.groups" in classify_expression
