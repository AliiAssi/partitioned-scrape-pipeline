import scrapy

from src.application.dto.base.date_partition import DatePartition
from src.application.dto.base.source_body import SourceBody
from src.application.services_interfaces.source_service_interface import ISourceService

# the crawl logic
class GenericDecisionSpider(scrapy.Spider):
    name = "decisions"

    def __init__(self, source_service: ISourceService, body: SourceBody, partition: DatePartition, **kwargs) -> None:
        # the spider is deliberately source-agnostic: everything site-specific arrives through the service
        super().__init__(**kwargs)
        self._source_service = source_service
        self._body = body
        self._partition = partition

    async def start(self):
        # used for kicking off page one; every later page is chained from the one before it
        yield self._build_listing_request(page_number=1)

    def _build_listing_request(self, page_number: int) -> scrapy.Request:
        # used for asking the source service where this partition's records are listed
        listing = self._source_service.build_listing_request(self._body, self._partition, page_number)
        return scrapy.Request(
            url=listing.url,
            headers=listing.headers,
            callback=self.parse_listing,
            errback=self.handle_listing_failure,
            cb_kwargs={"page_number": page_number},
            # errbacks do not receive cb_kwargs, so the page number travels in meta as well
            meta={"page_number": page_number},
            dont_filter=True,
        )

    def parse_listing(self, response, page_number: int):
        # a page that parses to zero records is how pagination ends, so no total is ever parsed
        page = self._source_service.parse_listing_page(response.body, self._body, self._partition)
        if page_number == 1 and page.reported_total is not None:
            yield {"reported_total": page.reported_total}
        if page.is_empty:
            return

        for record in page.records:
            document = self._source_service.build_document_request(record)
            yield scrapy.Request(
                url=document.url,
                headers=document.headers,
                callback=self.parse_document,
                errback=self.handle_document_failure,
                meta={"record": record},
            )

        yield self._build_listing_request(page_number=page_number + 1)

    def parse_document(self, response):
        # used for handing the raw bytes onward; nothing is decoded or cleaned at this stage
        yield {
            "record": response.meta["record"],
            "payload": response.body,
            "content_type": response.headers.get("Content-Type", b"").decode("latin-1"),
        }

    def handle_listing_failure(self, failure):
        # a listing page we never read leaves the cell's inventory unknown. emitting a row makes the
        # partition fail to reconcile, instead of the pagination chain just stopping silently
        request = getattr(failure, "request", None)
        response = getattr(failure.value, "response", None)
        yield {
            "listing_failed": True,
            "url": request.url if request is not None else None,
            "page_number": request.meta.get("page_number") if request is not None else None,
            "error_code": str(response.status) if response is not None else type(failure.value).__name__,
            "error_reason": str(failure.value)[:500],
        }

    def handle_document_failure(self, failure):
        # used so a failed download still emits a row, which is what keeps found == scraped + failed
        record = failure.request.meta.get("record")
        if record is None:
            return
        response = getattr(failure.value, "response", None)
        yield {
            "record": record,
            "payload": None,
            "error_code": str(response.status) if response is not None else type(failure.value).__name__,
            "error_reason": str(failure.value)[:500],
        }
