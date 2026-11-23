import re

# A job's role, from keywords in its title. Order matters: the first matching pattern wins. The groups are the
# brief's role list plus the extras the client chose to keep; the order and the edge cases (an "Associate Pastor of
# Students" is an Associate Pastor, college ministry is Youth & Student, Next Gen is Youth & Student, counselors are
# hidden like medical jobs, fundraising is Operations & Administration) were confirmed by the client.
ROLE_RULES = [
    # first: "Senior Pastor Administrative Assistant" supports the pastor, it isn't the pastor's job
    (
        r"administrative assistant|executive assistant|office manager|receptionist|secretary|\bassistant to\b",
        "Operations & Administration",
    ),
    (
        r"senior pastor|lead pastor|head pastor|solo pastor|teaching pastor|preaching pastor|senior minister|"
        r"lead minister",
        "Senior/Lead/Teaching Pastor",
    ),
    (r"executive pastor|executive minister", "Executive Pastor"),
    (r"campus pastor|site pastor", "Campus Pastor"),
    (r"associate pastor|assistant pastor|associate minister|assistant minister|pastoral associate", "Associate Pastor"),
    (
        r"worship|music (director|minist|pastor|leader|coordinator|associate)|minister of music|director of music|"
        r"choir|organist|pianist|accompanist|creative arts|liturg",
        "Worship",
    ),
    (
        r"youth|students? (pastor|minist)|next ?gen|(middle|high) school (pastor|minist)|college (pastor|minist)|"
        r"young adult|campus (staff )?minist|undergraduate minist",
        "Youth & Student",
    ),
    (
        r"children|kids|nursery|(preschool|early childhood|childcare) minist|"
        r"famil(y|ies) (pastor|minist|director|coordinator|life)|(pastor|director|minister|coordinator) of famil",
        "Children's & Family",
    ),
    (
        r"disciple|small group|groups? (pastor|minist|director|coordinator|lead)|"
        r"(pastor|director|minister|coordinator) of (small )?groups|life group|community group|spiritual formation|"
        r"faith formation|christian (education|formation)|adult (minist|education)|religious education|connections",
        "Discipleship & Groups",
    ),
    # before Chaplain and Communications: an adjunct teaching chaplaincy or communications is faculty
    (r"teacher|professor|instructor|faculty|tutor|lecturer|teaching assistant", "Teacher/Faculty"),
    (r"chaplain", "Chaplain"),
    (
        r"head of school|head ?master|superintendent|"
        r"\bprincipal\b(?! (product|engineer|software|program|data|consultant|designer|architect|scientist))",
        "Head of School",
    ),
    # (?<!vice ...): "Vice President of Development" is fundraising, not the organisation's head
    (r"executive director|chief executive|\bceo\b|(?<!vice )(?<!vice-)\bpresident\b", "Executive Director"),
    (r"communicat|media|marketing|graphic|video|design|digital|\bweb|photograph|content", "Communications"),
    (r"financ|accounting|accountant|bookkeep|payroll|controller|treasurer|\bcfo\b", "Finance"),
    (
        r"administ|operations|office assistant|ministry assistant|business manager|human resources|\bhr\b|"
        r"chief operating|\bcoo\b|admission|"
        r"development (director|officer|associate|manager|coordinator|assistant|specialist)|director of development|"
        r"vice president of (development|advancement)|chief development|fundrais|philanthrop|advancement|"
        r"major gift|donor|grant writ|grants? manager",
        "Operations & Administration",
    ),
    (r"facilit|maintenance|custodia|janitor|groundskeep|sexton|housekeep", "Facilities"),
    # \b: "rector" must not match inside "Director"
    (
        r"pastor|minister|clergy|priest|\brector\b|rabbi|\bimam\b|church plant|pastoral|deacon",
        "Pastor/Minister (other)",
    ),
    # Hidden from the public report (report.service.HIDDEN_ROLES): the brief removes medical jobs, and the client
    # chose to hide counselors and social workers the same way. A camp or admissions counselor, or a general counsel
    # (a lawyer), isn't one.
    (
        r"nurse|nursing|clinical|clinician|health|therap|(?<!camp )(?<!admissions )(?<!general )counsel|social work|"
        r"case ?manag|"
        r"casework|psycholog|psychiatr|\blcsw|\blpc\b|medical",
        "Healthcare/Counseling",
    ),
    (r"director|coordinator|manager", "Director/Coordinator"),
]
_COMPILED_RULES = [(re.compile(pattern), label) for pattern, label in ROLE_RULES]

# Every role, in the order the report lists them: the brief's order, then the extras.
ROLE_LABELS = (
    "Senior/Lead/Teaching Pastor", "Executive Pastor", "Associate Pastor", "Campus Pastor", "Worship",
    "Youth & Student", "Children's & Family", "Discipleship & Groups", "Communications", "Operations & Administration",
    "Executive Director", "Head of School", "Teacher/Faculty", "Chaplain", "Finance", "Facilities",
    "Director/Coordinator", "Pastor/Minister (other)", "Healthcare/Counseling", "Other",
)  # fmt: skip
assert {label for _, label in ROLE_RULES} <= set(ROLE_LABELS), "every rule's label must be in ROLE_LABELS"
# Groups a title lands in when it says little about the work; the AI's reading of the description may replace them.
CATCH_ALL_ROLES = {"Other", "Pastor/Minister (other)", "Director/Coordinator"}
# Left out of the public report. Only a title rule hides a job: the client chose not to let the AI hide one (it put
# pastoral care jobs there).
HIDDEN_ROLES = {"Healthcare/Counseling"}

# Labels used before the role list changed, mapped to today's, so shared report links keep their role filter.
OLD_ROLE_LABELS = {
    "Senior/Lead Pastor": "Senior/Lead/Teaching Pastor",
    "Worship/Music": "Worship",
    "Youth/Student Ministry": "Youth & Student",
    "Children's Ministry": "Children's & Family",
    "Discipleship/Teaching": "Discipleship & Groups",
    "Communications/Media": "Communications",
    "Administrative/Operations": "Operations & Administration",
    "Missions": "Other",
}


def bucket_role(title: str | None) -> str:
    t = (title or "").lower()
    for pattern, label in _COMPILED_RULES:
        if pattern.search(t):
            return label
    return "Other"


def pick_role(title: str | None, ai_role: str | None) -> str:
    """The title's role, unless the title only reaches a catch-all group and the AI, reading the whole posting,
    named a more specific one. Any group beats "Other"; the other catch-alls give way only to a specific group. The
    AI never moves a job into a hidden group."""
    role = bucket_role(title)
    if role not in CATCH_ALL_ROLES or ai_role not in ROLE_LABELS or ai_role == "Other" or ai_role in HIDDEN_ROLES:
        return role
    return ai_role if role == "Other" or ai_role not in CATCH_ALL_ROLES else role
