from __future__ import annotations

import functools
import logging
import types
import typing
from typing import TYPE_CHECKING, Any, ClassVar, Self, TypeAlias, Union, get_args, get_origin

from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

if TYPE_CHECKING:
    from pydantic.typing import AbstractSetIntStr, MappingIntStrAny

from ..utils.log_helper import get_logger

logger = get_logger("schema")

FilterFieldsType: TypeAlias = set[str] | dict[str, object]


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
    return tp is typing.Union or tp is types.UnionType


class EBaseModel(BaseModel):
    __public_fields__: ClassVar[FilterFieldsType] = set()
    __admin_only_fields__: ClassVar[FilterFieldsType] = set()
    __private_fields__: ClassVar[FilterFieldsType] = set()

    @classmethod
    def build_model(
        cls: type[Self],
        include: FilterFieldsType,
        exclude: FilterFieldsType,
        name: str = "sub",
        public: bool = True,
    ) -> type[BaseModel]:
        target_fields: dict[str, tuple[type, FieldInfo]] = {}
        for field_name, field_value in cls.__fields__.items():
            if field_name in exclude:
                continue
            elif field_name in include:
                if origin_is_union(get_origin(field_value.annotation)):
                    logger.debug(f"Found union field at {cls.__qualname__}: {field_name}")
                    new_union_base: list[Any] = []
                    for union_member in get_args(field_value.annotation):
                        if issubclass(union_member, EBaseModel):
                            new_member = union_member.public_model() if public else union_member.admin_model()
                            new_union_base.append(new_member)
                        else:
                            new_union_base.append(union_member)

                    new_union = Union[tuple(new_union_base)]  # type: ignore  # noqa: UP007, PGH003 # так надо.

                    target_fields[field_name] = (
                        new_union,
                        field_value.field_info,
                    )
                elif isinstance(field_value.annotation, type) and issubclass(field_value.annotation, EBaseModel):
                    logger.debug(f"Found EBaseModel field at {cls.__qualname__}: {field_name}")
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
            if attr_name in exclude:
                continue
            elif attr_name in include:
                logger.debug(f"Found property in {cls}: {attr_name}")
                target_fields[attr_name] = (
                    attr_value.fget.__annotations__["return"],
                    FieldInfo(),
                )
            else:
                logger.info(f"Unlisted property at {cls.__qualname__}: {attr_name}")

        return create_model(
            f"{cls.__qualname__}_{name}",
            __config__=cls.Config,
            __module__=f"{cls.__module__}.dynamic",
            # __validators__=cls.__validators__,  # type: ignore
            **target_fields,  # type: ignore
        )

    @classmethod
    @functools.lru_cache(typed=True)
    def public_model(cls: type[Self]) -> type[BaseModel]:
        return cls.build_model(
            cls.__public_fields__,
            cls.join_fields(cls.__private_fields__, cls.__admin_only_fields__),
            name="public",
            public=True,
        )

    @classmethod
    @functools.lru_cache(typed=True)
    def admin_model(cls: type[Self]) -> type[BaseModel]:
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
        include: AbstractSetIntStr | MappingIntStrAny | None = None,
        exclude: AbstractSetIntStr | MappingIntStrAny | None = None,
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
