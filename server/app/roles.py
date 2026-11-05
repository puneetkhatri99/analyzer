import re

# Fixed taxonomy for LLM title classification (pipeline/enrich.py). The LLM must
# pick one of these for every raw job title -- it never invents a new label.
CANONICAL_ROLES = [
    "Senior/Lead Pastor",
    "Associate Pastor",
    "Executive Pastor",
    "Worship/Music Pastor",
    "Youth/Student Pastor",
    "Children's Pastor",
    "Missions Pastor",
    "Discipleship/Teaching Pastor",
    "Chaplain",
    "Administrative/Operations",
    "Communications/Media",
    "Facilities",
    "Finance",
    "Other",
]

# Keyword fallback used by the API while LLM classification hasn't run.
# Order matters: the first matching pattern wins.
ROLE_RULES = [
    (r"senior pastor|lead pastor|head pastor|solo pastor", "Senior/Lead Pastor"),
    (r"executive pastor", "Executive Pastor"),
    (r"associate pastor", "Associate Pastor"),
    (r"worship|music director|choir|organist", "Worship/Music"),
    (r"youth|student ministr|college ministr", "Youth/Student Ministry"),
    (r"children|kids ministr|preschool", "Children's Ministry"),
    (r"missions?|missionary", "Missions"),
    (r"discipleship|teaching pastor|christian education", "Discipleship/Teaching"),
    (r"chaplain", "Chaplain"),
    (r"communicat|media|marketing|social media|graphic", "Communications/Media"),
    (r"facilit|maintenance|custodia|janitor|groundskeep", "Facilities"),
    (r"finance|accounting|bookkeep|payroll", "Finance"),
    (r"administ|operations|office manager|executive assistant", "Administrative/Operations"),
    (r"pastor|minister|clergy|priest|rector|rabbi|imam", "Pastor/Minister (other)"),
    (r"director|coordinator|manager", "Director/Coordinator"),
    (r"teacher|professor|instructor|faculty", "Teacher/Faculty"),
    (r"nurse|clinical|health|therapist", "Healthcare"),
]
_COMPILED_RULES = [(re.compile(pattern), label) for pattern, label in ROLE_RULES]


def bucket_role(title):
    t = (title or "").lower()
    for pattern, label in _COMPILED_RULES:
        if pattern.search(t):
            return label
    return "Other"
