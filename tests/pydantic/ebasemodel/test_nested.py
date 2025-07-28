from typing import Annotated

from pydantic import BaseModel

from yatb.ebasemodelv2 import EBaseModelV2, PresentationLevel

type PublicInt = Annotated[int, PresentationLevel.public]
type AdminInt = Annotated[int, PresentationLevel.admin]
type PrivateInt = Annotated[int, PresentationLevel.private]


class NestedClass(EBaseModelV2):
    class Nested(EBaseModelV2):
        public_field: PublicInt
        admin_field: AdminInt
        private_field: PrivateInt

    public_nested: Annotated[Nested, PresentationLevel.public]
    admin_nested: Annotated[Nested, PresentationLevel.admin]
    private_nested: Annotated[Nested, PresentationLevel.private]


def test_nested_class_all():
    model = NestedClass._model_public
    assert "public_nested" in model.model_fields
    assert "admin_nested" not in model.model_fields
    assert "private_nested" not in model.model_fields

    public_nested: type[BaseModel] | None = model.model_fields["public_nested"].annotation
    assert public_nested

    assert "public_field" in public_nested.model_fields
    assert "admin_field" not in public_nested.model_fields
    assert "private_field" not in public_nested.model_fields


def test_nested_class_admin():
    model = NestedClass._model_admin
    assert "public_nested" in model.model_fields
    assert "admin_nested" in model.model_fields
    assert "private_nested" not in model.model_fields

    public_nested: type[BaseModel] | None = model.model_fields["public_nested"].annotation
    assert public_nested

    assert "public_field" in public_nested.model_fields
    assert "admin_field" in public_nested.model_fields
    assert "private_field" not in public_nested.model_fields

    admin_nested: type[BaseModel] | None = model.model_fields["admin_nested"].annotation
    assert admin_nested

    assert "public_field" in admin_nested.model_fields
    assert "admin_field" in admin_nested.model_fields
    assert "private_field" not in admin_nested.model_fields
