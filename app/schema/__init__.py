from __future__ import annotations

import functools
import logging
import pprint
from typing import TYPE_CHECKING, Any, Dict, Set, Type, Union, get_args, get_origin
from typing import Literal
import typing
import types

from pydantic import BaseModel, Extra, validator, create_model
from pydantic.fields import FieldInfo, ModelField

# if TYPE_CHECKING:
#     from pydantic.typing import AbstractSetIntStr, MappingIntStrAny


from .. import config

logger = logging.getLogger("yatb.schema")

FilterFieldsType = Union[Set[str], Dict[str, object]]


# def lenient_issubclass(cls: Any, class_or_tuple: Any) -> bool:
#     try:
#         return isinstance(cls, type) and issubclass(cls, class_or_tuple)
#     except TypeError:
#         if isinstance(
#             cls,
#             typing._GenericAlias,  # type: ignore[attr-defined] # noqa: W0212
#             types.GenericAlias,  # type: ignore[attr-defined]
#             types.UnionType,
#         ):
#             return False
#         raise  # pragma: no cover


def origin_is_union(tp: type[Any] | None) -> bool:
    return tp is typing.Union or tp is types.UnionType  # noqa: E721


class EBaseModel(BaseModel):
    __public_fields__: FilterFieldsType = set()
    __admin_only_fields__: FilterFieldsType = set()
    __private_fields__: FilterFieldsType = set()

    @classmethod
    def build_model(
        cls: Type["EBaseModel"],
        include: FilterFieldsType,
        exclude: FilterFieldsType,
        name: str = "sub",
        public: bool = True,
    ) -> Type["BaseModel"]:
        target_fields: Dict[str, tuple[Type, FieldInfo]] = {}
        for field_name, field_value in cls.__fields__.items():
            if field_name in exclude:
                continue
            elif field_name in include:
                if origin_is_union(get_origin(field_value.annotation)):
                    logger.info(f"Found union field at {cls.__qualname__}: {field_name}")
                    new_union_base: list[Any] = []
                    for union_member in get_args(field_value.annotation):
                        if issubclass(union_member, EBaseModel):
                            new_member = union_member.public_model() if public else union_member.admin_model()
                            new_union_base.append(new_member)
                        else:
                            new_union_base.append(union_member)

                    new_union = Union[tuple(new_union_base)]  # type: ignore

                    target_fields[field_name] = (
                        new_union,
                        field_value.field_info,
                    )
                elif isinstance(field_value.annotation, type) and issubclass(field_value.annotation, EBaseModel):
                    logger.info(f"Found EBaseModel field at {cls.__qualname__}: {field_name}")
                    new_field_cls = (
                        field_value.annotation.public_model() if public else field_value.annotation.admin_model()
                    )
                    target_fields[field_name] = (
                        new_field_cls,
                        field_value.field_info,
                    )
                else:
                    target_fields[field_name] = (
                        field_value.annotation,
                        field_value.field_info,
                    )
            else:
                logger.info(f"Unlisted field at {cls.__qualname__}: {field_name}, {field_value = }")

        for attr_name, attr_value in cls.__dict__.items():
            if not isinstance(attr_value, property):
                continue

            logger.info(f"Found property in {cls}: {attr_name}")
            target_fields[attr_name] = (
                attr_value.fget.__annotations__["return"],
                FieldInfo(),
            )

        return create_model(
            f"{cls.__qualname__}_{name}",
            __config__=cls.Config,
            __module__=f"{cls.__module__}.dynamic",
            # __validators__=cls.__validators__,  # type: ignore
            **target_fields,
        )

    @classmethod
    @functools.lru_cache(typed=True)
    def public_model(cls: Type["EBaseModel"]) -> Type["BaseModel"]:
        return cls.build_model(
            cls.__public_fields__,
            cls.join_fields(cls.__private_fields__, cls.__admin_only_fields__),
            name="public",
            public=True,
        )

    @classmethod
    @functools.lru_cache(typed=True)
    def admin_model(cls: Type["EBaseModel"]) -> Type["BaseModel"]:
        return cls.build_model(
            cls.join_fields(cls.__public_fields__, cls.__admin_only_fields__),
            cls.__private_fields__,
            name="private",
            public=False,
        )

    @staticmethod
    def join_fields(f1: FilterFieldsType, f2: FilterFieldsType) -> FilterFieldsType:
        ret = set()
        if isinstance(f1, dict) or isinstance(f2, dict):
            ret = {}
            # ret |= ({i: ... for i in f1}  else f1)
            if isinstance(f1, set):
                ret |= {i: ... for i in f1}
            else:
                ret |= f1

            if isinstance(f2, set):
                ret |= {i: ... for i in f2}
            else:
                ret |= f2
        else:
            ret = f1 | f2
        return ret

    # def do_args(self, args, kwargs):
    #     if len(self.__public_fields__) == 0 and len(self.__admin_only_fields__) == 0:
    #         return
    #     _admin_mode = False

    #     print(self.__private_fields__, self.__public_fields__, self.__admin_only_fields__)
    #     print(self)
    #     print(args, kwargs)

    #     if "include" not in kwargs:
    #         kwargs["include"] = set()
    #     if "exclude" not in kwargs:
    #         kwargs["exclude"] = set()
    #     if "admin_mode" in kwargs:
    #         _admin_mode = kwargs["admin_mode"]
    #     kwargs["exclude"].update(self.get_exclude_fields())
    #     kwargs["include"].update(self.get_include_fieds(_admin_mode))

    #     print(self)
    #     print(_admin_mode, args, kwargs)

    # # TODO: this is a VEEERY strange solution with in and out fields... but i have no fucking idea about anything else
    # @staticmethod
    # def recursive_load(in_fields: dict, out_fields: dict, *args, **kwargs):
    #     for key, val in in_fields.items():  # iterate over fields list
    #         if val != ... and issubclass(val, EBaseModel):  # if we found subclass
    #             ev: FilterFieldsType = dict()  # set()  # prepare extendig set/dict
    #             for subclass in [val] + val.__subclasses__():  # build in/ex fields for subclasses...
    #                 tmp = subclass.get_include_fieds(*args, **kwargs)
    #                 if isinstance(tmp, dict):  # append them to resulting dict
    #                     ev.update(tmp)
    #                 elif isinstance(tmp, set):  # append them to resulting dict (with convertion)
    #                     ev |= {i: ... for i in tmp}
    #             out_fields[key] = ev
    #         else:
    #             out_fields[key] = val

    # @classmethod
    # # @functools.lru_cache(maxsize=1024, typed=True)
    # def get_include_fieds(cls, admin=False):
    #     # resolve fields, that we need to include
    #     if isinstance(cls.__public_fields__, dict) and isinstance(cls.__admin_only_fields__, dict):
    #         # in case of public and admin fields are dicts - we need to do some complex shit.
    #         ret_dict = {}
    #         EBaseModel.recursive_load(cls.__public_fields__, ret_dict, admin=admin)
    #         if admin:
    #             EBaseModel.recursive_load(cls.__admin_only_fields__, ret_dict, admin=admin)
    #         logger.debug(f"Include Fields Dict for {cls} and {admin}={ret_dict}")
    #         return ret_dict
    #     elif isinstance(cls.__public_fields__, set) and isinstance(cls.__admin_only_fields__, set):
    #         # in case of public and admin fields are set - just join them.
    #         ret = cls.__public_fields__ | (cls.__admin_only_fields__ if admin else set())
    #         return ret
    #     else:
    #         print(
    #             cls,
    #             cls.__public_fields__,
    #             cls.__admin_only_fields__,
    #             type(cls.__public_fields__),
    #             type(cls.__admin_only_fields__),
    #         )
    #         raise Exception("WTF why public fields and admin only fields have different types?!")

    # @classmethod
    # def get_exclude_fields(cls):
    #     return cls.__private_fields__

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
from .flags import DynamicKKSFlag, Flag, StaticFlag  # noqa
from .task import Task, TaskForm  # noqa
from .auth import AuthBase, CTFTimeOAuth, OAuth, SimpleAuth, TelegramAuth  # noqa


class FlagForm(EBaseModel):
    flag: str


# for i in [Task, User]:
#     logger.debug(f"Schema of {i} is {pprint.pformat(i.schema())}")
