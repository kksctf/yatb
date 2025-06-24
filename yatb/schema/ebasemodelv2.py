import functools
import typing
from collections.abc import Callable
from enum import Enum, auto
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Concatenate,
    Literal,
    ParamSpec,
    Self,
    TypeAlias,
    TypeVar,
    Union,
    Unpack,
    get_args,
    get_origin,
    overload,
    reveal_type,
)
from warnings import warn

import annotated_types
import typing_extensions
from pydantic import AliasChoices, AliasPath, computed_field, create_model, types
from pydantic import BaseModel as RawBaseModel
from pydantic import Field as RawField
from pydantic.config import JsonDict
from pydantic.fields import _T, Deprecated, _EmptyKwargs, _Unset
from pydantic.fields import FieldInfo as RawFieldInfo
from pydantic.fields import _FieldInfoInputs as _RawFieldInfoInputs
from pydantic.json_schema import PydanticJsonSchemaWarning
from pydantic_core import PydanticUndefined

from ..utils.log_helper import get_logger

logger = get_logger("schema.v2")


def origin_is_union(tp: type[Any] | None) -> bool:
    return tp is typing.Union or tp is UnionType


class PresentationLevel(Enum):
    all = auto()
    admin = auto()
    private = auto()

    def is_visible(self, target: Self) -> bool:
        if self == self.all:
            return True

        if self == self.admin and target in (self.admin, self.private):
            return True

        if self == self.private:
            return False

        return False


class _FieldInfoInputs(_RawFieldInfoInputs, total=False):
    """This class exists solely to add type checking for the `**kwargs` in `FieldInfo.from_field`."""

    level: PresentationLevel


class FieldInfo(RawFieldInfo):
    level: PresentationLevel

    __slots__ = ("level",)

    def __init__(self, **kwargs: Unpack[_FieldInfoInputs]) -> None:
        super().__init__(**kwargs)
        self.level = kwargs.pop("level")

    @staticmethod
    def merge_field_infos(*field_infos: RawFieldInfo, **overrides: Any) -> "FieldInfo":  # noqa: ANN401, C901, PLR0912
        """
        Merge `FieldInfo` instances keeping only explicitly set attributes.

        Later `FieldInfo` instances override earlier ones.

        Returns:
            FieldInfo: A merged FieldInfo instance.

        """
        # if len(field_infos) == 1:
        #     # No merging necessary, but we still need to make a copy and apply the overrides
        #     field_info = field_infos[0]._copy()
        #     field_info._attributes_set.update(overrides)

        #     default_override = overrides.pop("default", PydanticUndefined)
        #     if default_override is Ellipsis:
        #         default_override = PydanticUndefined
        #     if default_override is not PydanticUndefined:
        #         field_info.default = default_override

        #     for k, v in overrides.items():
        #         setattr(field_info, k, v)
        #     return field_info  # type: ignore

        merged_field_info_kwargs: dict[str, Any] = {}
        metadata = {}
        for field_info in field_infos:
            attributes_set = field_info._attributes_set.copy()

            try:
                json_schema_extra = attributes_set.pop("json_schema_extra")
                existing_json_schema_extra = merged_field_info_kwargs.get("json_schema_extra")

                if existing_json_schema_extra is None:
                    merged_field_info_kwargs["json_schema_extra"] = json_schema_extra
                if isinstance(existing_json_schema_extra, dict):
                    if isinstance(json_schema_extra, dict):
                        merged_field_info_kwargs["json_schema_extra"] = {
                            **existing_json_schema_extra,
                            **json_schema_extra,
                        }
                    if callable(json_schema_extra):
                        warn(
                            "Composing `dict` and `callable` type `json_schema_extra` is not supported."
                            "The `callable` type is being ignored."
                            "If you'd like support for this behavior, please open an issue on pydantic.",
                            PydanticJsonSchemaWarning,
                        )
                elif callable(json_schema_extra):
                    # if ever there's a case of a callable, we'll just keep the last json schema extra spec
                    merged_field_info_kwargs["json_schema_extra"] = json_schema_extra
            except KeyError:
                pass

            # later FieldInfo instances override everything except json_schema_extra from earlier FieldInfo instances
            merged_field_info_kwargs.update(attributes_set)

            for x in field_info.metadata:
                if not isinstance(x, FieldInfo):
                    metadata[type(x)] = x

        merged_field_info_kwargs.update(overrides)
        field_info = FieldInfo(**merged_field_info_kwargs)
        field_info.metadata = list(metadata.values())
        return field_info


# NOTE: Actual return type is 'FieldInfo', but we want to help type checkers
# to understand the magic that happens at runtime with the following overloads:
@overload  # type hint the return value as `Any` to avoid type checking regressions when using `...`.
def Field(
    default: "ellipsis",  # noqa: F821  # TODO: use `_typing_extra.EllipsisType` when we drop Py3.9
    *,
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[Any] | None = _Unset,
    exclude: bool | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: bool | None = _Unset,
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | typing.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: Literal["smart", "left_to_right"] = _Unset,
    fail_fast: bool | None = _Unset,
    level: PresentationLevel = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> Any: ...
@overload  # `default` argument set
def Field(
    default: _T,
    *,
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[Any] | None = _Unset,
    exclude: bool | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: bool | None = _Unset,
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | typing.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: Literal["smart", "left_to_right"] = _Unset,
    fail_fast: bool | None = _Unset,
    level: PresentationLevel = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> _T: ...
@overload  # `default_factory` argument set
def Field(
    *,
    default_factory: Callable[[], _T] | Callable[[dict[str, Any]], _T],
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[Any] | None = _Unset,
    exclude: bool | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: bool | None = _Unset,
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | typing.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: Literal["smart", "left_to_right"] = _Unset,
    fail_fast: bool | None = _Unset,
    level: PresentationLevel = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> _T: ...
@overload
def Field(  # No default set
    *,
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[Any] | None = _Unset,
    exclude: bool | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: bool | None = _Unset,
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | typing.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: Literal["smart", "left_to_right"] = _Unset,
    fail_fast: bool | None = _Unset,
    level: PresentationLevel = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> Any: ...
def Field(  # noqa: C901
    default: Any = PydanticUndefined,
    *,
    level: PresentationLevel = _Unset,
    **kwargs,
) -> Any:
    field_info: RawFieldInfo = FieldInfo.merge_field_infos(
        RawField(**kwargs),
        level=level,
    )
    return field_info


MODELS_CACHE: dict[tuple, type[RawBaseModel]] = {}  # pyright: ignore[reportGeneralTypeIssues]


class EBaseModelV2(RawBaseModel):
    _model_all: type[RawBaseModel]
    _model_admin: type[RawBaseModel]

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        cls._model_all = cls.build_model(PresentationLevel.all)
        cls._model_admin = cls.build_model(PresentationLevel.admin)

    @classmethod
    def build_model(cls, level: PresentationLevel) -> type[RawBaseModel]:
        cache_key = (cls.__module__, cls.__qualname__, level)

        if model := MODELS_CACHE.get(cache_key):
            return model

        new_fields: dict[str, tuple[type, RawFieldInfo]] = {}

        for field_name, field in cls.model_fields.items():
            if not isinstance(field, FieldInfo):
                logger.warning(f"{cls = }, {field_name = }, {field = } is not patched FieldInfo. Skipped!")
                continue

            if (annotation := field.annotation) is None:
                logger.error(f"WTF broken field {cls.__qualname__}: {field_name}, {field = }")
                continue

            if not field.level.is_visible(level):
                continue

            if origin_is_union(get_origin(annotation)):
                new_union_base: list[Any] = []
                for union_member in get_args(annotation):
                    if issubclass(union_member, EBaseModelV2):
                        new_union_base.append(union_member.build_model(level))
                    else:
                        new_union_base.append(union_member)

                new_union = Union[tuple(new_union_base)]  # noqa: UP007 # так надо

                new_fields[field_name] = (  # type: ignore # ;(
                    new_union,
                    FieldInfo.merge_field_infos(
                        field,
                        RawFieldInfo(
                            annotation=new_union,  # type: ignore # ;(
                        ),
                    ),
                )
            elif isinstance(annotation, type) and issubclass(annotation, EBaseModelV2):
                new_field_cls = annotation.build_model(level)
                new_fields[field_name] = (
                    new_field_cls,
                    FieldInfo.merge_field_infos(
                        field,
                        RawFieldInfo(
                            annotation=new_field_cls,
                            # level=level,
                        ),
                    ),
                )
            else:
                new_fields[field_name] = (
                    annotation,
                    field,
                )

        ret = create_model(
            f"{cls.__qualname__}__l_{level.name}",
            __doc__=cls.__doc__,
            __base__=None,
            __config__=cls.model_config,
            __module__=f"{cls.__module__}.dynamic",
            # __validators__=cls.__pydantic_decorators__,
            __validators__={},
            __cls_kwargs__=None,
            **new_fields,
        )
        ret.__pydantic_decorators__ = cls.__pydantic_decorators__

        MODELS_CACHE[cache_key] = ret
        return ret
