"""What every request to a job site shares: our identity, bot-check detection and the private-network guard."""

import ipaddress
import re
import socket
from typing import Any
from urllib.parse import urljoin, urlsplit

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MinistryJobsAnalyser/1.0)", "Accept-Language": "en-US,en;q=0.9"}
BLOCKED_RE = re.compile(r"just a moment\.\.\.|cf-chl|attention required|access denied|captcha|are you a robot", re.I)


class UnsafeURLError(ValueError):
    """The URL can't be fetched safely: its host doesn't resolve, or resolves to a private network."""


def with_scheme(url: str) -> str:
    """Feed and sheet links are often stored without a scheme."""
    # a full scheme check: some hosts start with "http" themselves (httpsladgovcomjobopenings.applytojob.com)
    return url if url.lower().startswith(("http://", "https://")) else "https://" + url


def url_key(url: str) -> str:
    """A job's identity across sources: its URL without scheme, www, query or trailing slash."""
    p = urlsplit(url.strip().lower())
    return p.netloc.removeprefix("www.") + p.path.rstrip("/")


def check_public_url(url: str) -> None:
    """Refuse URLs that point into a private network (SSRF): every address the host resolves to must be public."""
    host = urlsplit(url).hostname or ""
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror as e:
        raise UnsafeURLError(f"Can't find the site {host}") from e
    if any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise UnsafeURLError("That address points to a private network")


MAX_REDIRECTS = 5


def get_public(url: str, **kwargs: Any) -> requests.Response:
    """GET that follows redirects itself, checking every hop with check_public_url, so a public page can't redirect
    the server into its own network. Raises UnsafeURLError, or requests.RequestException on network errors.

    shortcut: the host is resolved again by requests after the check (DNS rebinding can slip between the two);
    pin the checked IP in the connection if this ever fetches URLs from the public, not only signed-in editors.
    """
    for _ in range(MAX_REDIRECTS + 1):
        check_public_url(url)
        response = requests.get(url, allow_redirects=False, **kwargs)
        if not response.is_redirect:
            return response
        url = urljoin(url, response.headers["location"])
    raise UnsafeURLError("The page redirects too many times")
