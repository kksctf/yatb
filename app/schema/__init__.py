from __future__ import annotations
from pydantic import BaseModel, validator, Extra

import pprint
import functools
import logging

try:
    from typing_extensions import Literal
except ModuleNotFoundError:
    from typing import Literal

from .. import config
from ..utils import md
logger = logging.getLogger("yatb.schema")


class EBaseModel(BaseModel):
    __public_fields__ = set()
    __admin_only_fields__ = set()
    __private_fields__ = set()

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
        for key, val in in_fields.items():
            if val != ... and issubclass(val, EBaseModel):
                ev = set()
                for subclass in [val] + val.__subclasses__():
                    tmp = subclass.get_include_fieds(*args, **kwargs)
                    if isinstance(tmp, dict):
                        ev = {i: ... for i in ev}
                    ev.update(tmp)
                out_fields[key] = ev
            else:
                out_fields[key] = val

    @classmethod
    # @functools.lru_cache(maxsize=1024, typed=True)
    def get_include_fieds(cls, admin=False):
        if (isinstance(cls.__public_fields__, dict) and not isinstance(cls.__admin_only_fields__, dict)) or (not isinstance(cls.__public_fields__, dict) and isinstance(cls.__admin_only_fields__, dict)):
            print(cls, cls.__public_fields__, cls.__admin_only_fields__, type(cls.__public_fields__), type(cls.__admin_only_fields__))
            raise Exception("WTF why public fields and admin only fields have different types?!")

        if isinstance(cls.__public_fields__, dict):
            ret_dict = {}
            EBaseModel.recursive_load(cls.__public_fields__, ret_dict, admin=admin)
            if admin:
                EBaseModel.recursive_load(cls.__admin_only_fields__, ret_dict, admin=admin)
            logger.debug(f"Include Fields Dict for {cls} and {admin}={ret_dict}")
            return ret_dict
        else:
            ret = cls.__public_fields__ | (cls.__admin_only_fields__ if admin else set())
            return ret

    @classmethod
    def get_exclude_fields(cls):
        return cls.__private_fields__

    # Workaround for serializing properties with pydantic until https://github.com/samuelcolvin/pydantic/issues/935#issuecomment-641175527 is solved
    @classmethod
    @functools.lru_cache()
    def get_properties(cls):
        return [prop for prop in dir(cls) if isinstance(getattr(cls, prop), property) and prop not in ("__values__", "fields")]

    def dict(
        self,
        *args,
        include=None,  # : Union['AbstractSetIntStr', 'MappingIntStrAny']
        exclude=None,  # : Union['AbstractSetIntStr', 'MappingIntStrAny']
        by_alias: bool = False,
        skip_defaults: bool = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ):  # -> 'DictStrAny':
        # self.do_args(args, kwargs)
        d = {
            'include': include,
            'exclude': exclude,
            'by_alias': by_alias,
            'skip_defaults': skip_defaults,
            'exclude_unset': exclude_unset,
            'exclude_defaults': exclude_defaults,
            'exclude_none': exclude_none
        }
        # logger.debug(f"Export:\n\t({self.__class__})\t{self}\n\tWITH KWARGS\n\t{d}")
        attribs = super().dict(
            *args,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none
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


from .scoring import Scoring, StaticScoring, DynamicKKSScoring  # noqa
from .task import Task, TaskForm  # noqa
from .user import User, UserForm, UserUpdateForm  # noqa


class FlagForm(BaseModel):
    flag: str


for i in [Task, User, UserForm, UserUpdateForm, TaskForm]:
    logger.debug(f"Schema of {i} is {pprint.pformat(i.schema())}")
