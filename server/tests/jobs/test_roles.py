import pytest

from app.jobs.roles import CATCH_ALL_ROLES, OLD_ROLE_LABELS, ROLE_LABELS, bucket_role, pick_role


@pytest.mark.parametrize(
    ("title", "role"),
    [
        # the brief's own examples: these used to land in "Pastor/Minister (other)"
        ("Campus Pastor", "Campus Pastor"),
        ("McKinney Campus Pastor", "Campus Pastor"),
        ("Student Pastor", "Youth & Student"),
        ("Kids Pastor", "Children's & Family"),
        ("Family Pastor", "Children's & Family"),
        ("Teaching Pastor", "Senior/Lead/Teaching Pastor"),
        # choices the client made
        ("Associate Pastor of Students", "Associate Pastor"),
        ("Associate Pastor of Worship", "Associate Pastor"),
        ("Campus Staff Minister - Arkansas Area (undergraduate ministry)", "Youth & Student"),
        ("Campus Minister", "Youth & Student"),
        ("Next Gen Director", "Youth & Student"),
        ("High School Principal", "Head of School"),
        ("Superintendent", "Head of School"),
        ("Director of Development", "Operations & Administration"),
        ("Vice President of Development", "Operations & Administration"),
        ("Christian Counselor", "Healthcare/Counseling"),
        ("Case Manager", "Healthcare/Counseling"),
        ("Missions Director", "Director/Coordinator"),  # no Missions group any more
        ("Missionary", "Other"),
        ("Program Coordinator", "Director/Coordinator"),
        # the order of the rules
        ("Senior Pastor Administrative Assistant / Office Manager", "Operations & Administration"),
        ("Administrative Assistant - Campus Pastor Support", "Operations & Administration"),
        ("Executive Director", "Executive Director"),
        ("President", "Executive Director"),
        ("Graduate adjunct instructor, biblical studies or chaplaincy", "Teacher/Faculty"),
        ("Director of Music Ministries", "Worship"),
        ("Executive Pastor of Operations", "Executive Pastor"),
        # look-alikes that must not match
        ("Executive Director", "Executive Director"),  # "rector" inside "Director" is not a rector
        ("Rector", "Pastor/Minister (other)"),
        ("General Counsel - Archdiocese", "Other"),  # a lawyer, not a counselor
        ("Camp Counselor", "Other"),
        ("Admissions Counselor", "Operations & Administration"),
        ("Principal Product Marketing Manager", "Communications"),
        ("Animator", "Other"),
    ],
)
def test_title_rules(title, role):
    assert bucket_role(title) == role


def test_the_ai_only_replaces_a_catch_all_group():
    assert pick_role("Program Coordinator", "Youth & Student") == "Youth & Student"
    assert pick_role("Pastor", "Senior/Lead/Teaching Pastor") == "Senior/Lead/Teaching Pastor"
    assert pick_role("Worship Leader", "Youth & Student") == "Worship"  # a clear title stands
    assert pick_role("Program Coordinator", "Other") == "Director/Coordinator"  # a vaguer AI answer doesn't win
    assert pick_role("Program Coordinator", "Pastor/Minister (other)") == "Director/Coordinator"
    assert pick_role("Sowers Church Residency", "Pastor/Minister (other)") == "Pastor/Minister (other)"  # beats Other
    assert pick_role("Program Coordinator", "Not a role") == "Director/Coordinator"
    assert pick_role("Program Coordinator", None) == "Director/Coordinator"
    # the AI never hides a job: "Director of Pastoral Care" stays public
    assert pick_role("Director of Pastoral Care", "Healthcare/Counseling") == "Pastor/Minister (other)"


def test_labels():
    assert ROLE_LABELS[-1] == "Other"
    assert set(ROLE_LABELS) >= CATCH_ALL_ROLES | set(OLD_ROLE_LABELS.values())
