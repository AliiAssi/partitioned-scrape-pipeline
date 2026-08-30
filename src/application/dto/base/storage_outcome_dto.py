from dataclasses import dataclass
from enum import Enum

from src.application.dto.base.content_hash import ContentHash
from src.application.dto.base.object_key import ObjectKey


class StorageAction(str, Enum):
    WRITTEN = "written"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class StorageOutcomeDTO:
    action: StorageAction
    object_key: ObjectKey
    content_hash: ContentHash
    identifier: str

    @classmethod
    def written(cls, object_key: ObjectKey, content_hash: ContentHash, identifier: str) -> "StorageOutcomeDTO":
        # used when the bytes were new or had changed since the last run
        return cls(StorageAction.WRITTEN, object_key, content_hash, identifier)

    @classmethod
    def unchanged(cls, object_key: ObjectKey, content_hash: ContentHash, identifier: str) -> "StorageOutcomeDTO":
        # used when the hash matched what we already hold, so nothing was written
        return cls(StorageAction.UNCHANGED, object_key, content_hash, identifier)

    @property
    def was_written(self) -> bool:
        return self.action is StorageAction.WRITTEN
