from abc import ABC, abstractmethod

from src.application.dto.base.object_key import ObjectKey


class IReadOnlyObjectStore(ABC):
    @abstractmethod
    def get_object(self, key: ObjectKey) -> bytes:
        # used for reading a landing file during transformation
        ...

    @abstractmethod
    def object_exists(self, key: ObjectKey) -> bool:
        ...


class IObjectStore(IReadOnlyObjectStore):
    @abstractmethod
    def ensure_bucket(self) -> None:
        ...

    @abstractmethod
    def put_object(self, key: ObjectKey, payload: bytes, content_type: str) -> None:
        # used for the only write path into a bucket
        ...
