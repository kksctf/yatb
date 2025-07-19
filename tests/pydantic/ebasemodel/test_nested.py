from typing import Union, get_args

from pydantic import BaseModel

from yatb.ebasemodelv2 import EBaseModelV2, ExtraMeta, Field, PresentationLevel


class NestedClass(EBaseModelV2):
    class Nested(EBaseModelV2):
        public_field: int = Field(ExtraMeta(PresentationLevel.public), ...)
        admin_field: int = Field(ExtraMeta(PresentationLevel.admin), ...)
        private_field: int = Field(ExtraMeta(PresentationLevel.private), ...)

    public_nested: Nested = Field(ExtraMeta(PresentationLevel.public), ...)
    admin_nested: Nested = Field(ExtraMeta(PresentationLevel.admin), ...)
    private_nested: Nested = Field(ExtraMeta(PresentationLevel.private), ...)


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
