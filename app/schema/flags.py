from . import EBaseModel, Literal, logger
from ..config import settings


class Flag(EBaseModel):

    classtype: Literal["Flag"] = "Flag"
    flag_base: str = settings.FLAG_BASE

    def flag_for_all(self):
        pass

    def get_user_flag(self, username: str):
        pass

    @property
    def dynamic_type_checker(self):
        return False

    def sanitization(self, user_flag):

        if self.flag_base + "{" in user_flag:
            user_flag = user_flag.replace(self.flag_base + "{", "", 1)
        if user_flag[-1] == "}":
            user_flag = user_flag[:-1]
        user_flag = self.flag_base + "{" + user_flag + "}"

        return user_flag

    @property
    def flag_value(self) -> str:
        return self.flag_base + "{" + "test_flag" + "}"

    def flag_checker(self, user_flag: str, username: str) -> bool:
        if self.flag_value == self.sanitization(user_flag):
            return True
        else:
            return False


class StaticFlag(Flag):
    __admin_only_fields__ = {"static_flag"}
    classtype: Literal["StaticFlag"] = "StaticFlag"
    flag_base: str = settings.FLAG_BASE
    static_flag: str

    @property
    def flag_value(self) -> str:
        return self.flag_base + "{" + self.static_flag + "}"


class DynamicKKSFlags(Flag):
    __admin_only_fields__ = {"dynamic_flag"}
    classtype: Literal["DynamicKKSFlags"] = "DynamicKKSFlags"
    flag_base: str = settings.FLAG_BASE
    dynamic_flag: str
    flag_dict: dict = {}

    @property
    def dynamic_type_checker(self):
        return True

    def flag_for_all(self, key: str, value: str):
        self.flag_dict[key] = value
        print(value)

    def get_user_flag(self, username: str):
        flag: str
        flag = self.flag_dict[username]
        return flag

    @property
    def flag_value(self) -> str:
        return self.flag_base + "{" + self.dynamic_flag

    def flag_checker(self, user_flag: str, username: str):
        if self.get_user_flag(username) == self.sanitization(user_flag):
            return True
        else:
            return False
