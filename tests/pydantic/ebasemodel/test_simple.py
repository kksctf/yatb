from typing import Union, get_args

from pydantic import BaseModel

from yatb.ebasemodelv2 import EBaseModelV2, Field, PresentationLevel, ExtraMeta


class SimpleClass(EBaseModelV2):
    public_field: int = Field(ExtraMeta(PresentationLevel.public), ...)
    admin_field: int = Field(ExtraMeta(PresentationLevel.admin), ...)
    private_field: int = Field(ExtraMeta(PresentationLevel.private), ...)


def test_simple_class_public():
    model = SimpleClass._model_public

    assert "public_field" in model.model_fields
    assert "admin_field" not in model.model_fields
    assert "private_field" not in model.model_fields


def test_simple_class_admin():
    model = SimpleClass._model_admin

    assert "public_field" in model.model_fields
    assert "admin_field" in model.model_fields
    assert "private_field" not in model.model_fields
