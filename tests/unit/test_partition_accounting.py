import json
from datetime import date

from src.application.dto.base.failure_detail_dto import FailureDetailDTO
from src.application.dto.base.partition_result_dto import PartitionResultDTO, RunResultDTO
from src.core.config import Settings
from src.infrastructure.scraping.crawl_runner import CrawlRunner
from src.infrastructure.scraping.pipelines.record_emitting_pipeline import ITEMS_FILENAME


def _partition(**overrides) -> PartitionResultDTO:
    fields = dict(
        partition_label="2024-01", body_code="wrc", stage="ingest",
        records_found=0, records_written=0, records_unchanged=0, duration_seconds=0.1,
    )
    fields.update(overrides)
    return PartitionResultDTO(**fields)


def test_a_balanced_cell_is_accounted_for():
    result = _partition(records_found=3, records_written=2, records_unchanged=1)
    assert result.is_accounted_for


def test_a_cell_whose_listing_was_never_read_cannot_reconcile():
    # the arithmetic balances -- nothing found, nothing stored, no record-level failure -- and it
    # still must not count as accounted for, because we never learned what the cell contained
    result = _partition(collection_complete=False)

    assert result.records_found == result.records_succeeded + len(result.failures)
    assert not result.is_accounted_for
    assert result.as_log_fields()["collection_complete"] is False


def test_one_incomplete_cell_fails_the_whole_run():
    run = RunResultDTO(
        stage="ingest", source_name="workplace_relations",
        start_date="2024-01-01", end_date="2024-02-01",
        partitions=[_partition(records_found=3, records_written=3), _partition(collection_complete=False)],
    )

    assert not run.collection_complete
    assert not run.has_no_unexplained_failures


def test_the_summary_line_is_one_parseable_json_object():
    # the cli prints exactly this, so stdout stays a json stream the whole way through
    run = RunResultDTO("ingest", "workplace_relations", "2024-01-01", "2024-02-01", [_partition()])

    line = json.dumps(run.as_log_fields())

    assert json.loads(line)["accounted_for"] is True
    assert "\n" not in line


def test_the_handoff_reader_turns_a_listing_failure_row_into_a_collection_failure(tmp_path):
    # the jsonl handoff is the contract between the crawl subprocess and the parent, and _read_items
    # is the pure half of it, so it is testable without spawning anything
    (tmp_path / ITEMS_FILENAME).write_text(
        json.dumps({"row_type": "summary", "reported_total": 234}) + "\n"
        + json.dumps({
            "row_type": "record", "identifier": "ADJ-00047352", "body_code": "wrc",
            "body_name": "Workplace Relations Commission", "title": "ADJ-00047352",
            "description": "Car Valet V Motor Garage", "decision_date": "2024-01-31",
            "source_url": "https://example.test/a.html", "document_url": "https://example.test/a.html",
            "partition_date": "2024-01", "content_type": "text/html",
            "source_name": "workplace_relations", "local_path": None,
            "error_code": "504", "error_reason": "504 Gateway Timeout",
        }) + "\n"
        + json.dumps({
            "row_type": "listing_failure", "url": "https://example.test/en/search/?pageNumber=5",
            "page_number": 5, "error_code": "504", "error_reason": "504 Gateway Timeout",
        }) + "\n",
        encoding="utf-8",
    )

    reported_total, items, collection_failures = CrawlRunner(Settings())._read_items(tmp_path)

    assert reported_total == 234
    assert len(items) == 1 and items[0].failed and items[0].record.decision_date == date(2024, 1, 31)
    assert [f.error_code for f in collection_failures] == ["504"]
    assert collection_failures[0].url.endswith("pageNumber=5")
