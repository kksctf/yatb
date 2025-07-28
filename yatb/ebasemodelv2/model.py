import dataclasses
import sys
import typing
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Concatenate,
    ParamSpec,
    Self,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    overload,
    reveal_type,
)

from beanie import Document
from pydantic import BaseModel as RawBaseModel
from pydantic import Field as RawField
from pydantic import computed_field as raw_computed_field
from pydantic import create_model
from pydantic.fields import ComputedFieldInfo, FieldInfo
from typing_inspection.introspection import AnnotationSource, InspectedAnnotation, _unpack_annotated, inspect_annotation

from ..utils.log_helper import get_logger
from .level import PresentationLevel

logger = get_logger("schema.v2")


def origin_is_union(tp: type[Any] | None) -> bool:
    return tp is typing.Union or tp is UnionType


MODELS_CACHE: dict[tuple, type[RawBaseModel]] = {}  # pyright: ignore[reportGeneralTypeIssues]


class EBaseModelV2(RawBaseModel):
    # Использование Self тут палка о двух концах.
    _model_public: ClassVar[type[Self]]
    _model_admin: ClassVar[type[Self]]

    public_model: ClassVar[type[Self]]
    admin_model: ClassVar[type[Self]]

    @classmethod
    def __extract_level(cls, field_info: FieldInfo | InspectedAnnotation) -> PresentationLevel | None:
        # reversed, чтобы доставать "типа переопределенные" уровни
        for metadata in reversed(field_info.metadata):
            if isinstance(metadata, PresentationLevel):
                return metadata
        return None

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs) -> None:  # noqa: ANN003
        super().__pydantic_init_subclass__(**kwargs)

        try:
            cls._model_public = cls._create_leveled_model(PresentationLevel.public)
            cls._model_admin = cls._create_leveled_model(PresentationLevel.admin)

            cls.public_model = cls._model_public
            cls.admin_model = cls._model_admin
        except Exception:
            logger.exception(f"{cls = }")
            raise

    @classmethod
    @overload
    def __resolve_field_info(
        cls,
        level: PresentationLevel,
        field_name: str,
        field: FieldInfo,
    ) -> tuple[type, FieldInfo] | None: ...

    @classmethod
    @overload
    def __resolve_field_info(
        cls,
        level: PresentationLevel,
        field_name: str,
        field: ComputedFieldInfo,
    ) -> tuple[type, ComputedFieldInfo] | None: ...

    @classmethod
    def __resolve_field_info(  # noqa: C901, PLR0912
        cls,
        level: PresentationLevel,
        field_name: str,
        field: FieldInfo | ComputedFieldInfo,
    ) -> tuple[type, FieldInfo | ComputedFieldInfo] | None:
        # WTF: hacky skip beanie-mongo internal fields
        if issubclass(cls, Document) and field_name in ["id", "revision_id"]:
            return None

        annotation: type | None
        field_level: PresentationLevel | None = None

        if isinstance(field, FieldInfo):
            annotation = field.annotation
        elif isinstance(field, ComputedFieldInfo):
            annotation = field.return_type
        else:
            raise TypeError

        if not annotation:
            logger.error(f"WTF broken field {cls.__qualname__}: {field_name}, {field = }")
            return None

        inspected: InspectedAnnotation = inspect_annotation(
            annotation,
            annotation_source=AnnotationSource.ANY,
            unpack_type_aliases="eager",
        )

        annotation = inspected.type  # pyright: ignore[reportAssignmentType]
        if not annotation or inspected.metadata is None:
            logger.error(f"{cls = }, {field_name = }, {annotation = }, {inspected = }, wtf")
            return None

        # Если в пидантиковой структуре есть мета - достанем из неё
        if isinstance(field, FieldInfo):
            field_level = cls.__extract_level(field)

        # если не нашлось, или это у нас ComputedFieldInfo - достанем напрямую из Annotated
        if not field_level:
            field_level = cls.__extract_level(inspected)

        if not field_level:
            logger.error(f"{cls = }, {field_name = }, {field = }, {field_level = } is not PresLevel. Skipped!")
            return None

        if not field_level.is_visible(level):
            return None

        if origin_is_union(get_origin(annotation)):
            new_union_base: list[Any] = []
            for union_member in get_args(annotation):
                if issubclass(union_member, EBaseModelV2):
                    new_union_base.append(union_member._create_leveled_model(level))  # noqa: SLF001
                else:
                    new_union_base.append(union_member)

            new_union = Union[tuple(new_union_base)]  # noqa: UP007 # так надо
            annotation = cast("type", new_union)  # this shit is shit. Shitty solution

        elif isinstance(annotation, type) and issubclass(annotation, EBaseModelV2):
            annotation = annotation._create_leveled_model(level)  # noqa: SLF001

        if isinstance(field, FieldInfo):
            field = FieldInfo.merge_field_infos(field, FieldInfo(annotation=annotation))
        elif isinstance(field, ComputedFieldInfo):
            field = dataclasses.replace(field, return_type=annotation)
        else:
            raise TypeError

        return (
            annotation,
            field,
        )

    @classmethod
    def _create_leveled_model(cls, level: PresentationLevel) -> type[Self]:
        cache_key = (cls.__module__, cls.__qualname__, level)

        if model := MODELS_CACHE.get(cache_key):
            return model  # pyright: ignore[reportReturnType] # well.....

        new_fields: dict[str, tuple[type, FieldInfo]] = {}
        new_computed_fields: dict[str, ComputedFieldInfo] = {}

        for field_name, field in cls.model_fields.items():
            resolved = cls.__resolve_field_info(level, field_name, field)
            if not resolved:
                continue

            new_fields[field_name] = resolved

        for field_name, field in cls.model_computed_fields.items():
            resolved = cls.__resolve_field_info(level, field_name, field)
            if not resolved:
                continue

            new_computed_fields[field_name] = resolved[1]

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
        ret.__pydantic_computed_fields__ = new_computed_fields
        ret.__pydantic_decorators__ = cls.__pydantic_decorators__

        for computed_field_name in new_computed_fields:
            setattr(ret, computed_field_name, getattr(cls, computed_field_name))

        MODELS_CACHE[cache_key] = ret
        return ret  # pyright: ignore[reportReturnType] # well.....
