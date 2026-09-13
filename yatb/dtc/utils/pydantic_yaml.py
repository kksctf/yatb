# https://github.com/NowanIlfideme/pydantic-yaml/blob/06b75137860ec6ad834b397a474fab7db00140ee/src/pydantic_yaml/_internals/v2.py
# MIT License

# Copyright (c) 2020 Anatoly Makarevich

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from io import BytesIO, IOBase, StringIO
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, TypeAdapter
from ruamel.yaml import YAML

T = TypeVar("T", bound=BaseModel)


def parse_yaml_raw_as(
    model_type: type[T],
    raw: str | bytes | IOBase,
    *,
    context: dict[str, Any] | None = None,
) -> T:
    """
    Parse raw YAML string as the passed model type.

    Parameters
    ----------
    model_type : Type[BaseModel]
        The resulting model type.
    raw : str or bytes or IOBase
        The YAML string or stream.
    context : dict[str, Any]
        pass to validate_python

    """

    stream: IOBase
    if isinstance(raw, str):
        stream = StringIO(raw)
    elif isinstance(raw, bytes):
        stream = BytesIO(raw)
    elif isinstance(raw, IOBase):
        stream = raw
    else:
        raise TypeError(f"Expected str, bytes or IO, but got {raw!r}")
    reader = YAML(typ="safe", pure=True)  # YAML 1.2 support
    objects = reader.load(stream)
    ta = TypeAdapter(model_type)  # type: ignore
    return ta.validate_python(objects, context=context)


def parse_yaml_file_as(
    model_type: type[T],
    file: Path | str | IOBase,
    *,
    context: dict[str, Any] | None = None,
) -> T:
    """
    Parse YAML file as the passed model type.

    Parameters
    ----------
    model_type : Type[BaseModel]
        The resulting model type.
    file : Path or str or IOBase
        The file path or stream to read from.
    context : dict[str, Any]
        pass to validate_python

    """

    # Short-circuit
    if isinstance(file, IOBase):
        return parse_yaml_raw_as(model_type, raw=file)

    if isinstance(file, str):
        file = Path(file).resolve()
    elif isinstance(file, Path):
        file = file.resolve()
    else:
        raise TypeError(f"Expected Path, str or IO, but got {file!r}")

    with file.open(mode="r") as f:
        return parse_yaml_raw_as(model_type, f, context=context)
