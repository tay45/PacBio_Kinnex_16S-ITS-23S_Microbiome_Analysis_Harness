import pytest

from kinnex16s import downstream_router


def test_valid_downstream_mode_emu_abundance():
    assert downstream_router.expand_downstream_mode("emu_abundance") == ["emu_abundance"]


def test_valid_downstream_mode_all():
    assert downstream_router.expand_downstream_mode("all") == [
        "mothur",
        "pbmm2_mapping",
        "emu_abundance",
    ]


def test_invalid_downstream_mode_rejection():
    with pytest.raises(ValueError, match="Invalid downstream mode"):
        downstream_router.expand_downstream_mode("not_a_mode")


def test_router_calls_emu_only_for_emu_abundance(monkeypatch):
    calls = []

    monkeypatch.setattr(
        downstream_router,
        "run_mothur_from_config",
        lambda config: calls.append("mothur") or {"mode": "mothur"},
    )
    monkeypatch.setattr(
        downstream_router,
        "run_pbmm2_mapping_from_config",
        lambda config: calls.append("pbmm2_mapping") or {"mode": "pbmm2_mapping"},
    )
    monkeypatch.setattr(
        downstream_router,
        "run_emu_from_config",
        lambda config: calls.append("emu_abundance") or {"mode": "emu_abundance"},
    )

    results = downstream_router.route_downstream(
        {"downstream": {"mode": "emu_abundance", "allowed_modes": ["emu_abundance"]}}
    )

    assert calls == ["emu_abundance"]
    assert results == [{"mode": "emu_abundance"}]


def test_router_calls_all_routes_for_all(monkeypatch):
    calls = []

    monkeypatch.setattr(
        downstream_router,
        "run_mothur_from_config",
        lambda config: calls.append("mothur") or {"mode": "mothur"},
    )
    monkeypatch.setattr(
        downstream_router,
        "run_pbmm2_mapping_from_config",
        lambda config: calls.append("pbmm2_mapping") or {"mode": "pbmm2_mapping"},
    )
    monkeypatch.setattr(
        downstream_router,
        "run_emu_from_config",
        lambda config: calls.append("emu_abundance") or {"mode": "emu_abundance"},
    )

    results = downstream_router.route_downstream(
        {"downstream": {"mode": "all", "allowed_modes": ["mothur", "pbmm2_mapping", "emu_abundance", "both", "all"]}}
    )

    assert calls == ["mothur", "pbmm2_mapping", "emu_abundance"]
    assert [result["mode"] for result in results] == ["mothur", "pbmm2_mapping", "emu_abundance"]


def test_router_still_calls_mothur_for_mothur_mode(monkeypatch):
    calls = []

    monkeypatch.setattr(
        downstream_router,
        "run_mothur_from_config",
        lambda config: calls.append("mothur") or {"mode": "mothur"},
    )

    results = downstream_router.route_downstream(
        {"downstream": {"mode": "mothur", "allowed_modes": ["mothur"]}}
    )

    assert calls == ["mothur"]
    assert results == [{"mode": "mothur"}]
