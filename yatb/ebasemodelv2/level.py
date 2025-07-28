from enum import Enum, auto
from typing import Annotated, Self


class PresentationLevel(Enum):
    public = auto()
    admin = auto()
    private = auto()

    def is_visible(self, target: Self) -> bool:
        if self == self.public:
            return True

        if self == self.admin and target in (self.admin, self.private):
            return True

        if self == self.private:
            return False

        return False
