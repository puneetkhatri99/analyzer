"""Recording every OpenAI call's tokens and estimated cost (ai_usage), and the AI costs page's figures.

cost_usd is an estimate from the token counts OpenAI returns and list prices; OpenAI's billing page is the truth.
"""

import logging
from typing import Any

from psycopg.rows import dict_row

from app.core.db import get_conn

# List prices in USD: per 1M tokens (input, cached input, output), and per web search call.
# shortcut: prices are hard-coded; update them here when OpenAI changes its prices or OPENAI_MODEL changes.
PRICES = {"gpt-5.4-mini": (0.75, 0.075, 4.50)}
WEB_SEARCH_PRICE = 0.01

log = logging.getLogger("admin")


def estimate_cost(model: str, input_tokens: int, cached: int, output_tokens: int, searches: int) -> float | None:
    """USD for one call, or None when the model's price isn't known."""
    price = PRICES.get(model)
    if price is None:
        return None
    tokens = (input_tokens - cached) * price[0] + cached * price[1] + output_tokens * price[2]
    return round(tokens / 1e6 + searches * WEB_SEARCH_PRICE, 6)


def record(response: Any, *, purpose: str, url: str, model: str, admin_email: str | None) -> None:
    """Store one AI call's usage and estimated cost. Never breaks the request it measures."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    cached = getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", 0) or 0
    searches = sum(1 for o in getattr(response, "output", []) if getattr(o, "type", "") == "web_search_call")
    cost = estimate_cost(model, usage.input_tokens, cached, usage.output_tokens, searches)
    log.info(
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
                                                output_tokens, web_searches, cost_usd)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (admin_email, purpose, url, model, usage.input_tokens, cached, usage.output_tokens, searches, cost),
            )
    except Exception:  # losing one usage row is better than failing the admin's extraction
        log.exception("Couldn't store the AI usage row for %s", url)


def costs_report() -> dict[str, Any]:
    """Estimated AI spend: totals, by purpose, by day (last 30 days) and the latest calls."""
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
        by_day = cur.execute(
            """SELECT created_at::date AS day, count(*) AS calls, coalesce(sum(cost_usd), 0) AS cost
               FROM public.ai_usage WHERE created_at >= now() - interval '30 days' GROUP BY 1 ORDER BY 1 DESC"""
        ).fetchall()
        recent = cur.execute(
            """SELECT created_at, admin_email, purpose, url, model, input_tokens, output_tokens, web_searches, cost_usd
               FROM public.ai_usage ORDER BY created_at DESC LIMIT 100"""
        ).fetchall()
    return {"totals": totals, "by_purpose": by_purpose, "by_day": by_day, "recent": recent}
