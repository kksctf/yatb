from typing import Annotated, Union, get_args

from pydantic import BaseModel

from yatb.schema.ebasemodelv2 import EBaseModelV2, Field, PresentationLevel

type PublicInt = Annotated[int, Field(level=PresentationLevel.public)]
type AdminInt = Annotated[int, Field(level=PresentationLevel.admin)]
type PrivateInt = Annotated[int, Field(level=PresentationLevel.private)]


class SimpleClass(EBaseModelV2):
    public_field: PublicInt
    admin_field: AdminInt
    private_field: PrivateInt


def test_simple_annotation_public():
    model = SimpleClass._model_public

    assert "public_field" in model.model_fields
    assert "admin_field" not in model.model_fields
    assert "private_field" not in model.model_fields


def test_simple_annotation_admin():
    model = SimpleClass._model_admin

    assert "public_field" in model.model_fields
    assert "admin_field" in model.model_fields
    assert "private_field" not in model.model_fields
