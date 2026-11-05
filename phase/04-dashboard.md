# Phase 4 — Dashboard

**Status:** Done
**Code:** `client/`
**Stack:** React 18, Vite, Chart.js (via react-chartjs-2), Tabulator

## Goal

One page where anyone can filter church job postings and immediately see how
salaries vary by role, location, denomination and church size.

## What's on the page

The screen answers one question first: **what does this ministry role pay?**

- **Finding line** under the title, computed from the current filters, for
  example "Median listed pay for all roles is $47,840 a year, from 737
  postings that state it. 1,103 of 1,840 postings list no pay at all."
- **Filters** in one row (search, role, state, denomination, church size, job
  type), with country, remote, minimum pay and "listed pay only" under
  More filters. Active filters show as removable chips. Filters live in the
  URL, so any view can be bookmarked or shared.
- **Headline figures:** median pay, the middle half's range (25th–75th
  percentile), postings with pay, employers. Medians, not averages: a few
  very high postings pulled the average $15k above what a typical role pays.
- **Pay by role** and **pay by state** as pay ladders: each row shows the
  middle half of pay as a band and the median as a tick. Clicking a row
  filters the whole screen. Groups with fewer than 5 paid postings are listed
  but not ranked.
- **By church size** and **by denomination:** postings and median pay.
- **How pay is spread:** a Chart.js histogram of annual pay with the median
  marked.
- **Postings:** a Tabulator table, sortable and paginated, linking to each
  original job page. **Export** downloads the matching postings as CSV.

One colour (blue) appears only on median pay, wherever it is drawn. Every
filter change waits 200 ms, then refetches; the old figures stay on screen,
dimmed, until the new ones arrive.

| File | Responsibility |
|---|---|
| `src/App.jsx` | filter state and URL sync, data fetching, layout, finding line |
| `src/api.js` | calls to the API |
| `src/format.js` | money, count, date formatting; the 5-posting benchmark minimum |
| `src/components/FilterBar.jsx` | filter controls and active-filter chips |
| `src/components/KpiStrip.jsx` | headline figures |
| `src/components/PayLadder.jsx` | pay-by-role and pay-by-state ladders |
| `src/components/BreakdownList.jsx` | church size and denomination lists |
| `src/components/PayDistribution.jsx` | Chart.js pay histogram |
| `src/components/JobsTable.jsx` | Tabulator table and CSV export |
| `src/styles.css` | tokens, layout, tablet and phone layouts |

The postings-over-time chart was removed: postings drop out of the feed when
they close, so the chart showed when the crawler saw jobs, not hiring trends.

## Run it

The API (phase 3) must be running. From `client/`:

```bash
cp .env.example .env    # points the dashboard at the API
npm install
npm run dev             # http://localhost:5173
```

## Deploy

The dashboard has no host of its own. The Render web service builds it
(`npm run build` → `client/dist/`) and FastAPI serves those files at `/`,
next to the API at `/api`, so the dashboard calls the API on its own address.
In dev, `vite.config.js` forwards `/api` to `127.0.0.1:8000`. `VITE_API_BASE`
is optional, only for pointing the dashboard at an API elsewhere.
