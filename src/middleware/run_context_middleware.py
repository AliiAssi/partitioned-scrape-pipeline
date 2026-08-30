import uuid
from contextlib import contextmanager

from src.core.logging import bind_log_context, clear_log_context


@contextmanager
def run_context(stage: str, source_name: str, start_date: str, end_date: str):
    # used for tagging every log line in a run with the same id, the way a request id works
    run_id = uuid.uuid4().hex[:12]
    bind_log_context(run_id=run_id, stage=stage, source=source_name, start_date=start_date, end_date=end_date)
    try:
        yield run_id
    finally:
        clear_log_context()
