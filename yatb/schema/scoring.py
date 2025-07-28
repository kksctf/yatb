import math
from typing import Literal

from pydantic import computed_field

from ..ebasemodelv2 import Admin, EBaseModelV2, Public
from ..utils.log_helper import get_logger

logger = get_logger("schema.scoring")


class Scoring(EBaseModelV2):
    classtype: Public[Literal["Scoring"]] = "Scoring"

    @computed_field
    @property
    def points(self) -> Public[int]:
        return -1337

    def solve_task(self) -> bool:
        return False

    def set_solves(self, count: int) -> None:
        pass

    def reset(self) -> None:
        pass


class StaticScoring(Scoring):
    classtype: Public[Literal["StaticScoring"]] = "StaticScoring"

    static_points: Admin[int]

    @computed_field
    @property
    def points(self) -> Public[int]:
        return self.static_points

    def solve_task(self) -> bool:
        return False


class DynamicKKSScoring(Scoring):
    classtype: Public[Literal["DynamicKKSScoring"]] = "DynamicKKSScoring"

    solves: Admin[int] = 0
    decay: Admin[int] = 50
    minimum: Admin[int] = 100
    maximum: Admin[int] = 1000

    @computed_field
    @property
    def points(self) -> Public[int]:
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
