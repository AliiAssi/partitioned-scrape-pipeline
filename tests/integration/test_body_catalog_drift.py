import ssl
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest
from bs4 import BeautifulSoup

from src.application.services.sources.workplace_relations import wrc_config
from src.core.config import Settings
from src.utils.text_normalization import collapse_whitespace

settings = Settings()
FETCH_TIMEOUT_SECONDS = 90


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _find_body_filter_group(soup: BeautifulSoup):
    label = next(
        (
            node
            for node in soup.find_all("label")
            if node.get("for") and collapse_whitespace(node.get_text(" ")) == wrc_config.BODY_FILTER_LABEL_TEXT
        ),
        None,
    )
    assert label is not None, "the search page no longer has a filter labelled 'Body'"
    group = soup.select_one(f"span#{label['for']}")
    assert group is not None, f"the Body label points at #{label['for']}, which holds no checkbox group"
    return group


@pytest.fixture(scope="module")
def bodies_offered_by_the_site() -> dict[str, str]:
    # {external_id: name} exactly as the live filter panel lists them
    request = Request(f"{wrc_config.SEARCH_ENDPOINT}?decisions=1", headers={"User-Agent": settings.user_agent})
    try:
        with urlopen(request, timeout=FETCH_TIMEOUT_SECONDS, context=_ssl_context()) as response:
            payload = response.read()
    except URLError as error:
        # a certificate problem is our misconfiguration, not the site being down: skipping on it would
        # turn this guard green for the wrong reason, which is the one failure mode it must not have
        if isinstance(error.reason, ssl.SSLError):
            raise
        pytest.skip(f"workplacerelations.ie is not reachable: {error.reason}")
    except (TimeoutError, ConnectionError) as error:
        pytest.skip(f"workplacerelations.ie is not reachable: {error}")

    group = _find_body_filter_group(BeautifulSoup(payload, "html.parser"))
    offered = {}
    for checkbox in group.select("input[type=checkbox][value]"):
        name = group.select_one(f"label[for='{checkbox['id']}']")
        offered[checkbox["value"]] = collapse_whitespace(name.get_text(" ")) if name else ""
    assert offered, "the Body filter parsed to nothing; the panel markup has changed"
    return offered


def test_no_body_has_been_added_removed_or_renumbered(bodies_offered_by_the_site):
    # the ids go straight into the search url, so drift here silently breaks the scrape
    assert set(bodies_offered_by_the_site) == {body.external_id for body in wrc_config.WRC_BODIES}


def test_no_body_has_been_renamed(bodies_offered_by_the_site):
    # names are cosmetic — they are stored as body_name — so this is a softer signal than the ids
    assert bodies_offered_by_the_site == {body.external_id: body.name for body in wrc_config.WRC_BODIES}
