"""Recording every OpenAI call's tokens and estimated cost (ai_usage), and the AI costs page's figures.

cost_usd is an estimate from the token counts OpenAI returns and list prices; OpenAI's billing page is the truth.
"""

import logging
from contextvars import ContextVar
from typing import Any

from psycopg.rows import dict_row

from app.core.config import get_settings
from app.core.db import get_conn
from app.core.settings_store import delete_setting, get_setting, set_setting
from app.shared.web import with_scheme

# List prices in USD: per 1M tokens (input, cached input, output), and per web search call.
# shortcut: prices are hard-coded; update them here when OpenAI changes its prices or OPENAI_MODEL changes.
# Prices as listed in Nov 2026 (developers.openai.com model pages; GPT-5.4 / 5.5 from third-party price trackers).
PRICES = {
    "gpt-5.4-nano": (0.20, 0.02, 1.25),
    "gpt-5.4-mini": (0.75, 0.075, 4.50),
    "gpt-5.4": (2.50, 0.25, 15.00),
    "gpt-5.5": (5.00, 0.50, 30.00),
}
WEB_SEARCH_PRICE = 0.01

# What one call of each kind uses on average: (input tokens, of which cached, output tokens, web searches), to price
# the same work on another model. Measured on gpt-5.4-mini in Nov 2026, except posting_review (an estimate: one
# posting's text and no search). costs_report replaces a profile with the live average once a purpose has 5+ calls.
PROFILES = {
    "posting_review": (2000, 0, 150, 0),
    "church_lookup": (10638, 2402, 239, 1.66),
    "bizdev_pay": (6978, 4147, 199, 1.0),
}

log = logging.getLogger("admin")

# Set by a background run (the daily feed) so every AI call it makes is stored with the run's ID.
current_run: ContextVar[str | None] = ContextVar("current_run", default=None)


def estimate_cost(model: str, input_tokens: int, cached: int, output_tokens: int, searches: int) -> float | None:
    """USD for one call, or None when the model's price isn't known."""
    price = PRICES.get(model)
    if price is None:
        return None
    tokens = (input_tokens - cached) * price[0] + cached * price[1] + output_tokens * price[2]
    return round(tokens / 1e6 + searches * WEB_SEARCH_PRICE, 6)


# ---- the monthly spending limit ------------------------------------------------------------------------------------

LIMIT_KEY = "ai_monthly_limit_usd"
MONTH_START = "date_trunc('month', now())"


class BudgetReached(Exception):
    """This month's estimated AI spend has reached the limit an admin set."""


def month_spend() -> float:
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT coalesce(sum(cost_usd), 0) FROM public.ai_usage WHERE created_at >= {MONTH_START}"
        ).fetchone()
    return float(row[0])


def get_limit() -> float | None:
    value = get_setting(LIMIT_KEY)
    return None if value is None else float(value)


def set_limit(limit: float | None, by: str) -> None:
    """Save the monthly limit in dollars; None removes it."""
    if limit is None:
        delete_setting(LIMIT_KEY)
    else:
        set_setting(LIMIT_KEY, limit, by=by)


def budget() -> dict[str, Any]:
    """The limit, what this month has cost so far, and whether the limit is reached (limit None = no limit)."""
    limit, spent = get_limit(), month_spend()
    return {"limit_usd": limit, "spent": spent, "reached": limit is not None and spent >= limit}


def ensure_budget() -> None:
    """Call before every OpenAI call: raises BudgetReached once the month's limit is reached.
    shortcut: the check and the spend aren't atomic, so calls already running (a few at a time) can overshoot by a few
    cents. Costs are estimates (a call on a model without a known price counts as nothing)."""
    b = budget()
    if b["reached"]:
        raise BudgetReached(
            f"The monthly AI limit of ${b['limit_usd']:.2f} is reached (${b['spent']:.2f} spent this month)"
        )


def record(response: Any, *, purpose: str, url: str, model: str, admin_email: str | None) -> None:
    """Store one AI call's usage and estimated cost. Never breaks the request it measures."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    cached = getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", 0) or 0
    searches = sum(1 for o in getattr(response, "output", []) if getattr(o, "type", "") == "web_search_call")
    cost = estimate_cost(model, usage.input_tokens, cached, usage.output_tokens, searches)
    # a feed run makes hundreds of calls; its progress and total are logged by the run itself
    log.log(
        logging.DEBUG if current_run.get() else logging.INFO,
        "AI call (%s) for %s: %s, %d tokens in (%d cached), %d out, %d web searches, cost %s",
        purpose,
        url,
        model,
        usage.input_tokens,
        cached,
        usage.output_tokens,
        searches,
        "unknown" if cost is None else f"${cost:.4f}",
    )
    try:
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO public.ai_usage (admin_email, purpose, url, model, input_tokens, cached_tokens,
                                                output_tokens, web_searches, cost_usd, run_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    admin_email,
                    purpose,
                    url,
                    model,
                    usage.input_tokens,
                    cached,
                    usage.output_tokens,
                    searches,
                    cost,
                    current_run.get(),
                ),
            )
    except Exception:  # losing one usage row is better than failing the admin's extraction
        log.exception("Couldn't store the AI usage row for %s", url)


def costs_report() -> dict[str, Any]:
    """Estimated AI spend: totals, by purpose, by run (daily feed) and by day (last 30 days).
    Every figure is summed from ai_usage, so deleting rows changes all of them."""
    with get_conn() as conn:
        cur = conn.cursor(row_factory=dict_row)
        totals = cur.execute(
            """SELECT coalesce(sum(cost_usd), 0) AS total,
                      coalesce(sum(cost_usd) FILTER (WHERE created_at >= date_trunc('month', now())), 0) AS this_month,
                      coalesce(sum(cost_usd) FILTER (WHERE created_at >= date_trunc('day', now())), 0) AS today,
                      count(*) AS calls, coalesce(sum(web_searches), 0) AS web_searches,
                      coalesce(sum(input_tokens), 0) AS input_tokens, coalesce(sum(output_tokens), 0) AS output_tokens,
                      count(*) FILTER (WHERE cost_usd IS NULL) AS unpriced, min(created_at) AS since
               FROM public.ai_usage"""
        ).fetchone()
        by_purpose = cur.execute(
            """SELECT purpose, count(*) AS calls, sum(web_searches) AS web_searches,
                      coalesce(sum(cost_usd), 0) AS cost, coalesce(avg(cost_usd), 0) AS avg_cost
               FROM public.ai_usage GROUP BY purpose ORDER BY cost DESC"""
        ).fetchall()
        by_run = cur.execute(
            """SELECT run_id, min(created_at) AS started, count(*) AS calls,
                      coalesce(sum(web_searches), 0) AS web_searches, coalesce(sum(cost_usd), 0) AS cost
               FROM public.ai_usage WHERE run_id IS NOT NULL GROUP BY run_id ORDER BY started DESC LIMIT 30"""
        ).fetchall()
        by_day = cur.execute(
            f"""SELECT {DAY} AS day, count(*) AS calls, coalesce(sum(cost_usd), 0) AS cost
               FROM public.ai_usage WHERE created_at >= now() - interval '30 days' GROUP BY 1 ORDER BY 1 DESC"""
        ).fetchall()
        measured = cur.execute(
            """SELECT purpose, avg(input_tokens) AS input, avg(cached_tokens) AS cached, avg(output_tokens) AS output,
                      avg(web_searches) AS searches FROM public.ai_usage
               WHERE purpose = ANY(%s) AND cost_usd IS NOT NULL GROUP BY purpose HAVING count(*) >= 5""",
            (list(PROFILES),),
        ).fetchall()
    profiles = {
        p: dict(zip(("input", "cached", "output", "searches"), v, strict=True), measured=False)
        for p, v in PROFILES.items()
    }
    for m in measured:
        purpose = m.pop("purpose")
        profiles[purpose] = {**{k: float(v) for k, v in m.items()}, "measured": True}
    pricing = {
        "model": get_settings().openai_model,
        "web_search": WEB_SEARCH_PRICE,
        "models": {name: dict(zip(("input", "cached", "output"), p, strict=True)) for name, p in PRICES.items()},
        "profiles": profiles,
    }
    return {
        "totals": totals,
        "by_purpose": by_purpose,
        "by_run": by_run,
        "by_day": by_day,
        "pricing": pricing,
        "budget": budget(),
    }


# ---- the calls list: filtered, paged, and deletable ---------------------------------------------------------------

PAGE_SIZE = 25
MAX_DELETE = 1000  # ids in one request
# A call's day in US Eastern, the team's day (as in the daily lead report); a bare ::date would follow the database's
# own time zone (UTC on Neon), moving evening calls to the next day.
DAY = "(created_at AT TIME ZONE 'America/New_York')::date"


def _where(f: dict[str, Any]) -> tuple[str, list[Any]]:
    """WHERE clause and parameters for the calls list's filters: purpose, run ('none' = not from a feed run),
    from / to (dates, inclusive) and q (part of the URL)."""
    parts: list[str] = []
    params: list[Any] = []
    if f.get("purpose"):
        parts.append("purpose = %s")
        params.append(f["purpose"])
    if f.get("run") == "none":
        parts.append("run_id IS NULL")
    elif f.get("run"):
        parts.append("run_id = %s")
        params.append(f["run"])
    if f.get("date_from"):
        parts.append(f"{DAY} >= %s")
        params.append(f["date_from"])
    if f.get("date_to"):
        parts.append(f"{DAY} <= %s")
        params.append(f["date_to"])
    if f.get("q"):
        parts.append("url ILIKE %s")
        escaped = f["q"].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")  # LIKE wildcards are literal
        params.append(f"%{escaped}%")
    return (" WHERE " + " AND ".join(parts)) if parts else "", params


def list_calls(f: dict[str, Any], page: int) -> dict[str, Any]:
    """One page of AI calls (newest first) matching the filters, with how many match and what they cost together."""
    where, params = _where(f)
    with get_conn() as conn:
        cur = conn.cursor(row_factory=dict_row)
        total = cur.execute(
            "SELECT count(*) AS n, coalesce(sum(cost_usd), 0) AS cost FROM public.ai_usage" + where, params
        ).fetchone()
        rows = cur.execute(
            "SELECT id, created_at, admin_email, purpose, run_id, url, model, input_tokens, output_tokens,"
            " web_searches, cost_usd FROM public.ai_usage"
            + where
            + " ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s",
            [*params, PAGE_SIZE, max(page - 1, 0) * PAGE_SIZE],
        ).fetchall()
    for r in rows:  # stored as the feed gives it, often without https://, which a link needs
        r["url"] = r["url"] and with_scheme(r["url"])
    return {"rows": rows, "total": total["n"], "cost": total["cost"], "page": page, "page_size": PAGE_SIZE}


def delete_calls(*, ids: list[int] | None = None, filters: dict[str, Any] | None = None) -> int:
    """Permanently delete the given calls, or every call matching the filters. Returns how many were deleted."""
    with get_conn() as conn:
        if ids is not None:
            cur = conn.execute("DELETE FROM public.ai_usage WHERE id = ANY(%s)", (ids,))
        else:
            where, params = _where(filters or {})
            cur = conn.execute("DELETE FROM public.ai_usage" + where, params)
        return cur.rowcount
