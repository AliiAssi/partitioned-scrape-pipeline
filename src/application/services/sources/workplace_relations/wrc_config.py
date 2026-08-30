import re

from src.application.dto.base.source_body import SourceBody

SOURCE_NAME = "workplace_relations"

SITE_ROOT = "https://www.workplacerelations.ie"
SEARCH_ENDPOINT = f"{SITE_ROOT}/en/search/"

WRC_BODIES: tuple[SourceBody, ...] = (
    SourceBody(code="wrc", name="Workplace Relations Commission", external_id="15376"),
    SourceBody(code="labour_court", name="Labour Court", external_id="3"),
    SourceBody(code="equality_tribunal", name="Equality Tribunal", external_id="1"),
    SourceBody(code="employment_appeals_tribunal", name="Employment Appeals Tribunal", external_id="2"),
)


LISTING_QUERY_TEMPLATE = (
    "decisions=1"
    "&from={date_from}"
    "&to={date_to}"
    "&legislationsub="
    "&body={body_id}"
    "&pageNumber={page_number}"
)


BODY_FILTER_LABEL_TEXT = "Body"

LISTING_ROW_SELECTOR = "li.each-item"
LISTING_LINK_SELECTOR = "h2.title a[href]"
LISTING_DATE_SELECTOR = "span.date"
LISTING_REFERENCE_SELECTOR = "span.refNO"
LISTING_DESCRIPTION_SELECTOR = "p.description"

# the site prints its own "234 results" count, which is the one number we did not derive ourselves —
# it is what the found-vs-scraped reconciliation compares against
REPORTED_TOTAL_PATTERN = re.compile(r"([\d,]+)\s+results", re.IGNORECASE)

# Decision page markup 
CONTENT_SELECTORS = (
    "div.container.mb-4 div.row div.col-sm-9",
    "div.container.mb-4 div.container div.row div.col-sm-9",
)

# site chrome to drop before the cleaned document is written to the curated zone
STRIP_SELECTORS = (
    "script",
    "style",
    "noscript",
    "iframe",
    "header",
    "footer",
    "nav",
    ".cookie",
    ".social-banner",
    ".searchbanner",
    ".return-to-search",
    ".no-print",
)

# one back-link carries no class, so it is matched on its text instead
RETURN_LINK_TEXT = "return to search"

CURATED_DOCUMENT_TEMPLATE = (
    "<!DOCTYPE html>\n"
    '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    "<title>{title}</title>\n</head>\n<body>\n{content}\n</body>\n</html>\n"
)

# it is very critical, Volatile markup

# Every page carries the server's own render time, which changes on every request:
#     <!-- Elapsed time: 0.0156031 -->
VOLATILE_MARKERS: tuple[re.Pattern[bytes], ...] = (re.compile(rb"<!--\s*Elapsed time:[^>]*-->"),)
