# ruff: noqa: INP001
from pathlib import Path
from typing import Any

import hatch_babel
from babel.messages.frontend import CommandLineInterface


class TranslationBuildHook(hatch_babel.PybabelBuldHook):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        locale_dir = Path(self.build_config.root) / self.config["locale_dir"]
        for catalog in sorted(locale_dir.glob("*/LC_MESSAGES/private.po")):
            result = CommandLineInterface().run(
                ["pybabel", "compile", "-i", str(catalog), "-o", str(catalog.with_suffix(".mo"))],
            )
            if result:
                raise RuntimeError(f"Failed to compile {catalog}")
        super().initialize(version, build_data)
