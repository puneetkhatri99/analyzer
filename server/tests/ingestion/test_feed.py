from app.ingestion.feed import parse_salary


def test_parse_salary():
    assert parse_salary("85,000-100,000 per year") == {
        "salary_min": 85000,
        "salary_max": 100000,
        "salary_period": "year",
    }
    assert parse_salary("17-22.5 per Hour") == {"salary_min": 17, "salary_max": 22.5, "salary_period": "hour"}
    assert parse_salary("70304 per year") == {"salary_min": 70304, "salary_max": 70304, "salary_period": "year"}
    assert (
        parse_salary("Competitive")
        == parse_salary(None)
        == {"salary_min": None, "salary_max": None, "salary_period": None}
    )
