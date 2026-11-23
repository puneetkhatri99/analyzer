# Market Analysis Tool – What We've Done So Far

*As of 20 November 2026*

## Summary

Five of the six open items from the developer brief are built and tested. The sixth, the Loxo connection, is waiting
for the client's Loxo API documentation. Everything so far runs on our test copy of the data. It goes live once it is
published (see the last section).

What changed, in one line each:

- **Job roles:** far fewer jobs now land in vague groups like "Other". The share fell from 54% to about 26%.
- **Duplicate jobs:** the same job posted twice now counts once. Our 4,331 job listings turned out to be 4,194 real
  openings.
- **Tidier lists:** each denomination now has one name, so "Southern Baptist" shows as "Baptist". Placeholder
  employers are hidden from the public.
- **Church size:** the system now finds it more often, tries again later when it can't, and staff can type it in by
  hand.
- **Newsletter:** the sign-up form has a new opt-in box. Once a week, those visitors are passed to Mailchimp. This
  stays switched off until we have the Mailchimp key.
- **Record keeping:** the system now writes down each decision it makes, so anything can be checked later.

The brief left some choices open. The team confirmed each of those before it was built.

---

## 1. Job roles: clearer groups

The share of jobs in vague groups ("Other", "Pastor/Minister (other)" and "Director/Coordinator") fell from 54% to
about 26%. Campus, Student and Kids Pastors now have their own groups, as the brief asked.

**How it works now.** The system first sorts a job by its title, using keywords. If the title is too vague to place,
an AI reads the whole job description and picks the group. A clear title always wins over the AI.

**The groups visitors can pick from**, in this order: Senior/Lead/Teaching Pastor, Executive Pastor, Associate Pastor,
Campus Pastor, Worship, Youth & Student, Children's & Family, Discipleship & Groups, Communications, Operations &
Administration, Executive Director, Head of School, Teacher/Faculty, Chaplain, Finance, Facilities,
Director/Coordinator, Pastor/Minister (other), Other.

**Examples from real job titles:**

| Job title | Group before | Group now | Why |
| --- | --- | --- | --- |
| Campus Pastor | Pastor/Minister (other) | Campus Pastor | New group from the brief |
| Student Pastor | Pastor/Minister (other) | Youth & Student | New group from the brief |
| Kids Pastor | Pastor/Minister (other) | Children's & Family | New group from the brief |
| Teaching Pastor | Discipleship/Teaching | Senior/Lead/Teaching Pastor | The brief groups these together |
| Head of School | Other | Head of School | New group from the brief |
| Executive Director | Director/Coordinator | Executive Director | New group from the brief |
| Director of Development | Director/Coordinator | Operations & Administration | Team's choice: fundraising goes here |
| Associate Pastor of Students | Associate Pastor | Associate Pastor | Team's choice: "Associate" wins over the ministry area |
| Campus Staff Minister (undergraduate ministry) | Pastor/Minister (other) | Youth & Student | Team's choice: college ministry is student ministry |
| Senior Pastor Administrative Assistant | Senior/Lead Pastor | Operations & Administration | It supports the pastor; it isn't the pastor's job |
| Case Manager | Director/Coordinator | Hidden from the public | Team's choice: counselors are hidden like medical jobs |

**Examples where the AI read the description:**

| Job title | Title alone gave | AI chose | Result |
| --- | --- | --- | --- |
| Salt Company Ministry Lead | Other | Youth & Student | Moved: the posting describes a college ministry |
| Production/Tech Resident | Other | Worship | Moved: worship production work |
| Sowers Church Residency | Other | Pastor/Minister (other) | Moved: a pastoral residency |
| Worship Leader | Worship | Youth & Student | Not moved: a clear title wins |
| Director of Pastoral Care | Pastor/Minister (other) | Healthcare/Counseling | Not moved: the team decided the AI may never hide a job |

**Cost.** A one-time AI pass over 1,504 current jobs cost about $1.58; about 250 of them moved out of a vague group.
New jobs get their group during the daily check the AI already does, at almost no extra cost.

**Old links still work.** A report link someone shared last month for "Worship/Music" now opens the "Worship" report.

Other team choices: "Next Gen" jobs go to Youth & Student; "Principal" and "Superintendent" count as Head of School;
Missions no longer has its own group.

---

## 2. Duplicate jobs counted once

The same job posted twice, or listed in two of our sources, now counts as one opening in every public figure. On
today's data, 4,331 job listings turned out to be 4,194 real openings, in 130 groups of repeats.

**How a repeat is spotted.** Two listings are treated as the same opening when either of these is true:

1. They point to the same web link, in the same state.
2. They have the same employer, the same job title and the same town, and they were posted within 90 days of each
   other. A job that keeps being reposted every few weeks stays one opening.

Names and titles are compared loosely. Small wording differences don't hide a repeat: "Pastor of Worship
(Full-Time)" matches "Worship Pastor", and "First Baptist Church, Inc." matches "First Baptist Church".

**Which copy is kept.** The newest copy that lists pay is kept, so a raised salary wins. Missing details are filled in
from the other copies. For example, if only the older copy says the church has 400 people, the kept copy gets that
too.

**Real examples that now count once:**

| Listings | Why they are one opening |
| --- | --- |
| "Youth Pastor – The Compass Church", Naperville, IL, posted Sep 10 and again Nov 16 | Same job reposted 67 days later |
| "Worship Pastor" at "Emmanuel Faith Community Church" (job feed) and at "Emmanuel Faith Community" (church spreadsheet), Escondido, CA | Same job in two sources, 8 days apart |
| "Corps Ministry Assistant" at The Salvation Army, Pittsburgh, PA, twice on Sep 24 | Posted twice on the same day |
| "Associate Pastor" at "Aspire Church" (job feed) and "Aspire" (church spreadsheet), Jacksonville, FL | Same job in two sources, 1 day apart |

**Examples that stay separate:**

| Listings | Why they are two openings |
| --- | --- |
| "Church Engagement Officer" at Steiger, Minneapolis, MN, and "Church Engagement Officer – Texas", Houston, TX, on the same web link | Different states. The link is a general careers page (team's choice) |
| The same title at the same church name in two different towns (for example, Dallas and Austin) | Different towns mean different churches |
| The same job posted again 200 days later | Too long a gap: treated as a new opening |

**One known limit.** If a church truly has two identical openings at the same time, for example two "Nursery Worker"
jobs, they count as one. The team chose this to keep pay figures from being double counted.

The admin job list still shows every listing, so staff can see all the copies.

---

## 3. Tidier lists

Each denomination now shows under one name, and jobs with a placeholder or missing employer are kept off the public
report. Visitors can also tell us about a denomination we don't list.

**Denominations merged.** The brief named the first few; the team approved the rest after we found them in the data.

| Name stored in the data | Jobs | Now shown as |
| --- | --- | --- |
| Southern Baptist | 93 | Baptist |
| Southern Baptist Convention | 4 | Baptist |
| United Methodist | 38 | Methodist |
| Roman Catholic | – | Catholic |
| Evangelical (The Salvation Army) | 11 | Salvation Army |
| Lutheran Church-Missouri Synod | 6 | Lutheran |
| Christian Church (Independent) | 4 | Independent Christian Church |
| Christian Church (disciples/independent) | 4 | Independent Christian Church |
| Independent Christian Churches | 3 | Independent Christian Church |
| Christian churches and churches of Christ | 1 | Independent Christian Church |
| Evangelical Covenant Church | 3 | Evangelical Covenant |
| Friends Southwest | 1 | Friends (Quaker) |
| Christian Reformed Church in North America (CRCNA) | 1 | Reformed |

Nothing stored was rewritten: names are merged as they are shown, so a merge can be undone easily. The public filter
now lists one Baptist, one Methodist and one Catholic.

**"Don't see your denomination?"** A new link sits under the denomination filter on the report. For example, a
visitor types "Anglican Church in North America" and presses Send. That then shows up in two places:

- in that person's activity on the admin Leads page, as *Couldn't find their denomination – Suggested "Anglican Church
  in North America"*;
- in the next daily lead email, under *Denominations visitors couldn't find in the list*.

**Placeholder employers.** We searched every employer name for placeholders such as "do not use", "test", "TBD", "N/A"
and blanks. The team chose to hide everything found:

- "Z. Do Not Use": 1 job ("Parish Catechetical Leader and Assistant to Pastor", Daytona Beach, FL);
- 2 jobs with no employer at all.

They no longer count in public figures. Staff still see them in admin.

---

## 4. Church size

The system now finds church sizes more often, keeps trying when it can't, and lets staff fill them in.

**What counts as a size.** Any size the church or a reliable directory states, never staff counts or a guess. Weekly
attendance comes first, and membership is used only when no attendance is given (team's choice).

| What the church's website says | Size saved |
| --- | --- |
| "About 400 people worship with us each week" | 400 |
| "We have 1,200 members" (no attendance given) | 1,200 |
| "400 attend weekly, 1,200 members" | 400 |
| "Our staff of 12" | Nothing: staff counts don't count |

**Trying again.** Before, a church whose size couldn't be found online was never looked up again. Now it is tried
again after 90 days, within the monthly AI spending limit.

**Staff can type it in.** Editors and admins now see a *Fill in the employer* box when they open a job in admin. For
example, they open a job at Grace Church, Dallas, TX, and type 450 and "Southern Baptist". Then:

- every job at Grace Church in Dallas shows a size of 450 and the denomination "Baptist";
- a Grace Church in another town is not changed;
- the size is marked "entered by" that staff member, and the change is recorded.

**Wording.** Because a size can now be membership, the public pages say "Church size" instead of "Weekly
attendance". This covers the sign-up form, the report filter, the report charts and the landing page.

---

## 5. Newsletter and Mailchimp

Visitors can now ask for the newsletter on the sign-up form. Once a week, those people are passed to Mailchimp with a
short record of what they did on the site. This is built but switched off until we have the client's Mailchimp key.

**The new checkbox.** "Send me the MinistryHub newsletter" sits under "Email me this report". It starts unticked, so
only people who choose it are ever sent (team's choice). Leaving it unticked on a later visit doesn't remove an
earlier yes; people unsubscribe from any newsletter email, as usual.

**What Mailchimp receives**, for example, for someone who ticked the box and checked a salary offer:

- the person: first name, last name and email, added to the newsletter list;
- tags: *MinistryHub salary tool* and *Checked an offer* (plus *Hot lead* or *Booked a call* when those apply);
- a note:

```
MinistryHub salary tool. Organization: Grace Church. First search: Worship in Ohio.
2026-11-20 Signed up
2026-11-20 Checked an offer of 52000 (year)
```

The next week, only what they did since then is sent. Someone who already unsubscribed in Mailchimp stays
unsubscribed. If Mailchimp refuses a send, the system tries again the next day and emails the team.

**Not live yet.** It needs the client's Mailchimp API key and the ID of the newsletter list. It has only been tested
against a pretend Mailchimp, so the first real run should be watched.

**Loxo** is not built yet. Loxo's field names are only in its private documentation, so the team chose to wait for the
client's Loxo API key and docs rather than guess.

---

## 6. Keeping a record

The system now writes down each decision it makes, so any figure can be traced back. This happens at the end of every
daily data update, and staff can also ask for it at any time. Email addresses are never written down.

Example lines from the record:

| What it records | Example line |
| --- | --- |
| The AI's role choice for each job | 'Childrens Creative and Worship Coordinator': title says Worship, AI says Children's & Family, using Worship |
| The daily duplicate count | 4,331 job rows are 4,194 openings; 130 groups of 2 or more copies were merged |
| Each merged group | Merged 2 copies (same job within 67 days); kept the newer one |
| A group worth a second look | Merged group with different cities ['houston', 'minneapolis'] |
| Each denomination merge | 'Southern Baptist' (93 jobs) is shown as 'Baptist' |
| Jobs hidden for their employer | 3 jobs; 2 with no employer; 1 with placeholder 'Z. Do Not Use' |
| A denomination a visitor suggested | Denomination suggested (kept): 'Anglican Church in North America' |
| A size typed in by staff | Employer facts set by (staff member) for 'Grace Church' (2 jobs): church size None -> 450 |
| A church looked up again | retry, last looked up 2026-08-10 without a size |
| A newsletter send | Mailchimp: member 1a2b3c4d sent (2 new activities) |

---

## 7. Still to do, and decisions needed

**To go live** (the developer's side):

- [ ] Publish the code. It is tested (169 automatic checks pass) but not yet saved to the shared code history.
- [ ] Update the live database. Two small additions are waiting. Before them, the step that clears the old AI cost log
      has to be run by hand. **Decision needed:** has that step already been run on the live site?
- [ ] Give live jobs their AI roles: about $1.60 for a one-time pass, or copy the results over from the test data.
- [ ] Check the new pages in a browser on desktop and phone.

**Waiting on the client:**

- [ ] The Mailchimp API key and the newsletter list's ID, to switch the newsletter on.
- [ ] The Loxo API key and Loxo's API documentation, to build the Loxo connection.

**Small things not done yet:**

- Admin pages still say "attendance" in a few places (filters, charts); the public pages are updated.
- The admin Leads list doesn't yet show who ticked the newsletter box.
- The "Drawn from 4,000+ openings" line on the report didn't change: 4,194 still rounds to 4,000+.

**Left out by team decision:** tracking whether each job is still open or closed, and "typical time open".
