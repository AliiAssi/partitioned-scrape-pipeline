from contextlib import contextmanager

from src.application.exceptions import PipelineError
from src.core.logging import get_logger

logger = get_logger(__name__)


@contextmanager
def capture_run_errors(stage: str):
    # used so anything that escapes a service still lands in the log as structured json, then re-raises
    try:
        yield
    except PipelineError as error:
        logger.error("run_failed", extra={"stage": stage, "error_code": type(error).__name__, "reason": str(error)})
        raise
    except Exception as error:
        logger.error("run_crashed", extra={"stage": stage, "error_code": type(error).__name__, "reason": str(error)})
        raise
