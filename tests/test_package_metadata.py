"""Check the shipped dependency metadata, including after a future version bump."""
from email.parser import BytesParser
from pathlib import Path
import shutil
import tarfile
import zipfile

from hatchling.builders.sdist import SdistBuilder
from hatchling.builders.wheel import WheelBuilder
from packaging.requirements import Requirement
import pytest


@pytest.mark.parametrize("version_override", [None, "9.8.7"])
def test_core_distributions_pin_companions(tmp_path, version_override):
    project = tmp_path / "core"
    shutil.copytree(
        Path(__file__).resolve().parents[1] / "packages" / "core", project,
        ignore=shutil.ignore_patterns("dist", "__pycache__", "*.egg-info"),
    )
    if version_override:
        (project / "src/python_redlines/__about__.py").write_text(
            f'__version__ = "{version_override}"\n', encoding="utf-8",
        )
    output = tmp_path / "dist"
    output.mkdir()
    wheel = next(WheelBuilder(str(project)).build(directory=str(output)))
    sdist = next(SdistBuilder(str(project)).build(directory=str(output)))
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))
        wheel_metadata = archive.read(metadata_name)
    with tarfile.open(sdist) as archive:
        assert any(n.endswith("/hatch_build.py") for n in archive.getnames())
        metadata_name = next(n for n in archive.getnames() if n.endswith("/PKG-INFO"))
        sdist_metadata = archive.extractfile(metadata_name).read()

    for raw_metadata in (wheel_metadata, sdist_metadata):
        metadata = BytesParser().parsebytes(raw_metadata)
        version = metadata["Version"]
        if version_override:
            assert version == version_override
        requirements = [Requirement(r) for r in metadata.get_all("Requires-Dist", [])]
        companions = [r for r in requirements if r.name.startswith("python-redlines-")]
        for extra, names in {
            "": set(),
            "docxodus": {"python-redlines-docxodus"},
            "ooxmlpowertools": {"python-redlines-ooxmlpowertools"},
            "all": {"python-redlines-docxodus", "python-redlines-ooxmlpowertools"},
        }.items():
            selected = [r for r in companions if r.marker is None or r.marker.evaluate({"extra": extra})]
            assert {r.name for r in selected} == names
            assert all(str(r.specifier) == f"=={version}" for r in selected)
