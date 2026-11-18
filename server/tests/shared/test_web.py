from types import SimpleNamespace

import pytest

from app.shared import web


def _response(status: int, location: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(status_code=status, is_redirect=location is not None, headers={"location": location})


def test_redirect_into_private_network_is_refused(monkeypatch):
    real_check = web.check_public_url  # 127.0.0.1 needs no DNS; only example.org is stubbed
    monkeypatch.setattr(web, "check_public_url", lambda url: None if "example.org" in url else real_check(url))
    hops = iter([_response(302, "http://127.0.0.1:8000/api/health")])
    monkeypatch.setattr(web.requests, "get", lambda url, **kw: next(hops))
    with pytest.raises(web.UnsafeURLError, match="private network"):
        web.get_public("https://example.org/job")


def test_relative_redirects_are_followed_and_checked(monkeypatch):
    checked: list[str] = []
    monkeypatch.setattr(web, "check_public_url", checked.append)
    hops = iter([_response(301, "/jobs/2"), _response(200)])
    monkeypatch.setattr(web.requests, "get", lambda url, **kw: next(hops))
    assert web.get_public("https://example.org/jobs/1").status_code == 200
    assert checked == ["https://example.org/jobs/1", "https://example.org/jobs/2"]


def test_endless_redirects_stop(monkeypatch):
    monkeypatch.setattr(web, "check_public_url", lambda url: None)
    monkeypatch.setattr(web.requests, "get", lambda url, **kw: _response(302, "/again"))
    with pytest.raises(web.UnsafeURLError, match="too many"):
        web.get_public("https://example.org/loop")


def test_with_scheme_adds_https_even_when_the_host_starts_with_http():
    assert web.with_scheme("httpsladgovcom.applytojob.com/apply/x") == "https://httpsladgovcom.applytojob.com/apply/x"
    assert web.with_scheme("apply.workable.com/j/1") == "https://apply.workable.com/j/1"
    assert web.with_scheme("http://a.org/j") == "http://a.org/j"
    assert web.with_scheme("HTTPS://a.org/j") == "HTTPS://a.org/j"
