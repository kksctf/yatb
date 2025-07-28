from typing import Annotated

from yatb.ebasemodelv2 import EBaseModelV2, PresentationLevel

type PublicInt = Annotated[int, PresentationLevel.public]
type AdminInt = Annotated[int, PresentationLevel.admin]
type PrivateInt = Annotated[int, PresentationLevel.private]

type AdminSubtypeInt = Annotated[PrivateInt, PresentationLevel.admin]


class SimpleClass(EBaseModelV2):
    public_from_private: Annotated[PrivateInt, PresentationLevel.public]

    admin_from_private_subtype: AdminSubtypeInt
    admin_from_private: Annotated[PrivateInt, PresentationLevel.admin]

    private_from_public: Annotated[PublicInt, PresentationLevel.private]


def test_override_public():
    model = SimpleClass._model_public

    assert "public_from_private" in model.model_fields

    assert "admin_from_private_subtype" not in model.model_fields
    assert "admin_from_private" not in model.model_fields

    assert "private_from_public" not in model.model_fields


def test_override_admin():
    model = SimpleClass._model_admin

    assert "public_from_private" in model.model_fields

    assert "admin_from_private_subtype" in model.model_fields
    assert "admin_from_private" in model.model_fields

    assert "private_from_public" not in model.model_fields
