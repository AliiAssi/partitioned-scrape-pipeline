from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ListingRequestDTO:
    url: str
    headers: dict[str, str] = field(default_factory=dict)
