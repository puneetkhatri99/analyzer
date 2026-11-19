from app.ingestion.feed import parse_salary

NONE = {"salary_min": None, "salary_max": None, "salary_period": None}


def pay(lo, hi, period):
    return {"salary_min": lo, "salary_max": hi, "salary_period": period}


def test_parse_salary():
    assert parse_salary("85,000-100,000 per year") == pay(85000, 100000, "year")
    assert parse_salary("17-22.5 per Hour") == pay(17, 22.5, "hour")
    assert parse_salary("70304 per year") == pay(70304, 70304, "year")
    assert parse_salary("1e+05-1.2e+05 per year") == pay(100000, 120000, "year")
    assert parse_salary("Competitive") == parse_salary(None) == NONE


def test_parse_salary_without_a_unit_and_other_periods():
    # the shapes the feed sends with no "per ...": the size tells hourly from yearly
    assert parse_salary("42000") == pay(42000, 42000, "year")
    assert parse_salary("19-23") == pay(19, 23, "hour")
    assert parse_salary("16.15") == pay(16.15, 16.15, "hour")
    assert parse_salary("$52,000 - $60,000") == pay(52000, 60000, "year")
    assert parse_salary("4000 per month") == pay(48000, 48000, "year")
    assert parse_salary("360-410 per week") == pay(18720, 21320, "year")
    # a day rate, a project fee, or a figure that isn't a believable wage gives no pay
    assert parse_salary("164 per day") == parse_salary("55-65000 per project") == NONE
    assert parse_salary("500 per month") == parse_salary("15 per year") == parse_salary("4000-5000") == NONE
