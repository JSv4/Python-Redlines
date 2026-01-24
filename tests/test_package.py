"""
Tests for the package-level API and imports.
"""

import pytest


class TestPackageImports:
    """Tests for package-level imports."""

    def test_import_package(self):
        """Test that the main package can be imported."""
        import python_redlines
        assert python_redlines is not None

    def test_import_version(self):
        """Test that version is available."""
        from python_redlines import __version__
        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_import_base_classes(self):
        """Test that base classes can be imported."""
        from python_redlines import ComparisonEngine, ComparisonError
        assert ComparisonEngine is not None
        assert ComparisonError is not None

    def test_import_engine_classes(self):
        """Test that engine classes can be imported."""
        from python_redlines import XmlPowerToolsEngine, DocxodusEngine
        assert XmlPowerToolsEngine is not None
        assert DocxodusEngine is not None

    def test_import_registry_functions(self):
        """Test that registry functions can be imported."""
        from python_redlines import (
            get_engine,
            list_engines,
            list_available_engines,
            EngineRegistry,
        )
        assert get_engine is not None
        assert list_engines is not None
        assert list_available_engines is not None
        assert EngineRegistry is not None

    def test_all_exports(self):
        """Test that __all__ contains expected exports."""
        import python_redlines

        expected_exports = [
            "__version__",
            "ComparisonEngine",
            "ComparisonError",
            "XmlPowerToolsEngine",
            "DocxodusEngine",
            "get_engine",
            "list_engines",
            "list_available_engines",
            "EngineRegistry",
        ]

        for export in expected_exports:
            assert export in python_redlines.__all__, f"Missing export: {export}"
            assert hasattr(python_redlines, export), f"Missing attribute: {export}"


class TestPackageDocstrings:
    """Tests for package documentation."""

    def test_package_docstring(self):
        """Test that the package has a docstring."""
        import python_redlines
        assert python_redlines.__doc__ is not None
        assert "Python Redlines" in python_redlines.__doc__

    def test_comparison_engine_docstring(self):
        """Test that ComparisonEngine has a docstring."""
        from python_redlines import ComparisonEngine
        assert ComparisonEngine.__doc__ is not None

    def test_get_engine_docstring(self):
        """Test that get_engine has a docstring."""
        from python_redlines import get_engine
        assert get_engine.__doc__ is not None


class TestEngineRegistration:
    """Tests for engine registration behavior."""

    def test_engines_auto_registered_on_import(self):
        """Test that engines are automatically registered on import."""
        from python_redlines import list_engines

        engines = list_engines()
        assert len(engines) >= 2
        assert "openxml-powertools" in engines
        assert "docxodus" in engines

    def test_default_engine_is_openxml_powertools(self):
        """Test that the default engine is openxml-powertools."""
        from python_redlines import EngineRegistry

        default = EngineRegistry.get_default_engine_name()
        assert default == "openxml-powertools"


class TestPackageUsagePatterns:
    """Tests for common usage patterns documented in the package."""

    def test_basic_usage_pattern(self):
        """Test the basic usage pattern from the docstring."""
        from python_redlines import get_engine

        # This tests the pattern, not the actual comparison
        # (which requires binaries)
        try:
            engine = get_engine()
            assert engine.name == "openxml-powertools"
        except FileNotFoundError:
            pytest.skip("Binaries not available")

    def test_specific_engine_pattern(self):
        """Test selecting a specific engine by name."""
        from python_redlines import get_engine

        try:
            engine = get_engine("openxml-powertools")
            assert engine.name == "openxml-powertools"
        except FileNotFoundError:
            pytest.skip("Binaries not available")

    def test_list_engines_pattern(self):
        """Test listing available engines."""
        from python_redlines import list_engines

        engines = list_engines()
        assert isinstance(engines, list)
        assert len(engines) > 0

    def test_invalid_engine_raises_value_error(self):
        """Test that requesting an invalid engine raises ValueError."""
        from python_redlines import get_engine

        with pytest.raises(ValueError) as exc_info:
            get_engine("nonexistent-engine")

        assert "nonexistent-engine" in str(exc_info.value)
