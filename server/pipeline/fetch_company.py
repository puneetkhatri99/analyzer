import requests
from bs4 import BeautifulSoup

TIMEOUT = 8
MAX_CHARS = 4000
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MinistryHubSalaryBot/1.0)"}


def fetch_company_text(company_url: str) -> str | None:
    """Fetch a church's homepage and return cleaned visible text, or None on failure."""
    if not company_url:
        return None
    url = company_url if company_url.startswith("http") else f"https://{company_url}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return text[:MAX_CHARS] if text else None
