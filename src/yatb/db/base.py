import datetime
import uuid
from typing import Any, Self

from beanie import Document

from yatb.ebasemodelv2 import EBaseModelV2


class DocumentEx[T: EBaseModelV2](Document):
    @classmethod
    def make_db_model(cls: type[Self], base: T) -> Self:
        return cls.model_validate(base, from_attributes=True)

    def update_entry_raw(self, data: dict[str, Any]) -> None:
        for i, v in data.items():
            if i in self.model_fields:
                setattr(self, i, v)

    @staticmethod
    def sanitize_dict(d: dict[uuid.UUID, datetime.datetime]) -> dict[str, datetime.datetime]:
        return {str(i): v for i, v in d.items()}

    async def update_entry(self, new: T) -> Self: ...
