from typing import Union, get_args

from pydantic import BaseModel

from yatb.schema.ebasemodelv2 import EBaseModelV2, Field, PresentationLevel


class SimpleClass(EBaseModelV2):
    public_field: int = Field(level=PresentationLevel.all)
    admin_field: int = Field(level=PresentationLevel.admin)
    private_field: int = Field(level=PresentationLevel.private)


def test_simple_class_public():
    model = SimpleClass._model_all

    assert "public_field" in model.model_fields
    assert "admin_field" not in model.model_fields
    assert "private_field" not in model.model_fields


def test_simple_class_admin():
    model = SimpleClass._model_admin

    assert "public_field" in model.model_fields
    assert "admin_field" in model.model_fields
    assert "private_field" not in model.model_fields


class NestedClass(EBaseModelV2):
    class Nested(EBaseModelV2):
        public_field: int = Field(level=PresentationLevel.all)
        admin_field: int = Field(level=PresentationLevel.admin)
        private_field: int = Field(level=PresentationLevel.private)

    public_nested: Nested = Field(level=PresentationLevel.all)
    admin_nested: Nested = Field(level=PresentationLevel.admin)
    private_nested: Nested = Field(level=PresentationLevel.private)


def test_nested_class_all():
    model = NestedClass._model_all
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


class SimpleUnitedClass(EBaseModelV2):
    public_united: int | str = Field(level=PresentationLevel.all)
    admin_united: int | str = Field(level=PresentationLevel.admin)
    private_united: int | str = Field(level=PresentationLevel.private)


def test_simple_united_class_all():
    model = UnitedClass._model_all
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
        public_field_a: int = Field(level=PresentationLevel.all)
        admin_field_a: int = Field(level=PresentationLevel.admin)
        private_field_a: int = Field(level=PresentationLevel.private)

    class NestedB(EBaseModelV2):
        public_field_b: int = Field(level=PresentationLevel.all)
        admin_field_b: int = Field(level=PresentationLevel.admin)
        private_field_b: int = Field(level=PresentationLevel.private)

    public_united: NestedA | NestedB = Field(level=PresentationLevel.all)
    admin_united: NestedA | NestedB = Field(level=PresentationLevel.admin)
    private_united: NestedA | NestedB = Field(level=PresentationLevel.private)


def test_united_class_all():
    model = UnitedClass._model_all
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
