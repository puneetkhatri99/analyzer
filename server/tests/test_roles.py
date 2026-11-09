from app.roles import bucket_role as b


def test_director_is_not_a_rector():
    assert b("Executive Director") == "Director/Coordinator"
    assert b("Rector") == b("Associate Rector") == b("Minister of Pastoral Care") == "Pastor/Minister (other)"
    assert b("Animator") == "Other"
