import math

from . import EBaseModel, Literal, logger


class Scoring(EBaseModel):
    __public_fields__ = {
        "classtype",
        "points",
    }
    classtype: Literal['Scoring'] = "Scoring"

    @property
    def points(self) -> int:
        return -1337

    def solve_task(self) -> bool:
        return False

    def reset(self):
        pass
    # class Config:
    #    extra = Extra.allow


class StaticScoring(Scoring):
    __admin_only_fields__ = {
        "static_points"
    }
    classtype: Literal['StaticScoring'] = "StaticScoring"

    static_points: int

    @property
    def points(self) -> int:
        return self.static_points

    def solve_task(self) -> bool:
        return False


class DynamicKKSScoring(Scoring):
    __admin_only_fields__ = {
        "solves",
        "decay",
        "minimum",
        "maximum"
    }
    classtype: Literal['DynamicKKSScoring'] = "DynamicKKSScoring"

    solves: int = 0
    decay: int = 50
    minimum: int = 100
    maximum: int = 1000

    @property
    def points(self) -> int:
        if self.solves == 0:
            return self.maximum
        if self.solves >= self.decay:
            return self.minimum
        else:
            coeff = 495 - (1 - math.pow(self.decay / (10**6), 0.25)) * 65.91 * math.log(self.decay)
            out = self.maximum - coeff * math.log(self.solves)
            if out > self.maximum:
                logger.warning(f"Wtf why more than maximum at {self}")
            return min(max(self.minimum, math.ceil(out)), self.maximum)

    def solve_task(self) -> bool:
        self.solves += 1
        return True

    def reset(self):
        self.solves = 0
