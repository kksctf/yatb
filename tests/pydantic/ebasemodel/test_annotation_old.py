from typing import Annotated

from yatb.ebasemodelv2 import EBaseModelV2, PresentationLevel

PublicInt = Annotated[int, PresentationLevel.public]
AdminInt = Annotated[int, PresentationLevel.admin]
PrivateInt = Annotated[int, PresentationLevel.private]


class SimpleClass(EBaseModelV2):
    public_field: PublicInt
    admin_field: AdminInt
    private_field: PrivateInt


def test_simple_annotation_old_public():
    model = SimpleClass._model_public

    assert "public_field" in model.model_fields
    assert "admin_field" not in model.model_fields
    assert "private_field" not in model.model_fields


def test_simple_annotation_old_admin():
    model = SimpleClass._model_admin

    assert "public_field" in model.model_fields
    assert "admin_field" in model.model_fields
    assert "private_field" not in model.model_fields
