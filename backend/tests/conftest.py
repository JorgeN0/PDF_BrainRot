from dataclasses import replace

import pytest

from app import config
from app.pipeline import backgrounds


@pytest.fixture
def tmp_settings(tmp_path, monkeypatch):
    """Point every module that reads settings at a throwaway data/backgrounds folder."""
    s = replace(
        config.settings,
        data_dir=tmp_path / "data",
        backgrounds_dir=tmp_path / "backgrounds",
    )
    s.backgrounds_dir.mkdir()
    s.jobs_dir.mkdir(parents=True)
    monkeypatch.setattr(backgrounds, "settings", s)
    return s
