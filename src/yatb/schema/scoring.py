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
        # No need to calculate anything if there is no solves
        if self.solves <= 0:
            return self.maximum

        # Enforce the absolute floor once the decay threshold is met.
        if self.solves >= self.decay:
            return self.minimum

        # --- Hill‑curve (sigmoid) parameters ---
        # k: solves *after the plateau* where the score is ~½ between max & min
        k = 6  # solves count where the score is ~½ way between max and min
        p = 3  # steepness exponent: larger => sharper drop

        # Hill (generalised logistic) curve:
        raw = self.minimum + (self.maximum - self.minimum) / (1 + ((self.solves - 1) / k) ** p)

        # Ensure the final score stays within [minimum, maximum].
        return max(self.minimum, min(self.maximum, math.ceil(raw)))

    def solve_task(self) -> bool:
        self.solves += 1
        return True

    def set_solves(self, count: int) -> None:
        self.solves = count

    def reset(self) -> None:
        self.set_solves(0)
