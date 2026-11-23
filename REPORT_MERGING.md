# How the public report combines data (for approval)

The public report never says "not enough data". When too few openings list pay for a search, the report widens it
step by step and tells the visitor exactly what was combined. This page lists every rule so it can be approved or
changed. **Items marked ❓ need your decision.**

## 1. When does it combine?

A figure needs **at least 5 current openings that list pay** (for the job type chosen: full-time yearly pay, or
part-time hourly pay). If the visitor's exact search has fewer, one filter at a time is widened until there are 5.

## 2. In what order?

1. **First widening: the location and church size move one step together.** The state becomes the state plus the
   states that border it, and church size is set to any size. The denomination family is kept.
2. **Still too thin: the area grows to the whole region** (see 3).
3. **Still too thin: nationwide.**
4. **Then the denomination family is dropped** (all denominations).
5. **Last: role** is combined with similar roles (see 6), then all roles. Role is kept exact for as long as possible.

Example: *Children's & Family, Arizona, Under 1,000*. Arizona alone has no pay data. Step 1 looks at Arizona,
California, Nevada, New Mexico and Utah at any church size. If that is still thin, step 2 widens to the Southwest
region, and only then does it go nationwide.

## 3. Location → nearby states → region → nationwide

First the chosen state plus the states that share a border with it (California → Oregon, Nevada, Arizona; Texas →
Arkansas, Louisiana, New Mexico, Oklahoma). If that is still too thin, the whole region below is added. Alaska and
Hawaii have no neighbours, so they go straight to their region.

| Region | States |
|---|---|
| North East | Connecticut, Delaware, District of Columbia, Maine, Maryland, Massachusetts, New Hampshire, New Jersey, New York, Pennsylvania, Rhode Island, Vermont |
| South East | Alabama, Arkansas, Florida, Georgia, Kentucky, Louisiana, Mississippi, North Carolina, South Carolina, Tennessee, Virginia, West Virginia |
| Midwest | Illinois, Indiana, Iowa, Kansas, Michigan, Minnesota, Missouri, Nebraska, North Dakota, Ohio, South Dakota, Wisconsin |
| Southwest | Arizona, New Mexico, Oklahoma, Texas |
| West Coast | California, Hawaii |
| Pacific Northwest | Alaska, Idaho, Oregon, Washington |
| Mountain West | Colorado, Montana, Nevada, Utah, Wyoming |

❓ Are these regions right? (Existing regions, not new; Texas is in the Southwest and Arkansas in the South East.)

## 4. Church size

Two bands: **Under 1,000 · 1,000 or more** (average weekly attendance). Only about 1 in 5 openings state a church
size, so four bands left each band with too few pay figures. If a band is too thin, church size is dropped.

❓ Two bands instead of the four in the brief (Under 250 · 250 to 999 · 1,000 to 4,999 · 5,000 or more). OK, or
should the four bands come back?

## 5. Denomination families

Visitors choose a **family**, not a single denomination ("Baptist" alone matched only about 36 paid openings; its
family matches about 95). The report's denomination chart shows the same families. Anything not listed falls into
"Other denominations".

| Family | Denominations |
|---|---|
| Baptist and evangelical churches | Baptist, Evangelical Free, Evangelical Covenant, Converge, Christian and Missionary Alliance, Independent Christian Church, Acts 29, Bible Church, Missionary Church, Berean Fellowship of Churches |
| Pentecostal and charismatic churches | Assemblies of God, Calvary Chapel, Vineyard, Fellowship of Christian Assemblies, Pentecostal, Foursquare, Church of God in Christ, Church of God of Prophecy, Every Nation |
| Methodist and holiness churches | Methodist, Wesleyan Church, Nazarene, Salvation Army |
| Reformed and Presbyterian churches | Presbyterian, Reformed, United Church of Christ |
| Lutheran and Episcopal churches | Lutheran, Episcopal |
| Catholic and Orthodox churches | Catholic, Orthodox |
| Non-denominational and interdenominational churches | Non-denominational, Interdenominational |
| Other denominations | Everything else: Church of Christ, Seventh-day Adventist, Latter-day Saints, Friends (Quaker) |

❓ Are these families right? In particular:
- Church of Christ, Seventh-day Adventist, Latter-day Saints and Friends (Quaker) are in "Other denominations" because
  they do not fit the others. Should any join a family?
- United Church of Christ is placed with Reformed and Presbyterian. Correct?
- Salvation Army is placed with Methodist and holiness. Correct?

## 6. Role groups

| Group | Roles |
|---|---|
| Pastoral roles | Senior/Lead/Teaching Pastor, Executive Pastor, Associate Pastor, Campus Pastor, Pastor/Minister (other) |
| Ministry team roles | Worship, Youth & Student, Children's & Family, Discipleship & Groups |
| Administration and support roles | Communications, Operations & Administration, Finance, Facilities |
| Education and chaplaincy roles | Head of School, Teacher/Faculty, Chaplain |
| Leadership roles | Executive Director, Director/Coordinator |
| Other roles | Anything else |

❓ Are these groups right? (Role is the last filter to be widened, so these groups are only used when the other three
filters have already been widened.)

## 7. What the visitor sees

- **Headline** shows what the figures cover ("Associate Pastor pay in the United States").
- **"We widened your search" panel** lists each widened filter: *Location: Wyoming → Nationwide*.
- **Pay card** carries a "Based on combined data" badge next to the confidence label.
- **Charts** (roles, church size, states, denominations): a row with too little pay is combined with similar rows and
  marked "Combined: …" instead of being hidden. A chart with fewer than two rows is left out.
- **Printed report and email** state the same combinations before the figures.

## 8. Confidence label (kept as is)

Counted after any combining, from the number of openings with pay behind the figure.

| Openings with pay | Label |
|---|---|
| 30 or more | Strong |
| 10 to 29 | Moderate |
| 5 to 9 | Limited |
| Fewer than 5 | No figure; the search is widened first |

Typical pay is the middle value; "Most churches offer" is the middle half of postings (25th to 75th percentile),
rounded to $500 a year or $0.50 an hour.

## 9. Duplicates

One opening is counted once, even if posted twice or listed by two sources. Two openings are the same when they share
a link, or have the same employer, title and state, and were posted within 90 days of each other. Separate openings
with the same title at the same church at the same time therefore count as one.

---

*For the developer:* the lists in sections 5 and 6 are in `server/app/report/groups.py`; edit them and nothing else
needs to change. The order and levels are in `server/app/report/merging.py`.
