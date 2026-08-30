from scrapy.downloadermiddlewares.retry import RetryMiddleware

from src.core.logging import get_logger

logger = get_logger(__name__)

# subclass of Scrapy's RetryMiddleware that adds logging and changes nothing else.
class RetryLoggingMiddleware(RetryMiddleware):
    def process_response(self, request, response, spider=None):
        # used so a retried status never disappears silently from the run summary
        if response.status in self.retry_http_codes:
            logger.warning(
                "request_retry_scheduled",
                extra={"url": request.url, "status": response.status, "attempt": request.meta.get("retry_times", 0) + 1},
            )
        return super().process_response(request, response)

    def process_exception(self, request, exception, spider=None):
        # used for the transport-level failures, which the status code path never sees
        logger.warning(
            "request_exception",
            extra={"url": request.url, "error_code": type(exception).__name__, "attempt": request.meta.get("retry_times", 0) + 1},
        )
        return super().process_exception(request, exception)
