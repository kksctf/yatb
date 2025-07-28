from typing import Annotated, Literal

from .level import PresentationLevel as P

type Public[X] = Annotated[X, P.public]
type Admin[X] = Annotated[X, P.admin]
type Private[X] = Annotated[X, P.private]
