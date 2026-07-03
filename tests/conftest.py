"""Fixtures compartidas: aísla ~/.flujo en un directorio temporal."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def hogar_flujo_temporal(tmp_path, monkeypatch):
    monkeypatch.setenv("FLUJO_HOME", str(tmp_path / "flujo-home"))
    return tmp_path / "flujo-home"
