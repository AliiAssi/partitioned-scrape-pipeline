import json
import shutil
import subprocess
import sys
import tempfile
import threading
from collections import deque
from pathlib import Path
from typing import IO

from src.application.dto.base.date_partition import DatePartition
from src.application.dto.base.failure_detail_dto import FailureDetailDTO
from src.application.dto.base.partition_work_dto import PartitionWorkDTO
from src.application.dto.base.source_body import SourceBody
from src.application.dto.ingestion.ingest_partition_input_dto import CrawledItemDTO
from src.application.exceptions import PartitionIngestionError
from src.core.config import Settings
from src.core.logging import current_log_context, get_logger
from src.infrastructure.scraping.crawl_runner_interface import ICrawlRunner
from src.infrastructure.scraping.pipelines.record_emitting_pipeline import ITEMS_FILENAME, row_to_record

logger = get_logger(__name__)

ENTRYPOINT_MODULE = "src.infrastructure.scraping.crawl_entrypoint"

# how much of a failed crawl's stderr is kept for the error log; a traceback is rarely longer
STDERR_TAIL_LINES = 50


def _drain(stream: IO[str], sink: deque[str]) -> None:
    # used for consuming the child's stderr without blocking the stdout loop that streams its logs
    with stream:
        for line in stream:
            sink.append(line)


class CrawlRunner(ICrawlRunner):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def crawl_partition(self, source_name: str, body: SourceBody, partition: DatePartition) -> PartitionWorkDTO:
        # one subprocess per cell, so a crawler crash takes down a partition rather than the worker
        workspace = Path(tempfile.mkdtemp(prefix=f"{body.code}_{partition.label}_", dir=self._workspace_root()))
        try:
            self._run_crawl_process(source_name, body, partition, workspace)
            reported_total, items, collection_failures = self._read_items(workspace)
            return PartitionWorkDTO(
                items=items,
                expected_total=reported_total,
                collection_failures=tuple(collection_failures),
            )
        finally:
            # documents are read into memory first, so the handoff directory never outlives the call
            shutil.rmtree(workspace, ignore_errors=True)

    def _workspace_root(self) -> str:
        # used for keeping every crawl handoff under one configurable directory
        root = Path(self._settings.crawl_workspace_dir)
        root.mkdir(parents=True, exist_ok=True)
        return str(root)

    def _run_crawl_process(self, source_name: str, body: SourceBody, partition: DatePartition, workspace: Path) -> None:
        # used for driving scrapy without importing it into the orchestrator's process
        command = [
            sys.executable,
            "-m",
            ENTRYPOINT_MODULE,
            "--source", source_name,
            "--body-code", body.code,
            "--start", partition.start.isoformat(),
            "--end", partition.end.isoformat(),
            "--size", partition.size,
            "--output-dir", str(workspace),
            # the child is a separate process, so the run's identity has to travel as an argument
            "--run-id", str(current_log_context().get("run_id", "")),
        ]
        logger.info("crawl_started", extra={"partition": partition.label, "body": body.code})

        # streamed, not captured. a partition takes minutes, and buffering the child until it exits
        # gives no progress signal and then replays its whole log after the parent's "crawl_started",
        # out of the order things actually happened in.
        stderr_tail: deque[str] = deque(maxlen=STDERR_TAIL_LINES)
        with subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
        ) as process:
            # stderr is drained on a thread so a long traceback cannot fill its pipe buffer and
            # deadlock the child while we are busy reading stdout
            drain = threading.Thread(target=_drain, args=(process.stderr, stderr_tail), daemon=True)
            drain.start()
            for line in process.stdout:
                # the child logs json through the same formatter as the parent, so it passes straight
                # through and stays interleaved with our own lines in real time
                sys.stdout.write(line)
                sys.stdout.flush()
            drain.join(timeout=5)

        if process.returncode != 0:
            logger.error(
                "crawl_process_failed",
                extra={"partition": partition.label, "body": body.code, "stderr": "".join(stderr_tail)[-2000:]},
            )
            raise PartitionIngestionError(f"crawl failed for {body.code} {partition.label}")

    def _read_items(self, workspace: Path) -> tuple[int | None, list[CrawledItemDTO], list[FailureDetailDTO]]:
        # used for reading the jsonl handoff back into dtos, one line per record found
        items_path = workspace / ITEMS_FILENAME
        if not items_path.exists():
            return None, [], []

        reported_total: int | None = None
        items: list[CrawledItemDTO] = []
        collection_failures: list[FailureDetailDTO] = []
        with items_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                row_type = row.get("row_type")
                if row_type == "summary":
                    reported_total = row.get("reported_total")
                    continue
                if row_type == "listing_failure":
                    # a page of the listing we never read, so this cell's inventory is incomplete
                    collection_failures.append(
                        FailureDetailDTO(
                            identifier=None,
                            url=row.get("url"),
                            error_code=row.get("error_code") or "listing_page_unreadable",
                            reason=row.get("error_reason") or "listing page could not be read",
                        )
                    )
                    continue
                local_path = row.get("local_path")
                items.append(
                    CrawledItemDTO(
                        record=row_to_record(row),
                        payload=Path(local_path).read_bytes() if local_path else None,
                        error_code=row.get("error_code"),
                        error_reason=row.get("error_reason"),
                    )
                )
        return reported_total, items, collection_failures
