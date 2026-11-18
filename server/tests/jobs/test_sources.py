import pytest
from fastapi import HTTPException

from app.jobs.router import chosen_sources


def test_one_or_several_sources():
    assert chosen_sources("json") == ["json"]
    assert chosen_sources("json,nonprofits,json") == ["json", "nonprofits"]


@pytest.mark.parametrize("bad", ["", "json,people", ","])
def test_unknown_or_empty_source_is_rejected(bad):
    with pytest.raises(HTTPException):
        chosen_sources(bad)
