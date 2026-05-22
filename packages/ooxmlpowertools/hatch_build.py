"""Wheel build hook: stamp the platform tag from the bundled binary archive.

Each binary package wheel must target exactly one platform. The archive placed
in src/<pkg>/_binaries/ by build_differ.py determines the wheel's platform tag.
"""
import pathlib

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

# .NET runtime identifier -> wheel platform tag
PLATFORM_TAGS = {
    "linux-x64": "manylinux2014_x86_64",
    "linux-arm64": "manylinux2014_aarch64",
    "win-x64": "win_amd64",
    "win-arm64": "win_arm64",
    "osx-x64": "macosx_11_0_x86_64",
    "osx-arm64": "macosx_11_0_arm64",
}


class RedlinesBinaryBuildHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version, build_data):
        archives = sorted(
            p for p in (pathlib.Path(self.root) / "src").glob("*/_binaries/*")
            if p.name.endswith((".tar.gz", ".zip"))
        )
        if len(archives) != 1:
            raise ValueError(
                f"Expected exactly one binary archive under src/*/_binaries/, "
                f"found {len(archives)}: {[a.name for a in archives]}. "
                f"Run `python build_differ.py <rid>` to populate it before building."
            )

        rid = archives[0].name.split(".", 1)[0]
        if rid not in PLATFORM_TAGS:
            raise ValueError(f"Unknown runtime identifier '{rid}' from archive {archives[0].name}")

        build_data["pure_python"] = False
        build_data["infer_tag"] = False
        build_data["tag"] = f"py3-none-{PLATFORM_TAGS[rid]}"
