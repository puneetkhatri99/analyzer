# Phase 5 — Lead gate

**Status:** Not started. Scope still to be defined.

## Goal (assumed)

Capture leads from people who use the salary data, for example by asking for
an email address before showing full results. This goal is inferred from the
phase name only; confirm it before building.

## Open questions

- What is gated: the whole dashboard, salary figures only, or exports?
- What is collected: email only, or also name, church and role?
- Where do leads go: a new Postgres table, a CRM, or an email tool?
- Does a returning visitor have to sign in, or is one submission enough?

## Likely shape

- **Database:** a `leads` table (email, captured_at, source).
- **API:** `POST /api/leads`, plus a way for the dashboard to know whether
  the visitor already submitted.
- **Dashboard:** a form shown before the gated content.
