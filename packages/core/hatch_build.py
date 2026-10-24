"""Keep optional engine dependencies in lockstep with the core release."""
from hatchling.metadata.plugin.interface import MetadataHookInterface


class CompanionMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        version = metadata["version"]
        ooxmlpowertools = f"python-redlines-ooxmlpowertools=={version}"
        docxodus = f"python-redlines-docxodus=={version}"
        # Keep the deprecated engine in both its own extra and `all`.
        metadata["optional-dependencies"] = {
            "ooxmlpowertools": [ooxmlpowertools],
            "docxodus": [docxodus],
            "all": [ooxmlpowertools, docxodus],
        }
