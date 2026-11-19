"""Guards the row -> dict mapping of the three job sources: every source's SELECT must line up with COLUMNS."""

import pytest

from app.core.db import get_conn
from app.jobs import repository
from app.jobs.repository import COLUMNS, SOURCES, load_jobs, source_counts

DERIVED = {"role", "salary_annual_mid", "source"}


@pytest.mark.parametrize("source", list(SOURCES))
def test_each_source_selects_exactly_the_columns_in_order(source):
    with get_conn() as conn:
        cur = conn.execute(SOURCES[source]["sql"] + " LIMIT 0")
        assert [c.name for c in cur.description] == COLUMNS


@pytest.mark.parametrize("source", list(SOURCES))
def test_a_loaded_job_has_the_same_keys_for_every_source(source):
    for d in load_jobs(source)[:20]:
        assert set(d) == set(COLUMNS) | DERIVED
        assert d["source"] == source


def test_source_counts_cover_every_source():
    assert [c["key"] for c in source_counts()] == list(repository.SOURCES)
