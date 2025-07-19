import functools
import typing
from collections.abc import Callable, Mapping
from dataclasses import dataclass
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
    cast,
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
from typing_inspection.introspection import AnnotationSource, _unpack_annotated, inspect_annotation

from .utils.log_helper import get_logger

logger = get_logger("schema.v2")


def origin_is_union(tp: type[Any] | None) -> bool:
    return tp is typing.Union or tp is UnionType


class PresentationLevel(Enum):
    public = auto()
    admin = auto()
    private = auto()

    def is_visible(self, target: Self) -> bool:
        if self == self.public:
            return True

        if self == self.admin and target in (self.admin, self.private):
            return True

        if self == self.private:
            return False

        return False


# from https://github.com/pydantic/pydantic/discussions/2419#discussioncomment-10551986
# Adapted from: https://stackoverflow.com/questions/71968447/python-typing-copy-kwargs-from-one-function-to-another
# also refer to discussion here: https://discuss.python.org/t/taking-the-argument-signature-from-a-different-function/42618/20
#
# FIXME: ...in the future - It's currently impossible to slot in 'MyMetadata' as a named kwarg:
# https://peps.python.org/pep-0612/#concatenating-keyword-parameters
#
P = ParamSpec("P")  # param spec of wrapper
T = TypeVar("T")  # return type of wrapped function


@dataclass
class ExtraMeta:
    level: PresentationLevel = PresentationLevel.private


# cursed.
def wrap(_: Callable[P, Any]) -> Callable[[Callable[..., T]], Callable[Concatenate[ExtraMeta | None, P], T]]:
    """Wrap a `Converter` `__init__` in a type-safe way."""

    def impl(fun: Callable[..., T]) -> Callable[Concatenate[ExtraMeta | None, P], T]:
        return cast("Callable[Concatenate[ExtraMeta | None, P], T]", fun)

    return impl


@wrap(RawField)
def Field(mymetadata: ExtraMeta | None = ExtraMeta(), *args, **kwargs):
    """My custom docstring"""

    field = RawField(*args, **kwargs)
    # in the original FieldInfo metadata is an array so keep it consistent
    field.metadata.append(mymetadata)

    return field


class FieldInfo(RawFieldInfo):
    metadata: list[Any | ExtraMeta]


MODELS_CACHE: dict[tuple, type[RawBaseModel]] = {}  # pyright: ignore[reportGeneralTypeIssues]


class EBaseModelV2(RawBaseModel):
    if TYPE_CHECKING:
        model_fields: ClassVar[Mapping[str, FieldInfo]]  # pyright: ignore[reportIncompatibleVariableOverride]

    _model_public: ClassVar[type[RawBaseModel]]
    _model_admin: ClassVar[type[RawBaseModel]]

    public_model: ClassVar[type[RawBaseModel]]
    admin_model: ClassVar[type[RawBaseModel]]

    @classmethod
    def __extract_extra_meta(cls, field_info: FieldInfo) -> ExtraMeta | None:
        for metadata in field_info.metadata:
            if isinstance(metadata, ExtraMeta):
                return metadata
        return None

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs) -> None:  # noqa: ANN003
        super().__pydantic_init_subclass__(**kwargs)

        cls._model_public = cls._create_leveled_model(PresentationLevel.public)
        cls._model_admin = cls._create_leveled_model(PresentationLevel.admin)

        cls.public_model = cls._create_leveled_model(PresentationLevel.public)
        cls.admin_model = cls._create_leveled_model(PresentationLevel.admin)

    @classmethod
    def _create_leveled_model(cls, level: PresentationLevel) -> type[RawBaseModel]:
        cache_key = (cls.__module__, cls.__qualname__, level)

        if model := MODELS_CACHE.get(cache_key):
            return model

        new_fields: dict[str, tuple[type, RawFieldInfo]] = {}

        for field_name, field in cls.model_fields.items():
            meta = cls.__extract_extra_meta(field)

            if (annotation := field.annotation) is None:
                logger.error(f"WTF broken field {cls.__qualname__}: {field_name}, {field = }")
                continue

            # WTF: strange heuristic for `type XXX = Annotated[yyy, Field()]`
            # we live in totally cursed society https://github.com/pydantic/pydantic/issues/11467
            if not meta and _unpack_annotated(annotation, unpack_type_aliases="skip") == (annotation, []):
                inspected = inspect_annotation(
                    annotation,
                    annotation_source=AnnotationSource.ANY,
                    unpack_type_aliases="eager",
                )

                annotation = inspected.type
                field = FieldInfo.merge_field_infos(
                    inspected.metadata[0],
                    RawFieldInfo(
                        annotation=inspected.type,  # pyright: ignore[reportArgumentType]
                    ),
                )
                meta = cls.__extract_extra_meta(field)  # pyright: ignore[reportArgumentType] # fuck pydantic

            if not meta:
                logger.warning(f"{cls = }, {field_name = }, {field = }, {meta = } is not patched FieldInfo. Skipped!")
                continue

            if not meta.level or not isinstance(meta.level, PresentationLevel):
                logger.error(f"WTF field with strange level {cls.__qualname__}: {field_name}, {field = }")
                continue

            if not meta.level.is_visible(level):
                continue

            if origin_is_union(get_origin(annotation)):
                new_union_base: list[Any] = []
                for union_member in get_args(annotation):
                    if issubclass(union_member, EBaseModelV2):
                        new_union_base.append(union_member._create_leveled_model(level))
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
                new_field_cls = annotation._create_leveled_model(level)
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
