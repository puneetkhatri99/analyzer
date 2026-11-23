"""Which roles and denominations count as "similar" when a report search has too little pay data to stand alone
(report/merging.py). Edit the lists here: nothing else needs to change. A role or denomination that isn't listed
falls into the catch-all group at the end.
"""

# Names are the role labels of jobs/roles.py.
ROLE_GROUPS = {
    "Pastoral roles": [
        "Senior/Lead/Teaching Pastor",
        "Executive Pastor",
        "Associate Pastor",
        "Campus Pastor",
        "Pastor/Minister (other)",
    ],
    "Ministry team roles": ["Worship", "Youth & Student", "Children's & Family", "Discipleship & Groups"],
    "Administration and support roles": ["Communications", "Operations & Administration", "Finance", "Facilities"],
    "Education and chaplaincy roles": ["Head of School", "Teacher/Faculty", "Chaplain"],
    "Leadership roles": ["Executive Director", "Director/Coordinator"],
}
OTHER_ROLES = "Other roles"

# Names are the denominations of job_pages/parser.py (DENOMINATIONS) and the ones found on pages and sheets.
DENOMINATION_FAMILIES = {
    "Baptist and evangelical churches": [
        "Baptist",
        "Evangelical Free",
        "Evangelical Covenant",
        "Converge",
        "Christian and Missionary Alliance",
        "Independent Christian Church",
        "Acts 29",
        "Bible Church",
        "Missionary Church",
        "Berean Fellowship of Churches",
    ],
    "Pentecostal and charismatic churches": [
        "Assemblies of God",
        "Calvary Chapel",
        "Vineyard",
        "Fellowship of Christian Assemblies",
        "Pentecostal",
        "Foursquare",
        "Church of God in Christ",
        "Church of God of Prophecy",
        "Every Nation",
    ],
    "Methodist and holiness churches": ["Methodist", "Wesleyan Church", "Nazarene", "Salvation Army"],
    "Reformed and Presbyterian churches": ["Presbyterian", "Reformed", "United Church of Christ"],
    "Lutheran and Episcopal churches": ["Lutheran", "Episcopal"],
    "Catholic and Orthodox churches": ["Catholic", "Orthodox"],
    "Non-denominational and interdenominational churches": ["Non-denominational", "Interdenominational"],
}
OTHER_DENOMINATIONS = "Other denominations"

_ROLE_GROUP_OF = {role: group for group, roles in ROLE_GROUPS.items() for role in roles}
_FAMILY_OF = {name: family for family, names in DENOMINATION_FAMILIES.items() for name in names}


def role_group(role: str) -> str:
    return _ROLE_GROUP_OF.get(role, OTHER_ROLES)


def denomination_family(name: str) -> str:
    return _FAMILY_OF.get(name, OTHER_DENOMINATIONS)


FAMILIES = [*DENOMINATION_FAMILIES, OTHER_DENOMINATIONS]  # what the report offers as "denomination", in this order


def as_family(name: str) -> str:
    """A family name stays; a single denomination (from a link or email made before families were offered) becomes its
    family."""
    return name if name in FAMILIES else denomination_family(name)
