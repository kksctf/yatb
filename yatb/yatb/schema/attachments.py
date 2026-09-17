from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl


class FileAttachment(BaseModel):
    type: Literal["file"] = "file"

    name: Annotated[str, Field(min_length=1)]
    url: HttpUrl
    size_bytes: Annotated[int, Field(ge=0)]
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class WebAttachment(BaseModel):
    type: Literal["web"] = "web"

    label: Annotated[str, Field(min_length=1)]
    url: HttpUrl


class EndpointAttachment(BaseModel):
    type: Literal["endpoint"] = "endpoint"

    label: Annotated[str, Field(min_length=1)]
    host: Annotated[str, Field(min_length=1)]
    port: Annotated[int, Field(ge=1, le=65535)]


type Attachment = Annotated[
    FileAttachment | WebAttachment | EndpointAttachment,
    Field(discriminator="type"),
]
