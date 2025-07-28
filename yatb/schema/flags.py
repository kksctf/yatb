import binascii
import hmac
from typing import Literal

from ..config import settings
from ..ebasemodelv2 import Admin, EBaseModelV2, Public
from .user import User


class Flag(EBaseModelV2):
    classtype: Public[Literal["Flag"]] = "Flag"

    flag_base: Admin[str] = settings.FLAG_BASE

    def sanitization(self, user_flag: str) -> str:
        if self.flag_base + "{" in user_flag:
            user_flag = user_flag.replace(self.flag_base + "{", "", 1)
        if user_flag[-1] == "}":
            user_flag = user_flag[:-1]
        user_flag = self.flag_base + "{" + user_flag + "}"

        return user_flag  # noqa: RET504

    def flag_value(self, user: User) -> str:
        return self.flag_base + "{test_flag}"

    def flag_checker(self, user_flag: str, user: User) -> bool:
        if self.flag_value(user) == self.sanitization(user_flag):  # noqa: SIM103
            return True
        return False


class StaticFlag(Flag):
    classtype: Public[Literal["StaticFlag"]] = "StaticFlag"

    flag: Admin[str]

    def flag_value(self, user: User) -> str:
        return self.flag_base + "{" + self.flag + "}"


class DynamicKKSFlag(Flag):
    classtype: Public[Literal["DynamicKKSFlag"]] = "DynamicKKSFlag"

    dynamic_flag_base: Admin[str]

    def flag_value(self, user: User) -> str:
        flag_part = "{" + self.dynamic_flag_base + "}" + f"{user.user_id}"
        hash = hmac.digest(settings.FLAG_SIGN_KEY.encode(), flag_part.encode(), "sha256")
        return self.flag_base + "{" + self.dynamic_flag_base + "_" + binascii.hexlify(hash).decode()[0:14] + "}"
