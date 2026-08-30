from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ObjectKey:
    value: str

    @classmethod
    def for_landing(cls, source_name: str, body_code: str, partition_label: str, filename: str) -> "ObjectKey":
        # used for the raw zone, where the file keeps the name the site gave it
        return cls(f"{source_name}/{body_code}/{partition_label}/{filename}")

    @classmethod
    def for_curated(cls, source_name: str, body_code: str, partition_label: str, identifier: str, extension: str) -> "ObjectKey":
        # used for the curated zone, where the brief requires identifier.ext
        return cls(f"{source_name}/{body_code}/{partition_label}/{identifier}.{extension}")

    @property
    def filename(self) -> str:
        # used for the tail of the key when logging or renaming
        return self.value.rsplit("/", 1)[-1]

    def __str__(self) -> str:
        return self.value
