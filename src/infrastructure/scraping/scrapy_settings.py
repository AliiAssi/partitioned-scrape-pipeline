from src.core.config import Settings


def build_crawler_settings(settings: Settings) -> dict[str, object]:
    # used for turning our one config object into the settings scrapy expects
    return {
        "BOT_NAME": "wrc_pipeline",
        "USER_AGENT": settings.user_agent,
        "ROBOTSTXT_OBEY": settings.robots_obey,
        "CONCURRENT_REQUESTS_PER_DOMAIN": settings.concurrent_requests_per_domain,
        "DOWNLOAD_DELAY": settings.download_delay,
        "DOWNLOAD_TIMEOUT": settings.download_timeout,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": settings.retry_times,
        "RETRY_HTTP_CODES": [429, 500, 502, 503, 504, 522, 524, 408],
        "AUTOTHROTTLE_ENABLED": settings.autothrottle_enabled,
        "AUTOTHROTTLE_START_DELAY": 0.5,
        "AUTOTHROTTLE_MAX_DELAY": 20.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": settings.autothrottle_target_concurrency,
        "COOKIES_ENABLED": False,
        "TELNETCONSOLE_ENABLED": False,
        "LOG_ENABLED": True,
        "LOG_LEVEL": "WARNING",
        "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "src.infrastructure.scraping.middlewares.retry_logging_middleware.RetryLoggingMiddleware": 550,
        },
        "ITEM_PIPELINES": {
            "src.infrastructure.scraping.pipelines.record_emitting_pipeline.RecordEmittingPipeline": 300,
        },
    }
