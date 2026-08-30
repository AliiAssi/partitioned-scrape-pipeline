import hashlib
from dataclasses import dataclass

from src.core.constants import HASH_ALGORITHM


@dataclass(frozen=True, slots=True)
class ContentHash:
    algorithm: str
    digest: str

    @classmethod
    def of_bytes(cls, payload: bytes) -> "ContentHash":
        # used as the only place bytes ever get hashed in this codebase
        return cls(algorithm=HASH_ALGORITHM, digest=hashlib.new(HASH_ALGORITHM, payload).hexdigest())

    @classmethod
    def from_stored(cls, stored: str | None) -> "ContentHash | None":
        # used for rebuilding a hash read back out of mongo
        if not stored or ":" not in stored:
            return None
        algorithm, _, digest = stored.partition(":")
        return cls(algorithm=algorithm, digest=digest)

    def __str__(self) -> str:
        # used so the stored form always carries its algorithm with it
        return f"{self.algorithm}:{self.digest}"
