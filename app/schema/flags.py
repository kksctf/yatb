import binascii
import hmac
from typing import ClassVar, Literal

from ..config import settings
from .ebasemodel import EBaseModel
from .user import User


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

        return user_flag

    def flag_value(self, user: User) -> str:
        return self.flag_base + "{test_flag}"

    def flag_checker(self, user_flag: str, user: User) -> bool:
        if self.flag_value(user) == self.sanitization(user_flag):
            return True
        else:
            return False


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

    def flag_value(self, user: User) -> str:
        flag_part = "{" + self.dynamic_flag_base + "}" + f"{user.user_id}"
        hash = hmac.digest(settings.FLAG_SIGN_KEY.encode(), flag_part.encode(), "sha256")
        return self.flag_base + "{" + self.dynamic_flag_base + "_" + binascii.hexlify(hash).decode()[0:14] + "}"
