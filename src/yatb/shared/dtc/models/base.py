import hashlib
from functools import lru_cache

from pydantic import BaseModel


class BaseETCDModel(BaseModel):
    def make_binary(self) -> bytes:
        return self.model_dump_json(indent=None).encode()

    @staticmethod
    @lru_cache(maxsize=128)
    def encode(source: str) -> str:
        # FIXME: wtf this is it...
        return hashlib.sha256(b"v3[45nuyoewnbui]" + source.encode() + b"orbi7hwone67b").hexdigest()[:8]
