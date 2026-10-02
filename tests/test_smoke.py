"""Smoke tests: the package and its layers import cleanly."""

import f1companion
from f1companion import analysis, charts, data


def test_version_is_set() -> None:
    assert f1companion.__version__ == "0.1.0"


def test_layers_import() -> None:
    for module in (data, analysis, charts):
        assert module.__doc__
