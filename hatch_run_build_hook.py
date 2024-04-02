import subprocess
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class HatchRunBuildHook(BuildHookInterface):
    PLUGIN_NAME = 'hatch-run-build'

    def initialize(self, version, build_data):
        # Run the 'hatch run build' command
        subprocess.run(['hatch', 'run', 'build'], check=True)