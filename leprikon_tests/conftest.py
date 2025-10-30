from locale import LC_ALL, setlocale
from typing import Generator

import pytest


@pytest.fixture
def locale_cs_CZ() -> Generator[None, None, None]:
    prev_locale = setlocale(LC_ALL)
    setlocale(LC_ALL, "cs_CZ.utf8")
    yield
    setlocale(LC_ALL, prev_locale)
