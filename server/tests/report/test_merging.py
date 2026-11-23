"""A search with too little pay is loosened one step at a time (location, size, denomination, role) and says what was
combined; thin rows of the bar charts are combined instead of dropped."""

from app.report import service as report
from app.report.groups import denomination_family, role_group


def job(role="Worship", state="Ohio", pay=50000, size=None, denom=None, hours="Full-Time", period="year"):
    return {
        "role": role,
        "state": state,
        "region": state,
        "country": "US",
        "hours": hours,
        "church_size": size,
        "denomination": denom,
        "salary_min": pay,
        "salary_max": pay,
        "salary_period": period,
        "pull_date": "2026-11-05",
    }


def kinds(r):
    return [m["kind"] for m in r["merged"]]


def test_a_search_with_enough_data_is_not_merged():
    r = report.build_report({"role": ["Worship"], "state": ["Ohio"]}, [job()] * 5)
    assert r["merged"] == [] and r["note"] is None and r["pay"]["typical"] == 50000


def test_a_denomination_is_a_family_and_is_widened_to_all_denominations_when_it_is_thin():
    family = "Baptist and evangelical churches"
    jobs = [job(denom="Baptist")] * 2 + [job(denom="Converge")] * 3 + [job(denom="Catholic")] * 9
    r = report.build_report({"denomination": [family]}, jobs)  # Baptist + Converge are one family: 5, enough
    assert r["merged"] == [] and r["pay"] is not None
    r = report.build_report({"denomination": ["Baptist"]}, jobs)  # an old link names a single denomination: its family
    assert r["filters"]["denomination"] == [family] and r["merged"] == []
    r = report.build_report({"denomination": ["Lutheran and Episcopal churches"]}, jobs)  # no such openings
    assert kinds(r) == ["denomination"] and "included all denominations" in r["note"]


def test_church_size_is_dropped_when_its_band_is_thin_and_old_links_map_to_the_two_bands():
    jobs = [job(size=300)] * 2 + [job(size=2000)] * 9
    r = report.build_report({"size": ["Under 1,000"]}, jobs)
    assert kinds(r) == ["size"] and "left out the church size" in r["note"]
    r = report.build_report({"size": ["250 to 999"]}, jobs)  # a link from the four-band days
    assert r["filters"]["size"] == ["Under 1,000"] and kinds(r) == ["size"]
    r = report.build_report({"size": ["5,000 or more"]}, jobs)
    assert r["filters"]["size"] == ["1,000 or more"] and r["merged"] == []


def test_role_is_combined_with_its_group_when_the_place_cannot_help():
    jobs = (
        [job(role="Associate Pastor")] * 2 + [job(role="Campus Pastor")] * 3 + [job(role="Worship", state="Texas")] * 9
    )
    r = report.build_report({"role": ["Associate Pastor"]}, jobs)  # no place chosen: only the role can be loosened
    assert kinds(r) == ["role"] and "Pastoral roles" in r["note"]
    r = report.build_report({"role": ["Associate Pastor"], "state": ["Ohio"]}, jobs)  # place first, then the role
    assert kinds(r) == ["state", "role"] and r["scope"] == "national"


def test_filters_are_loosened_in_order_location_then_size_then_denomination_then_role():
    ohio = [job(role="Associate Pastor", size=300, denom="Lutheran")] * 2
    elsewhere = [job(role="Worship", state="Texas", size=5000, denom="Baptist")] * 9
    r = report.build_report(
        {"role": ["Associate Pastor"], "state": ["Ohio"], "size": ["250 to 999"], "denomination": ["Lutheran"]},
        ohio + elsewhere,
    )
    assert kinds(r) == ["state", "size", "denomination", "role"]  # all four, in that order
    assert r["pay"] is not None and r["scope"] == "national"


def test_every_loosened_filter_is_listed_with_a_reason_and_no_search_is_left_without_a_figure():
    jobs = [
        job(role=role, state=state, denom=d)
        for role in ("Worship", "Finance")
        for state in ("Ohio", "Texas")
        for d in (None, "Baptist")
    ] * 3  # 24 jobs
    for role in ("Worship", "Finance", "Chaplain"):
        for state in ("Ohio", "Wyoming"):
            r = report.build_report({"role": [role], "state": [state], "denomination": ["Lutheran"]}, jobs)
            assert r["pay"] is not None
            assert all(m["text"] for m in r["merged"]) and (r["note"] is None) == (r["merged"] == [])


def test_thin_chart_rows_are_combined_not_dropped():
    jobs = (
        [job(role="Worship")] * 6
        + [job(role="Associate Pastor")] * 3
        + [job(role="Campus Pastor")] * 3  # two thin roles of one group: 6 together
        + [job(role="Finance")] * 5
    )
    rows = {r["name"]: r for r in report.build_report({}, jobs)["by_role"]}
    assert rows["Pastoral roles"]["merged"] == ["Associate Pastor", "Campus Pastor"]
    assert "Worship" in rows and rows["Worship"]["merged"] == []
    assert "Associate Pastor" not in rows


def test_thin_states_are_combined_into_their_region_and_a_chart_of_one_row_is_left_out():
    jobs = [job(state="Ohio")] * 7 + [job(state="Indiana")] * 3 + [job(state="Michigan")] * 3
    r = report.build_report({}, jobs)
    names = {x["name"]: x["merged"] for x in r["by_state"]}
    assert names == {"Ohio": [], "Midwest": ["Indiana", "Michigan"]}
    assert report.build_report({}, [job()] * 8)["by_denomination"] == []  # nothing to compare


def test_church_size_rows_are_the_two_bands():
    jobs = [job(size=100)] * 6 + [job(size=300)] * 2 + [job(size=2000)] * 3 + [job(size=9000)] * 5
    rows = report.build_report({}, jobs)["by_size"]
    assert [(r["name"], r["merged"]) for r in rows] == [("Under 1,000", []), ("1,000 or more", [])]


def test_comparison_with_national_falls_back_to_the_nearby_states():
    jobs = [job(state="Ohio")] * 2 + [job(state="Indiana")] * 6 + [job(state="Texas", pay=90000)] * 8
    v = report.build_report({"state": ["Ohio"]}, jobs)["vs_national"]
    assert v and v["area"] == "Ohio and nearby states" and v["area_typical"] < v["national_typical"]


def test_groups_cover_the_names_the_app_produces():
    from app.jobs.roles import HIDDEN_ROLES, ROLE_LABELS

    assert {role_group(r) for r in ROLE_LABELS if r not in HIDDEN_ROLES and r != "Other"} <= {
        "Pastoral roles",
        "Ministry team roles",
        "Administration and support roles",
        "Education and chaplaincy roles",
        "Leadership roles",
    }
    assert denomination_family("Baptist") == denomination_family("Converge") != denomination_family("Catholic")
    assert denomination_family("Something new") == "Other denominations"


def test_each_merge_says_what_was_chosen_and_what_is_shown():
    jobs = [job(state="Texas", denom="Baptist")] * 9
    r = report.build_report({"state": ["Ohio"], "denomination": ["Lutheran"]}, jobs)
    assert [(m["label"], m["chosen"], m["shown"]) for m in r["merged"]] == [
        ("Location", "Ohio", "Nationwide"),
        ("Denomination", "Lutheran and Episcopal churches", "All denominations"),
    ]


def test_the_headline_covers_what_the_figures_cover_not_what_was_searched():
    jobs = [job(role="Worship", state="Texas")] * 9
    r = report.build_report({"role": ["Worship"], "state": ["Ohio"]}, jobs)
    assert r["title"] == {"role": "Worship", "area": "Ohio"}  # what was searched (lead tracking, email subject)
    assert r["covers"] == {"role": "Worship", "area": "the United States"}
    r = report.build_report({"role": ["Associate Pastor"]}, [job(role="Campus Pastor")] * 9)
    assert r["covers"] == {"role": "Pastoral roles", "area": "the United States"}
    r = report.build_report({"role": ["Worship"], "state": ["Texas"]}, jobs)  # nothing merged: same as searched
    assert r["covers"] == {"role": "Worship", "area": "Texas"}


def test_a_thin_california_search_uses_its_neighbours_before_going_nationwide():
    jobs = (
        [job(state="California")] * 2 + [job(state="Nevada")] * 2 + [job(state="Oregon")] * 2 + [job(state="Ohio")] * 9
    )
    r = report.build_report({"state": ["California"]}, jobs)
    assert r["scope"] == "nearby" and r["covers"]["area"] == "California and nearby states"
    assert r["merged"][0]["shown"] == "California and nearby states"


def test_the_first_widening_moves_place_and_size_together_then_only_the_area_grows_and_denomination_goes_last():
    family = "Baptist and evangelical churches"
    mine = {"role": ["Worship"], "state": ["Arizona"], "size": ["Under 1,000"], "denomination": [family]}
    mine_row = [job(state="Arizona", size=100, denom="Baptist")] * 2
    near = [job(state="Nevada", size=3000, denom="Converge")] * 5  # a neighbour, other size band, same family
    texas = [job(state="Texas", size=3000, denom="Converge")] * 5  # same region, not a neighbour
    r = report.build_report(mine, mine_row + near + texas)
    assert r["scope"] == "nearby" and kinds(r) == ["state", "size"]  # place and size in one step; family kept
    r = report.build_report(mine, mine_row + texas)
    assert r["scope"] == "region" and kinds(r) == ["state", "size"]  # then only the area grows
    r = report.build_report(mine, [job(state="Ohio", size=3000, denom="Converge")] * 5)
    assert r["scope"] == "national" and kinds(r) == ["state", "size"]  # denomination family still kept
    r = report.build_report(mine, [job(state="Ohio", size=3000, denom="Catholic")] * 5)
    assert r["scope"] == "national" and kinds(r) == ["state", "size", "denomination"]  # dropped only at the end


def test_choosing_every_size_or_every_denomination_is_no_filter():
    jobs = [job(size=300)] * 3 + [job(size=3000)] * 3 + [job()] * 9  # openings with no size or denomination too
    r = report.build_report({"size": ["Under 1,000", "1,000 or more"], "denomination": list(report.FAMILIES)}, jobs)
    assert r["filters"]["size"] == [] and r["filters"]["denomination"] == [] and r["merged"] == []
