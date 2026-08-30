# Architecture

## Why monthly partitions

The unit of work is `(month × body)`, not month alone. Measured on the live site, one month of
Workplace Relations Commission decisions is ~234 records across 24 listing pages; the Labour Court adds
~45. That is large enough to amortise the cost of starting a crawl process and small enough that a
failure retries cheaply. Crossing the month with the body means one slow body cannot stall the others,
a retry re-runs one cell rather than a whole month, and an empty cell is attributable.

The size is configuration (`PARTITION_SIZE`), so weekly or daily is a change to `.env`, not to code.
Weekly would suit the Employment Appeals Tribunal's busiest years — 2,833 records in 2012 — where a
month is closer to 240 listing pages.

## Retries and rate limiting

The search endpoint is the bottleneck, not the site's defences. A listing page is ~810 KB and is served
**without compression** in ~4.9 s; a decision page is ~27 KB and returns in well under a second. Probing
at 8 concurrent requests produced no 429, no 403 and no CAPTCHA, so the constraint we design around is
politeness plus origin latency, not evasion.

- Scrapy's retry middleware is subclassed only to log: every retried status and every transport
  exception is emitted as structured JSON with its URL and attempt number, so a request that quietly
  succeeded on attempt three is still visible.
- Retries cover 429, 408 and 5xx, three times, with AutoThrottle targeting six concurrent requests and
  a 20 s ceiling. Concurrency, delay, timeout and retry count are all environment variables.
- Mongo and MinIO calls go through one `call_with_retries` helper with exponential backoff, so a
  transient storage blip does not lose a partition.
- Pagination stops when a page parses to zero records. Nothing depends on arithmetic over a scraped
  total, which is what usually causes a crawler to stop one page early. Measured: page 25 of a
  24-page month returns HTTP 200 with zero rows, so the stop condition is the observed behaviour
  rather than an assumption — at the cost of one wasted ~800 KB request per cell.
- A listing page that never arrives is emitted as a `listing_failure` row rather than silently
  ending the pagination chain. It marks the cell's inventory incomplete, which is what stops a
  partition that read nothing from reconciling trivially.

**On `robots.txt`.** The site's `robots.txt` disallows `/en/Cases/` — the path the decisions themselves
live on — while the search endpoint we page through is allowed. The intent is unambiguous: the case
documents are not meant to be crawled.

There is a second detail worth stating before someone else finds it. The literal rule would not
actually stop this crawler. The site links its own documents in lowercase (`/en/cases/2024/january/...`),
RFC 9309 path matching is case-sensitive, and Scrapy's parser agrees — `Protego.can_fetch()` returns
`True` for every document URL we request, even with `ROBOTSTXT_OBEY=true`. So the flag is not what
stands between this pipeline and the documents, and leaning on that capitalisation mismatch would be
lawyering rather than an argument.

The decision is therefore made explicitly instead of technically: `ROBOTS_OBEY` is an environment
variable, defaulted to `false` for this assessment, paired with conservative throttling and an honest,
contactable User-Agent. In production against a real client this is where you seek permission or a
data-sharing agreement rather than a config flag.

## Deduplication

Two mechanisms, one in the application and one in the database.

The Mongo `_id` is the composite `body_code:identifier`, and every write is a `replace_one(upsert=True)`.
A unique index on `(identifier, body_code)` backs it, so a duplicate is impossible even if the calling
code is wrong.

Change detection is `DocumentStorageService.store_document_if_content_changed`, which hashes with SHA-256
and compares against what is already stored before writing. If the hash and the object key both match,
nothing is written to either store and the record is counted as `unchanged`. A re-run over the same range
therefore costs listing and document requests but no storage writes at all. Hashing happens twice per
document — once in landing, once over the cleaned bytes in curated — because they answer different
questions: *did the source change?* and *did our extraction change?*

Hashing the raw bytes alone does not work here, and finding that out took a measurement. Every page the
site serves carries `<!-- Elapsed time: 0.0156031 -->`, the server's own render time, which changes on
each request. A first implementation re-wrote 20 to 26 of every 45 documents on an unchanged re-run.
So each record stores two hashes: `file_hash` over the bytes actually written to the object store, and
`content_fingerprint` over a copy with the source's volatile markers blanked out. The fingerprint drives
the change check; `file_hash` still describes the file on disk. Which markup is volatile is source-specific
knowledge, so it sits behind `ISourceService.normalise_for_comparison` rather than in the storage service.
With it, consecutive runs report 45 found, 0 written, 45 unchanged.

The write order is object first, metadata second. A crash between them leaves an orphan object that the
next run overwrites; the reverse order would leave metadata pointing at a file that does not exist.

Measured on the live site: a decision page is 33 270 bytes and the curated extraction of it is 14 623
bytes — the chrome is roughly half the page, not nine tenths of it.

## Supporting 50+ sources

Everything site-specific lives behind `ISourceService`, an application-layer contract with six methods:
list the bodies, build a listing request, parse a listing page, build a document request, extract the
relevant content, and normalise a payload for comparison — the last one being where a source declares
which of its own markup is per-request noise. A source service does no I/O — it turns parameters into request descriptors and bytes
into DTOs — which is why it is business logic rather than infrastructure, and why it is testable against
saved fixture pages with nothing running.

Adding a source is one package under `application/services/sources/`, one registry entry and one config
value. The Scrapy spider, the storage services, the repositories and the Dagster assets are untouched:
the spider cannot tell which source it is crawling and never branches on one.

At fifty sources the parts that would actually change are operational, not structural:

- **Scheduling.** The partition grid becomes `(source × body × month)`; Dagster backfills over three
  dimensions rather than two, and each source needs its own concurrency budget so one slow origin cannot
  starve the pool.
- **Crawl execution.** One subprocess per cell is right at this scale and wrong at fifty sources; the
  `ICrawlRunner` seam is where a queue-backed worker pool or a Modal function would slot in without the
  application layer noticing.
- **Storage layout.** Buckets would be partitioned by source, and the metadata collections sharded on
  `source_name`.
- **Source health.** Fifty parsers break silently in fifty ways. The `records_found == succeeded +
  failures` check already fails a run whose numbers do not reconcile, and `collection_complete` fails
  the ones that have nothing to reconcile because they never read their listing; at scale that becomes
  a per-source freshness and reconciliation dashboard rather than an exit code.
