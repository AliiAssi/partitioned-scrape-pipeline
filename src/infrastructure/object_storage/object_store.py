import io

from minio import Minio
from minio.error import S3Error
from urllib3.exceptions import HTTPError

from src.application.dto.base.object_key import ObjectKey
from src.core.config import Settings
from src.core.logging import get_logger
from src.infrastructure.object_storage_interfaces.object_store_interface import IObjectStore
from src.utils.retry import call_with_retries

logger = get_logger(__name__)

RETRYABLE_STORAGE_ERRORS = (HTTPError, ConnectionError)


class ObjectStore(IObjectStore):
    def __init__(self, client: Minio, bucket_name: str, settings: Settings) -> None:
        self._client = client
        self._bucket_name = bucket_name
        self._settings = settings

    def ensure_bucket(self) -> None:
        # used at startup so the first put does not fail on a missing bucket
        if not self._client.bucket_exists(self._bucket_name):
            self._client.make_bucket(self._bucket_name)
            logger.info("bucket_created", extra={"bucket": self._bucket_name})

    def put_object(self, key: ObjectKey, payload: bytes, content_type: str) -> None:
        # used for the only write path into a bucket
        self._run(
            lambda: self._client.put_object(
                self._bucket_name,
                key.value,
                io.BytesIO(payload),
                length=len(payload),
                content_type=content_type,
            ),
            f"put:{key.value}",
        )

    def get_object(self, key: ObjectKey) -> bytes:
        # used for reading a landing file back during transformation
        def read() -> bytes:
            response = self._client.get_object(self._bucket_name, key.value)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        return self._run(read, f"get:{key.value}")

    def object_exists(self, key: ObjectKey) -> bool:
        # used by tests and by the coverage checks
        try:
            self._client.stat_object(self._bucket_name, key.value)
            return True
        except S3Error:
            return False

    def _run(self, operation, description: str):
        # used for wrapping every call in the same backoff instead of repeating try blocks
        return call_with_retries(
            operation,
            attempts=self._settings.storage_retry_attempts,
            backoff_seconds=self._settings.storage_retry_backoff_seconds,
            retry_on=RETRYABLE_STORAGE_ERRORS,
            description=f"minio.{self._bucket_name}.{description}",
        )


def build_minio_client(settings: Settings) -> Minio:
    # used so the credentials are read in exactly one place
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key_value,
        secret_key=settings.minio_secret_key_value,
        secure=settings.minio_secure,
    )
