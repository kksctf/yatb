from io import StringIO
from pathlib import Path
from typing import Self

from pydantic import BaseModel, TypeAdapter
from ruamel.yaml import YAML, CommentedMap


class YAMLModel(BaseModel):
    __raw_yaml: CommentedMap | None = None  # pyright: ignore[reportGeneralTypeIssues]
    __original_path: Path | None = None  # pyright: ignore[reportGeneralTypeIssues]

    @staticmethod
    def __make_yaml() -> YAML:
        return YAML(typ="rt", pure=True)

    @classmethod
    def load_yaml(cls: type[Self], src: Path) -> Self:
        reader = cls.__make_yaml()

        with src.open("r", encoding="utf-8") as stream:
            objects = reader.load(stream)

        ta = TypeAdapter(cls)

        ret = ta.validate_python(objects)
        ret.__raw_yaml = objects  # noqa: SLF001
        ret.__original_path = src  # noqa: SLF001

        return ret

    def dump_yaml(self) -> str:
        if not self.__raw_yaml:
            raise Exception

        writer = self.__make_yaml()

        data = self.model_dump(mode="json")
        self.__raw_yaml.update(data)

        result = StringIO()
        writer.dump(self.__raw_yaml, result)

        return result.getvalue()

    def save_yaml_to_file(self) -> None:
        if not self.__original_path:
            raise Exception

        with self.__original_path.open("w", encoding="utf-8") as f:
            f.write(self.dump_yaml())
