# MinistryHub Market Analysis Tool: client meeting agenda

**Prepared:** 16 November 2026

| | Topic | Priority |
|---|---|---|
| ⭐ | OpenAI API key | 🔴 Most important |
| 1 | Existing data (Excel sheets and JSON feed) | 🟠 High |
| 2 | Websites we can't read | 🟠 High |
| 3 | Sign-up, email check and returning visitors | 🟡 Medium |
| 4 | Hot leads | 🟡 Medium |
| 5 | Loxo and Mailchimp | 🟡 Medium |
| 6 | The report | 🟡 Medium |
| 7 | AI provider | 🟢 Low |
| 8 | Still waiting on from the client | 🟢 Follow-up |

---

## ⭐ Most important: OpenAI API key

- We need the client's own **OpenAI API key** from MinistryHub's account, so AI usage and billing are in their name. The client already agreed the live tool should run on their account.
- The data cleanup work can't start without it: removing non-ministry jobs, sorting roles, and finding church size and denomination.
- Also agree on a **monthly AI budget**. The tool will warn them as spending gets close and pause AI work at the limit.

---

## 1. Existing data (Excel sheets and JSON feed)

- What do we do with the data already imported from the Excel sheets and the JSON feed? Clean it and keep it, or start fresh?
- Will they keep sending Excel sheets? If yes, how often, and in the same format?
- What exactly is the difference between the **"BizDev Churches"** and **"BizDev Nonprofits"** sheets? Who fills them in, and what is each used for?
- **Confirm:** the public site shows one combined dataset and never shows that the data comes from different sources. This is our reading of the brief.
- **Confirm:** nonprofit jobs stay hidden from the public for now. The brief says to analyse them first and turn them on later.

---

## 2. The report

- Is the content shown in their **Sample Design** enough, or do they want more in the report?
- If they want more (for example comparisons by state or denomination), should it go in **sections people can open**, to keep the page light?

---

## 3. Sign-up, email check and returning visitors

- **How should we confirm a visitor's email is real?**
  > **Our suggestion:** email them the report, so only a real address receives it.
- **Do returning visitors sign in each time, or do we remember them?**
  > **Our suggestion:** remember them in their browser, and recognise them by email if they sign up again, so their history continues.

---

## 4. Hot leads

- **Confirm the rule from the brief:** a visitor is a hot lead when they download a report, run **3 or more reports**, or click **"Book a call."**
- Who gets the alert: just Jordan, or others too? We need the email address(es).
- How should the alert arrive: an email per lead, or a daily summary?
- What should it include? For example: name, organization, what they searched, and their offer amount.

---

## 5. Loxo and Mailchimp

- Which details go to each system?

  | Detail | Loxo | Mailchimp |
  |---|---|---|
  | Name, email, organization | ? | ? |
  | Roles and locations searched | ? | ? |
  | "Check my offer" amount | ? | ? |
  | Hot-lead status | ? | ? |

- We need **API access for both**, plus the **Mailchimp audience** they want sign-ups added to.
- **Confirm timing:** Loxo daily and Mailchimp weekly, as the brief says.

---

## 6.Websites we can't read

Some job sites block automated access, and others have no reliable way to pull the details.

> **Our proposal:** skip those sites, and if any of them matter, ask the client whether they can get us a feed or export from the site owner. Getting past bot protection isn't something we should do.

- Which sites are most important to them, so we focus our effort there?

---

## 7. AI provider

The client said either OpenAI or Claude is fine, and that they want to talk it through.

> **Our recommendation:** stay on OpenAI for now, and build it so we can switch later if needed.

---

## 8. Still waiting on from the client

- [ ] The role list from the MinistryHub job board
- [ ] Privacy Policy and Terms of Use page links
- [ ] The list of job sites to collect from
- [ ] Jordan's email address (for hot-lead alerts)
- [ ] Loxo and Mailchimp API access
- [ ] OpenAI API key
