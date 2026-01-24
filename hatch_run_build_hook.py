"""
Hatch build hook for building comparison engine binaries.

This hook runs during the package build process to compile the
.NET binaries for all supported comparison engines and platforms.
"""

import os
import subprocess
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class HatchRunBuildHook(BuildHookInterface):
    PLUGIN_NAME = 'hatch-run-build'

    def initialize(self, version, build_data):
        """
        Initialize the build hook by compiling engine binaries.

        This runs the build_differ.py script which compiles self-contained
        .NET executables for all engines and platforms.
        """
        # Check if we should skip the build (useful for development)
        if os.environ.get('SKIP_BINARY_BUILD', '').lower() in ('1', 'true', 'yes'):
            print("Skipping binary build (SKIP_BINARY_BUILD is set)")
            return

        # Run the build script
        print("Building comparison engine binaries...")
        try:
            result = subprocess.run(
                ["python", "-m", "build_differ"],
                check=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Binary build failed: {e}")
            if e.stdout:
                print(f"stdout: {e.stdout}")
            if e.stderr:
                print(f"stderr: {e.stderr}")
            # Don't fail the build - binaries might already exist
            # or the user might be installing on a platform we don't build for
