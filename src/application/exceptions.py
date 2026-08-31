class PipelineError(Exception):
    pass


class ConfigurationError(PipelineError):
    pass


class UnknownSourceError(PipelineError):
    pass


class PartitionIngestionError(PipelineError):
    pass


class RecordProcessingError(PipelineError):
    def __init__(self, message: str, *, identifier: str | None = None, url: str | None = None, error_code: str | None = None) -> None:
        # used so every record-level failure carries the url and code the log line needs
        super().__init__(message)
        self.identifier = identifier
        self.url = url
        self.error_code = error_code or type(self).__name__


class DocumentDownloadError(RecordProcessingError):
    pass


class ContentExtractionError(RecordProcessingError):
    pass


class DocumentReadError(RecordProcessingError):
    pass


class DuplicateCaseReferenceError(RecordProcessingError):
    pass


class ListingParseError(PipelineError):
    pass
