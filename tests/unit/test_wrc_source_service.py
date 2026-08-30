from datetime import date

import pytest

from src.application.dto.base.date_partition import DatePartition
from src.application.services.sources.workplace_relations.wrc_content_extractor import WrcContentExtractor
from src.application.services.sources.workplace_relations.wrc_listing_parser import WrcListingParser
from src.application.services.sources.workplace_relations.wrc_source_service import WrcSourceService
from tests.fixtures import DECISION_PAGE, DECISION_PAGE_RESERVED, EMPTY_LISTING_PAGE, LISTING_PAGE

service = WrcSourceService(WrcListingParser(), WrcContentExtractor())
JANUARY_2024 = DatePartition(date(2024, 1, 1), date(2024, 2, 1), "monthly")
WRC = next(body for body in service.list_available_bodies() if body.code == "wrc")


def test_the_listing_url_is_the_stateless_get_the_search_post_redirects_to():
    request = service.build_listing_request(WRC, JANUARY_2024, 3)
    assert request.url == (
        "https://www.workplacerelations.ie/en/search/?decisions=1"
        "&from=01/01/2024&to=31/01/2024&legislationsub=&body=15376&pageNumber=3"
    )


def test_rows_are_parsed_with_the_date_from_the_row_not_the_url():
    page = service.parse_listing_page(LISTING_PAGE, WRC, JANUARY_2024)
    record = next(r for r in page.records if r.identifier == "ADJ-00047352")

    assert len(page.records) == 3
    assert page.reported_total == 3
    assert record.decision_date == date(2024, 1, 31)
    assert record.partition_date == "2024-01"
    assert record.storage_id == "wrc:ADJ-00047352"
    assert record.description == "Car Valet V Motor Garage"


def test_a_page_past_the_end_parses_to_nothing_which_is_how_pagination_stops():
    assert service.parse_listing_page(EMPTY_LISTING_PAGE, WRC, JANUARY_2024).is_empty


def test_extraction_keeps_the_decision_and_drops_the_chrome():
    cleaned = service.extract_relevant_content(DECISION_PAGE, "text/html")

    assert b"Summary of Workers Case" in cleaned
    assert b"Return to Search" not in cleaned
    assert b"cookie" not in cleaned.lower()
    assert b"Data Protection" not in cleaned
    assert b"var tracking" not in cleaned


def test_the_per_request_render_time_is_blanked_before_content_is_compared():
    assert DECISION_PAGE != DECISION_PAGE_RESERVED
    assert service.normalise_for_comparison(DECISION_PAGE, "text/html") == service.normalise_for_comparison(
        DECISION_PAGE_RESERVED, "text/html"
    )


@pytest.mark.parametrize("method", ["extract_relevant_content", "normalise_for_comparison"])
def test_a_pdf_is_never_touched(method):
    payload = b"%PDF-1.7 Elapsed time: 3"
    assert getattr(service, method)(payload, "application/pdf") == payload
