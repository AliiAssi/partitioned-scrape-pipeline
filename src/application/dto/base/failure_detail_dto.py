from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FailureDetailDTO:
    identifier: str | None
    url: str | None
    error_code: str
    reason: str

    @classmethod
    def from_error(cls, error: Exception) -> "FailureDetailDTO":
        # used so every dropped record ends up in the log with a url and a reason
        return cls(
            identifier=getattr(error, "identifier", None),
            url=getattr(error, "url", None),
            error_code=getattr(error, "error_code", type(error).__name__),
            reason=str(error),
        )

    def as_log_fields(self) -> dict[str, str | None]:
        # used for flattening the failure into the json log line
        return {
            "failed_identifier": self.identifier,
            "failed_url": self.url,
            "error_code": self.error_code,
            "reason": self.reason,
        }
