# Workplace Relations decisions pipeline

A Scrapy pipeline that scrapes decisions and determinations from the Irish
[Workplace Relations](https://www.workplacerelations.ie/en/search/) database, stores the raw documents in
object storage with their metadata in MongoDB, and then transforms them into a cleaned, renamed curated
zone. Ingest and transform are orchestrated as separate partitioned Dagster assets.

## What it scrapes

Four tribunals publish through the same search page — the Workplace Relations Commission, the Labour
Court, the Equality Tribunal and the Employment Appeals Tribunal. The last two were largely folded into
the WRC by the Workplace Relations Act 2015, but they kept issuing decisions well past it, so every body
is queried for every partition rather than being skipped on an assumed end date. An empty month costs one
request; a wrongly skipped one loses records silently.

The pipeline walks a date range one month at a time, asks each body what it published in that month,
pages through every result, stores each decision document, and records its metadata.

## Prerequisites

- Python 3.13
- Docker with Compose

## Setup

```bash
cp .env.example .env
python -m venv .venv && pip install -r requirements-dev.txt
docker compose up -d
```

MongoDB listens on `27017`. MinIO listens on `9000`, with its console on
[localhost:9001](http://localhost:9001) (`minioadmin` / `minioadmin`).

## Running it

Both stages, one command:

```bash
.venv/bin/python app.py run --start-date 01/01/2024 --end-date 01/03/2024
```

The same commands run in a container against the same compose network — the `pipeline` service sits
behind a `cli` profile so `docker compose up -d` still starts storage only:

```bash
docker compose run --rm pipeline run --start-date 01/01/2024 --end-date 01/03/2024
```

Or one stage at a time:

```bash
.venv/bin/python app.py ingest --start-date 01/01/2024 --end-date 01/02/2024
```

```bash
.venv/bin/python app.py transform --start-date 01/01/2024 --end-date 01/02/2024
```

Restrict to particular bodies with a repeatable flag:

```bash
.venv/bin/python app.py ingest --start-date 01/01/2024 --end-date 01/02/2024 --body wrc --body labour_court
```

Dates accept `dd/mm/yyyy` or `yyyy-mm-dd`. The start date is inclusive and the end date is exclusive, so
`01/01/2024` to `01/03/2024` is January and February.

The process exits `1` if any partition's numbers do not reconcile — that is, if the count the site
reported does not equal the records stored plus the failures logged, or if a listing page could not
be read at all, which leaves the count itself unknown. A crawl that dies fails its own cell and the
remaining cells still run.

## Running it with Dagster

Dagster keeps run history, event logs and schedule state under `DAGSTER_HOME`; without it, it stores
them in a temp directory and discards them on exit. It has to be an absolute path in the shell
environment — `dagster dev` reads it from the process environment, so a value in `.env` is ignored.
From the repo root:

```bash
mkdir -p .dagster_home && DAGSTER_HOME="$PWD/.dagster_home" .venv/bin/dagster dev -m src.presentation.orchestration.definitions
```

Open [localhost:3000](http://localhost:3000). `landing_documents` and `curated_documents` are partitioned
on `(month × body)`; `curated_documents` depends on `landing_documents`, so materialising a cell runs
ingest before transform. Backfill a range by selecting both assets and choosing the partitions.

## What lands where

| | Landing | Curated |
|---|---|---|
| Bucket | `landing` | `curated` |
| Collection | `landing_decisions` | `curated_decisions` |
| Object key | `{source}/{body}/{month}/{site-filename}` | `{source}/{body}/{month}/{identifier}.{ext}` |
| Content | exactly as served | HTML stripped to the decision text; PDFs untouched |

The landing zone is never modified or deleted. The transformation service holds a read-only handle to it,
so that is enforced by the type system rather than by convention.

A metadata record looks like this:

```json
{
  "_id": "wrc:ADJ-00047352",
  "identifier": "ADJ-00047352",
  "body_code": "wrc",
  "body_name": "Workplace Relations Commission",
  "title": "ADJ-00047352",
  "description": "Car Valet V Motor Garage",
  "decision_date": "2024-01-31T00:00:00Z",
  "source_url": "https://www.workplacerelations.ie/en/cases/2024/january/adj-00047352.html",
  "partition_date": "2024-01",
  "content_type": "text/html",
  "file_path": "workplace_relations/wrc/2024-01/adj-00047352.html",
  "file_hash": "sha256:...",
  "scraped_at": "2026-08-29T18:41:02Z"
}
```

## Idempotency

Running the pipeline twice over the same range creates no duplicate records and rewrites no unchanged
files. Metadata is keyed on `body_code:identifier` and always upserted; documents are only written when
their content hash differs from what is already stored. The second run reports every record as
`unchanged`.

Each record carries two hashes. `file_hash` covers the bytes actually written to the object store.
`content_fingerprint` covers the same bytes with the source's per-request noise blanked out — this site
stamps its own render time into every page, so a raw byte hash reports about half the documents as
changed on every run. The fingerprint is what the change check compares.

## Logs

Every line is JSON on stdout, carrying the run id, stage, source and date range — including the
closing summary the command prints, so a whole run pipes through `jq` without a special case. Each
partition emits a start and a completion line with records found, written, unchanged and failed;
every dropped record is logged individually with its URL and error code; the run ends with a summary.
Anything written for a human — validation errors, tracebacks — goes to stderr.

```json
{"timestamp":"...","level":"INFO","logger":"src.application.services.run_summary_service",
 "event":"partition_completed","run_id":"a1b2c3d4e5f6","stage":"ingest","source":"workplace_relations",
 "start_date":"2024-01-01","end_date":"2024-02-01","partition":"2024-01","body":"wrc",
 "records_found":234,"records_written":234,"records_unchanged":0,"records_failed":0,
 "duration_seconds":128.4,"collection_complete":true,"accounted_for":true}
```

`collection_complete` is false when a listing page never arrived. It is separate from the arithmetic
on purpose: a cell that read nothing has nothing to add up, and would otherwise reconcile trivially.

Secrets are held as pydantic `SecretStr` (`config.py`) so they are not stringified by accident, but
there is no redaction filter on the log formatter — nothing currently logs a credential, and the
guarantee is "we do not log them", not "we scrub them on the way out".

## Tests

```bash
.venv/bin/python -m pytest tests -q
```

`tests/unit` and `tests/e2e` run with nothing else up: the parsers work against small page fixtures, and
the end-to-end tests drive both stages through in-memory storage, including the assertion that a second
run writes nothing even when the site's render-time comment has moved.

`tests/integration` reaches outside the process and skips itself when it cannot: the storage tests
need the containers, and `test_body_catalog_drift.py` fetches the live search page and checks the
four bodies in `wrc_config.py` still match the site's own Body filter. That catalog is deliberately
a constant — it carries our body codes and the active date ranges the site never publishes, and it
feeds Dagster's partition keys — so this is the guard that notices if the site adds, renames or
renumbers one.

## Configuration

Every connection string, bucket, collection, partition size and crawl parameter comes from the
environment; see `.env.example`. Three things are deliberately constants rather than settings: the
AutoThrottle delay bounds and Scrapy's own log level (`scrapy_settings.py`), and the Dagster grid's
start date (`partition_grid.py`), which cannot move without renaming every partition key.

One setting deserves attention: `ROBOTS_OBEY`. The site's `robots.txt` disallows `/en/Cases/`, where the
decision documents live, while allowing the search endpoint. It defaults to `false` here so the pipeline
does what the assessment asks. Note that the literal rule would not in fact block this crawler — see
[ARCHITECTURE.md](ARCHITECTURE.md), which explains why that is not the argument being made.

## Layout

```text
src/
├── presentation/     cli commands, dagster assets, request and result schemas
├── application/      dtos, services, service interfaces — the pipeline's business logic
├── infrastructure/   scrapy, mongo, minio, and the interfaces they satisfy
├── core/             config, logging, providers
├── middleware/       run context, error capture
└── utils/            date parsing, retry, text helpers
```

Dependencies point inward: presentation calls application, infrastructure implements interfaces the
application declares. `src/core/providers.py` is the only place an interface is bound to a class — it
returns one frozen `PipelineServices` object that the CLI and the Dagster assets both consume, which is
why swapping MinIO for S3 or Mongo for DocumentDB is a diff in one file.
