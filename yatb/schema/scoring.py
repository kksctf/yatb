import math
from typing import ClassVar, Literal

from pydantic import computed_field

from ..utils.log_helper import get_logger
from .ebasemodel import EBaseModel

logger = get_logger("schema.scoring")


class Scoring(EBaseModel):
    __public_fields__: ClassVar = {
        "classtype",
        "points",
    }
    classtype: Literal["Scoring"] = "Scoring"

    @computed_field
    @property
    def points(self) -> int:
        return -1337

    def solve_task(self) -> bool:
        return False

    def set_solves(self, count: int) -> None:
        pass

    def reset(self) -> None:
        pass

    # class Config:
    #    extra = Extra.allow


class StaticScoring(Scoring):
    __admin_only_fields__: ClassVar = {"static_points"}
    classtype: Literal["StaticScoring"] = "StaticScoring"

    static_points: int

    @computed_field
    @property
    def points(self) -> int:
        return self.static_points

    def solve_task(self) -> bool:
        return False


class DynamicKKSScoring(Scoring):
    __admin_only_fields__: ClassVar = {"solves", "decay", "minimum", "maximum"}
    classtype: Literal["DynamicKKSScoring"] = "DynamicKKSScoring"

    solves: int = 0
    decay: int = 50
    minimum: int = 100
    maximum: int = 1000

    @computed_field
    @property
    def points(self) -> int:
        if self.solves == 0:
            return self.maximum
        if self.solves >= self.decay:
            return self.minimum

        coeff = 495 - (1 - math.pow(self.decay / (10**6), 0.25)) * 65.91 * math.log(self.decay)
        out = self.maximum - coeff * math.log(self.solves)
        if out > self.maximum:
            logger.warning(f"Wtf why more than maximum at {self}")
        return min(max(self.minimum, math.ceil(out)), self.maximum)

    def solve_task(self) -> bool:
        self.solves += 1
        return True

    def set_solves(self, count: int) -> None:
        self.solves = count

    def reset(self) -> None:
        self.set_solves(0)
