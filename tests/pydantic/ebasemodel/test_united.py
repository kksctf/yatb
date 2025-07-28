from typing import Annotated, Union, get_args

from pydantic import BaseModel

from yatb.ebasemodelv2 import EBaseModelV2, PresentationLevel

type PublicInt = Annotated[int | str, PresentationLevel.public]
type AdminInt = Annotated[int | str, PresentationLevel.admin]
type PrivateInt = Annotated[int | str, PresentationLevel.private]


class SimpleUnitedClass(EBaseModelV2):
    public_united: PublicInt
    admin_united: AdminInt
    private_united: PrivateInt


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


class NestedA(EBaseModelV2):
    public_field_a: PublicInt
    admin_field_a: AdminInt
    private_field_a: PrivateInt


class NestedB(EBaseModelV2):
    public_field_b: PublicInt
    admin_field_b: AdminInt
    private_field_b: PrivateInt


type PubicUnited = Annotated[NestedA | NestedB, PresentationLevel.public]
type AdminUnited = Annotated[NestedA | NestedB, PresentationLevel.admin]
type PrivateUnited = Annotated[NestedA | NestedB, PresentationLevel.private]


class UnitedClass(EBaseModelV2):
    public_united: PubicUnited
    admin_united: AdminUnited
    private_united: PrivateUnited


def test_united_class_all():
    model = UnitedClass._model_public
    assert "public_united" in model.model_fields
    assert "admin_united" not in model.model_fields
    assert "private_united" not in model.model_fields

    public_united: Union[type[BaseModel], type[BaseModel]] | None = model.model_fields["public_united"].annotation  # noqa: PYI016, PYI055, UP007
    assert public_united

    for part, public_united_entry in zip(["a", "b"], get_args(public_united), strict=True):
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

    for part, public_united_entry in zip(["a", "b"], get_args(public_united), strict=True):
        assert f"public_field_{part}" in public_united_entry.model_fields
        assert f"admin_field_{part}" in public_united_entry.model_fields
        assert f"private_field_{part}" not in public_united_entry.model_fields

    admin_united: Union[type[BaseModel], type[BaseModel]] | None = model.model_fields["admin_united"].annotation  # noqa: PYI016, PYI055, UP007
    assert admin_united

    for part, admin_united_entry in zip(["a", "b"], get_args(admin_united), strict=True):
        assert f"public_field_{part}" in admin_united_entry.model_fields
        assert f"admin_field_{part}" in admin_united_entry.model_fields
        assert f"private_field_{part}" not in admin_united_entry.model_fields
