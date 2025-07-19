from typing import Union, get_args

from pydantic import BaseModel

from yatb.ebasemodelv2 import EBaseModelV2, Field, ExtraMeta, PresentationLevel


class SimpleUnitedClass(EBaseModelV2):
    public_united: int | str = Field(ExtraMeta(PresentationLevel.public), ...)
    admin_united: int | str = Field(ExtraMeta(PresentationLevel.admin), ...)
    private_united: int | str = Field(ExtraMeta(PresentationLevel.private), ...)


def test_simple_united_class_all():
    model = UnitedClass._model_public
    assert "public_united" in model.model_fields
    assert "admin_united" not in model.model_fields
    assert "private_united" not in model.model_fields


def test_simple_united_class_admin():
    model = UnitedClass._model_admin
    assert "public_united" in model.model_fields
    assert "admin_united" in model.model_fields
    assert "private_united" not in model.model_fields


class UnitedClass(EBaseModelV2):
    class NestedA(EBaseModelV2):
        public_field_a: int = Field(ExtraMeta(PresentationLevel.public), ...)
        admin_field_a: int = Field(ExtraMeta(PresentationLevel.admin), ...)
        private_field_a: int = Field(ExtraMeta(PresentationLevel.private), ...)

    class NestedB(EBaseModelV2):
        public_field_b: int = Field(ExtraMeta(PresentationLevel.public), ...)
        admin_field_b: int = Field(ExtraMeta(PresentationLevel.admin), ...)
        private_field_b: int = Field(ExtraMeta(PresentationLevel.private), ...)

    public_united: NestedA | NestedB = Field(ExtraMeta(PresentationLevel.public), ...)
    admin_united: NestedA | NestedB = Field(ExtraMeta(PresentationLevel.admin), ...)
    private_united: NestedA | NestedB = Field(ExtraMeta(PresentationLevel.private), ...)


def test_united_class_all():
    model = UnitedClass._model_public
    assert "public_united" in model.model_fields
    assert "admin_united" not in model.model_fields
    assert "private_united" not in model.model_fields

    public_united: Union[type[BaseModel], type[BaseModel]] | None = model.model_fields["public_united"].annotation  # noqa: PYI016, PYI055, UP007
    assert public_united

    for part, public_united_entry in zip(["a", "b"], get_args(public_united), strict=False):
        assert f"public_field_{part}" in public_united_entry.model_fields
        assert f"admin_field_{part}" not in public_united_entry.model_fields
        assert f"private_field_{part}" not in public_united_entry.model_fields


def test_united_class_admin():
    model = UnitedClass._model_admin
    assert "public_united" in model.model_fields
    assert "admin_united" in model.model_fields
    assert "private_united" not in model.model_fields

    public_united: Union[type[BaseModel], type[BaseModel]] | None = model.model_fields["public_united"].annotation  # noqa: PYI016, PYI055, UP007
    assert public_united

    for part, public_united_entry in zip(["a", "b"], get_args(public_united), strict=False):
        assert f"public_field_{part}" in public_united_entry.model_fields
        assert f"admin_field_{part}" in public_united_entry.model_fields
        assert f"private_field_{part}" not in public_united_entry.model_fields

    admin_united: Union[type[BaseModel], type[BaseModel]] | None = model.model_fields["admin_united"].annotation  # noqa: PYI016, PYI055, UP007
    assert admin_united

    for part, admin_united_entry in zip(["a", "b"], get_args(admin_united), strict=False):
        assert f"public_field_{part}" in admin_united_entry.model_fields
        assert f"admin_field_{part}" in admin_united_entry.model_fields
        assert f"private_field_{part}" not in admin_united_entry.model_fields
