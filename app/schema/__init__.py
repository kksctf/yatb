from __future__ import annotations

import functools
import logging
import pprint
from typing import TYPE_CHECKING, Dict, Set, Type, Union

from pydantic import BaseModel, Extra, validator

if TYPE_CHECKING:
    from pydantic.typing import AbstractSetIntStr, MappingIntStrAny

try:
    from typing_extensions import Literal
except ModuleNotFoundError:
    from typing import Literal

from .. import config

logger = logging.getLogger("yatb.schema")

FilterDictType = Dict[str, object]
FilterFieldsType = Union[Set[str], FilterDictType]


class EBaseModel(BaseModel):
    __public_fields__: FilterFieldsType = set()
    __admin_only_fields__: FilterFieldsType = set()
    __private_fields__: FilterFieldsType = set()

    def do_args(self, args, kwargs):
        if len(self.__public_fields__) == 0 and len(self.__admin_only_fields__) == 0:
            return
        _admin_mode = False

        print(self.__private_fields__, self.__public_fields__, self.__admin_only_fields__)
        print(self)
        print(args, kwargs)

        if "include" not in kwargs:
            kwargs["include"] = set()
        if "exclude" not in kwargs:
            kwargs["exclude"] = set()
        if "admin_mode" in kwargs:
            _admin_mode = kwargs["admin_mode"]
        kwargs["exclude"].update(self.get_exclude_fields())
        kwargs["include"].update(self.get_include_fieds(_admin_mode))

        print(self)
        print(_admin_mode, args, kwargs)

    # TODO: this is a VEEERY strange solution with in and out fields.... but i have no fucking idea about anything else
    @staticmethod
    def recursive_load(in_fields: dict, out_fields: dict, *args, **kwargs):
        for key, val in in_fields.items():  # iterate over fields list
            if val != ... and issubclass(val, EBaseModel):  # if we found subclass
                ev: FilterFieldsType = dict()  # set()  # prepare extendig set/dict
                for subclass in [val] + val.__subclasses__():  # build in/ex fields for subclasses...
                    tmp = subclass.get_include_fieds(*args, **kwargs)
                    if isinstance(tmp, dict):  # append them to resulting dict
                        ev.update(tmp)
                    elif isinstance(tmp, set):  # append them to resulting dict (with convertion)
                        ev |= {i: ... for i in tmp}
                out_fields[key] = ev
            else:
                out_fields[key] = val

    @classmethod
    # @functools.lru_cache(maxsize=1024, typed=True)
    def get_include_fieds(cls, admin=False):
        # resolve fields, that we need to include
        if isinstance(cls.__public_fields__, dict) and isinstance(cls.__admin_only_fields__, dict):
            # in case of public and admin fields are dicts - we need to do some complex shit.
            ret_dict = {}
            EBaseModel.recursive_load(cls.__public_fields__, ret_dict, admin=admin)
            if admin:
                EBaseModel.recursive_load(cls.__admin_only_fields__, ret_dict, admin=admin)
            logger.debug(f"Include Fields Dict for {cls} and {admin}={ret_dict}")
            return ret_dict
        elif isinstance(cls.__public_fields__, set) and isinstance(cls.__admin_only_fields__, set):
            # in case of public and admin fields are set - just join them.
            ret = cls.__public_fields__ | (cls.__admin_only_fields__ if admin else set())
            return ret
        else:
            print(
                cls,
                cls.__public_fields__,
                cls.__admin_only_fields__,
                type(cls.__public_fields__),
                type(cls.__admin_only_fields__),
            )
            raise Exception("WTF why public fields and admin only fields have different types?!")

    @classmethod
    def get_exclude_fields(cls):
        return cls.__private_fields__

    # Workaround for serializing properties with pydantic until
    # https://github.com/samuelcolvin/pydantic/issues/935#issuecomment-641175527 is solved
    @classmethod
    @functools.lru_cache()
    def get_properties(cls):
        return [
            prop
            for prop in dir(cls)
            if isinstance(getattr(cls, prop), property) and prop not in ("__values__", "fields")
        ]

    def dict(
        self,
        *args,
        include: Union["AbstractSetIntStr", "MappingIntStrAny"] = None,  # type: ignore # idk why this not optional
        exclude: Union["AbstractSetIntStr", "MappingIntStrAny"] = None,  # type: ignore # idk why this not optional
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ):  # -> 'DictStrAny':
        # self.do_args(args, kwargs)
        # logger.debug(f"Export:\n\t({self.__class__})\t{self}\n\tWITH KWARGS\n\t{d}")
        attribs = super().dict(
            *args,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
        props = self.get_properties()
        # Include and exclude properties
        if include:
            props = [prop for prop in props if prop in include]
        if exclude:
            props = [prop for prop in props if prop not in exclude]
        if props:
            attribs.update({prop: getattr(self, prop) for prop in props})
        return attribs


from .user import User  # noqa
from .scoring import DynamicKKSScoring, Scoring, StaticScoring  # noqa
from .flags import DynamicKKSFlag, Flag, StaticFlag, RegexFlag  # noqa
from .task import Task, TaskForm  # noqa
from .auth import AuthBase, CTFTimeOAuth, OAuth, SimpleAuth, TelegramAuth  # noqa


class FlagForm(EBaseModel):
    flag: str


for i in [Task, User]:
    logger.debug(f"Schema of {i} is {pprint.pformat(i.schema())}")
