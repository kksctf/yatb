import functools
import types
import typing
from typing import TYPE_CHECKING, Any, ClassVar, Self, TypeAlias, Union, get_args, get_origin

from pydantic import BaseModel, computed_field, create_model
from pydantic.fields import FieldInfo

from ..utils.log_helper import get_logger

if TYPE_CHECKING:
    from pydantic.main import IncEx

logger = get_logger("schema")

FilterFieldsType: TypeAlias = set[str]  #  | dict[str, object]


def origin_is_union(tp: type[Any] | None) -> bool:
    return tp is typing.Union or tp is types.UnionType


class EBaseModel(BaseModel):
    __public_fields__: ClassVar[FilterFieldsType] = set()
    __admin_only_fields__: ClassVar[FilterFieldsType] = set()
    __private_fields__: ClassVar[FilterFieldsType] = set()

    @classmethod
    def build_model(  # noqa: PLR0912, C901 # WTF: refactor & simplify
        cls: type[Self],
        include: FilterFieldsType,
        exclude: FilterFieldsType,
        name: str = "sub",
        *,
        public: bool = True,
    ) -> type[Self]:
        target_fields: dict[str, tuple[type, FieldInfo]] = {}

        for field_name, field_value in cls.model_fields.items():
            if field_name in exclude:
                continue

            if field_name not in include:
                logger.error(f"Unlisted field at {cls.__qualname__}: {field_name}, {field_value = }")
                continue

            if field_value.annotation is None:
                logger.error(f"WTF Field {cls.__qualname__}: {field_name}, {field_value = }")
                continue

            if origin_is_union(get_origin(field_value.annotation)):
                logger.debug(f"Found union field at {cls.__qualname__}: {field_name}")
                new_union_base: list[Any] = []
                for union_member in get_args(field_value.annotation):
                    if issubclass(union_member, EBaseModel):
                        new_member = (  # WTF: make it more robust
                            union_member.public_model() if public else union_member.admin_model()
                        )
                        new_union_base.append(new_member)
                    else:
                        new_union_base.append(union_member)

                new_union = Union[tuple(new_union_base)]  # type: ignore  # noqa: UP007, PGH003 # так надо.

                target_fields[field_name] = (
                    new_union,
                    field_value,
                )
            elif isinstance(field_value.annotation, type) and issubclass(field_value.annotation, EBaseModel):
                logger.debug(f"Found EBaseModel field at {cls.__qualname__}: {field_name}")
                new_field_cls = (
                    field_value.annotation.public_model() if public else field_value.annotation.admin_model()
                )
                target_fields[field_name] = (
                    new_field_cls,
                    field_value,
                )
            else:
                target_fields[field_name] = (
                    field_value.annotation,
                    field_value,
                )

        for attr_name, attr_value in cls.__dict__.items():
            if not isinstance(attr_value, property):
                continue
            if attr_name in exclude:
                continue
            if attr_name not in include:
                logger.error(f"Unlisted property at {cls.__qualname__}: {attr_name}")
                continue

            logger.debug(f"Found property in {cls}: {attr_name}")

            annotation = attr_value.fget.__annotations__["return"]
            target_fields[attr_name] = (
                annotation,
                FieldInfo.from_annotation(annotation),
            )

        ret = create_model(
            f"{cls.__qualname__}_{name}",
            __config__=cls.model_config,
            __module__=f"{cls.__module__}.dynamic",
            # __validators__=cls.__pydantic_decorators__,  # type: ignore # WTF: why commented
            **target_fields,  # type: ignore
        )
        ret.__pydantic_decorators__ = cls.__pydantic_decorators__

        return ret

    @classmethod
    @functools.lru_cache(typed=True)
    def public_model(cls: type[Self]) -> type[Self]:
        return cls.build_model(
            cls.__public_fields__,
            cls.join_fields(cls.__private_fields__, cls.__admin_only_fields__),
            name="public",
            public=True,
        )

    @classmethod
    @functools.lru_cache(typed=True)
    def admin_model(cls: type[Self]) -> type[Self]:
        return cls.build_model(
            cls.join_fields(cls.__public_fields__, cls.__admin_only_fields__),
            cls.__private_fields__,
            name="private",
            public=False,
        )

    @staticmethod
    def join_fields(f1: FilterFieldsType, f2: FilterFieldsType) -> FilterFieldsType:
        ret = set()
        # if isinstance(f1, dict) or isinstance(f2, dict):
        #     ret = {}
        #     # ret |= ({i: ... for i in f1}  else f1)
        #     if isinstance(f1, set):
        #         ret |= {i: ... for i in f1}
        #     else:
        #         ret |= f1

        #     if isinstance(f2, set):
        #         ret |= {i: ... for i in f2}
        #     else:
        #         ret |= f2
        # else:
        ret = f1 | f2

        return ret
