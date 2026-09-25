"""Tests for invst.config module."""

from pathlib import Path

import pytest

from invst.config import (
    Config,
    get_config,
    validate_scoring_weights,
)


def test_get_project_root(project_root: Path) -> None:
    """Test that project root is found and contains pyproject.toml."""
    assert project_root.is_dir()
    assert (project_root / "pyproject.toml").is_file()
    assert (project_root / "config" / "settings.yaml").is_file()


def test_config_loading_and_dotted_access(sample_config: Config) -> None:
    """Test dotted access to settings, scoring weights, and sector mappings."""
    # Settings
    assert sample_config.project.name == "invst"
    assert isinstance(sample_config.database.path, Path)
    assert sample_config.database.wal_mode is True
    assert sample_config.universe.index == "nifty_500"
    assert sample_config.constraints.max_holdings == 8

    # Scoring weights
    assert sample_config.scoring_weights.quality.roe_5yr_avg == 0.25
    assert sample_config.scoring_weights.valuation.pe_ttm == 0.30
    assert sample_config.scoring_weights.risk.annualised_vol_252d == 0.25
    assert sample_config.scoring_weights.composite.quality == 0.35

    # Direct access to stages
    assert sample_config.quality.roe_5yr_avg == 0.25
    assert sample_config.valuation.pe_ttm == 0.30

    # Sectors
    assert "financial_services" in sample_config.sectors
    assert sample_config.sectors.financial_services.display_name == "Financial Services"
    assert "Banks - Private" in sample_config.sectors.financial_services.sub_sectors


def test_config_singleton(project_root: Path) -> None:
    """Test that get_config caches the singleton instance and respects reload."""
    cfg1 = get_config(project_root=project_root)
    cfg2 = get_config(project_root=project_root)
    assert cfg1 is cfg2

    cfg3 = get_config(project_root=project_root, reload=True)
    assert cfg3 is not None
    assert cfg3.project.name == "invst"


def test_config_immutability(sample_config: Config) -> None:
    """Test that Config and its nodes cannot be mutated."""
    with pytest.raises(TypeError):
        sample_config.database = "something_else"  # type: ignore[misc]

    with pytest.raises(TypeError):
        sample_config.database.path = "/new/path"  # type: ignore[misc]

    with pytest.raises(TypeError):
        sample_config["database"] = {}  # type: ignore[index]

    with pytest.raises(TypeError):
        del sample_config["database"]  # type: ignore[attr-defined]


def test_env_var_overrides(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that environment variables override configuration values."""
    test_db = str(project_root / "db" / "custom_test.db")
    monkeypatch.setenv("INVST_DB_PATH", test_db)
    monkeypatch.setenv("INVST_LOG_LEVEL", "DEBUG")

    cfg = get_config(project_root=project_root, reload=True)
    assert str(cfg.database.path) == str(Path(test_db).resolve())
    assert cfg.logging.level == "DEBUG"


def test_validate_scoring_weights() -> None:
    """Test that invalid scoring weights raise ValueError."""
    invalid_weights = {
        "quality": {
            "factor1": 0.6,
            "factor2": 0.5,  # sum = 1.1 != 1.0
        }
    }
    with pytest.raises(ValueError, match="Scoring weights for stage 'quality' must sum to 1.0"):
        validate_scoring_weights(invalid_weights)


def test_config_to_dict(sample_config: Config) -> None:
    """Test exporting config back to standard Python dict."""
    as_dict = sample_config.to_dict()
    assert isinstance(as_dict, dict)
    assert as_dict["project"]["name"] == "invst"
    assert "scoring_weights" in as_dict
