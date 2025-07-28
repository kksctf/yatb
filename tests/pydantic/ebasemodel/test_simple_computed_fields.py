from typing import Annotated

from pydantic import computed_field

from yatb.ebasemodelv2 import EBaseModelV2, PresentationLevel


class SimpleClass(EBaseModelV2):
    @computed_field
    @property
    def public_prop(self) -> Annotated[int, PresentationLevel.public]:
        return -1

    @computed_field
    @property
    def admin_prop(self) -> Annotated[int, PresentationLevel.admin]:
        return 0

    @computed_field
    @property
    def private_prop(self) -> Annotated[int, PresentationLevel.private]:
        return 1


def test_simple_class_public():
    model = SimpleClass._model_public

    assert "public_prop" in model.model_computed_fields
    assert "admin_prop" not in model.model_computed_fields
    assert "private_prop" not in model.model_computed_fields


def test_simple_class_admin():
    model = SimpleClass._model_admin

    assert "public_prop" in model.model_computed_fields
    assert "admin_prop" in model.model_computed_fields
    assert "private_prop" not in model.model_computed_fields

    inst = model()
    assert inst.public_prop == -1
    assert inst.admin_prop == 0
