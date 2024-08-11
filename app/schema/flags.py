import binascii
import hmac
from enum import Enum, auto
from typing import ClassVar, Literal

from ..config import settings
from .ebasemodel import EBaseModel
from .user import User


class FlagCheckResult(Enum):
    invalid = auto()
    valid = auto()
    invalid_sign = auto()


class Flag(EBaseModel):
    __public_fields__: ClassVar = {"classtype"}
    __admin_only_fields__: ClassVar = {"flag_base"}

    classtype: Literal["Flag"] = "Flag"
    flag_base: str = settings.FLAG_BASE

    def sanitization(self, user_flag: str) -> str:
        if self.flag_base + "{" in user_flag:
            user_flag = user_flag.replace(self.flag_base + "{", "", 1)
        if user_flag[-1] == "}":
            user_flag = user_flag[:-1]
        user_flag = self.flag_base + "{" + user_flag + "}"

        return user_flag  # noqa: RET504

    def flag_value(self, user: User) -> str:
        return self.flag_base + "{test_flag}"

    def flag_checker(self, user_flag: str, user: User) -> FlagCheckResult:
        if self.flag_value(user) == self.sanitization(user_flag):
            return FlagCheckResult.valid

        return FlagCheckResult.invalid


class StaticFlag(Flag):
    __admin_only_fields__: ClassVar = {"flag_base", "flag"}

    classtype: Literal["StaticFlag"] = "StaticFlag"
    flag: str

    def flag_value(self, user: User) -> str:
        return self.flag_base + "{" + self.flag + "}"


class DynamicKKSFlag(Flag):
    __admin_only_fields__: ClassVar = {"flag_base", "dynamic_flag_base"}

    classtype: Literal["DynamicKKSFlag"] = "DynamicKKSFlag"
    dynamic_flag_base: str

    def flag_parts(self, user: User) -> tuple[str, str]:
        flag_part = "{" + self.dynamic_flag_base + "}" + f"{user.user_id}"
        hash = hmac.digest(settings.FLAG_SIGN_KEY.encode(), flag_part.encode(), "sha256")
        return self.dynamic_flag_base, binascii.hexlify(hash).decode()[0:14]

    def flag_value(self, user: User) -> str:
        base, hash = self.flag_parts(user)
        return self.flag_base + "{" + base + "_" + hash + "}"

    def flag_checker(self, user_flag: str, user: User) -> FlagCheckResult:
        sanitized_flag = self.sanitization(user_flag)
        if self.flag_value(user) == sanitized_flag:
            return FlagCheckResult.valid

        # some of copypaste, but i have no idea how to make this without copypaste
        base, hash = self.flag_parts(user)
        prefix = self.flag_base + "{" + base
        if sanitized_flag.startswith(prefix):
            return FlagCheckResult.invalid_sign

        return FlagCheckResult.invalid
