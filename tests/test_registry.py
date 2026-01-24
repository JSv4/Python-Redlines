"""
Tests for the engine registry system.
"""

import pytest
from pathlib import Path
from typing import Tuple, Optional, Union

from python_redlines.base import ComparisonEngine
from python_redlines.registry import (
    EngineRegistry,
    get_engine,
    list_engines,
    list_available_engines,
)


class MockEngine(ComparisonEngine):
    """A mock engine for testing the registry."""

    def __init__(self, target_path: Optional[str] = None):
        self.target_path = target_path

    @property
    def name(self) -> str:
        return "mock-engine"

    @property
    def description(self) -> str:
        return "A mock engine for testing"

    def compare(
        self,
        author: str,
        original: Union[bytes, Path],
        modified: Union[bytes, Path]
    ) -> Tuple[bytes, Optional[str], Optional[str]]:
        return b"mock result", f"Author: {author}", None

    def is_available(self) -> bool:
        return True


class AnotherMockEngine(ComparisonEngine):
    """Another mock engine for testing."""

    @property
    def name(self) -> str:
        return "another-mock"

    @property
    def description(self) -> str:
        return "Another mock engine"

    def compare(
        self,
        author: str,
        original: Union[bytes, Path],
        modified: Union[bytes, Path]
    ) -> Tuple[bytes, Optional[str], Optional[str]]:
        return b"another result", None, None

    def is_available(self) -> bool:
        return True


class TestEngineRegistry:
    """Tests for the EngineRegistry class."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Save and restore registry state around each test."""
        # Save current state
        saved_engines = EngineRegistry._engines.copy()
        saved_default = EngineRegistry._default_engine

        yield

        # Restore state
        EngineRegistry._engines = saved_engines
        EngineRegistry._default_engine = saved_default

    def test_register_engine(self):
        """Test registering an engine."""
        EngineRegistry.clear()
        EngineRegistry.register(MockEngine)

        assert "mock-engine" in EngineRegistry.list_engines()

    def test_register_engine_as_default(self):
        """Test registering an engine as the default."""
        EngineRegistry.clear()
        EngineRegistry.register(MockEngine, default=True)

        assert EngineRegistry.get_default_engine_name() == "mock-engine"

    def test_first_registered_becomes_default(self):
        """Test that the first registered engine becomes default if none set."""
        EngineRegistry.clear()
        EngineRegistry.register(MockEngine)

        assert EngineRegistry.get_default_engine_name() == "mock-engine"

    def test_get_engine_by_name(self):
        """Test getting an engine by name."""
        EngineRegistry.clear()
        EngineRegistry.register(MockEngine)

        engine = EngineRegistry.get_engine("mock-engine")
        assert isinstance(engine, MockEngine)
        assert engine.name == "mock-engine"

    def test_get_default_engine(self):
        """Test getting the default engine."""
        EngineRegistry.clear()
        EngineRegistry.register(MockEngine, default=True)
        EngineRegistry.register(AnotherMockEngine)

        engine = EngineRegistry.get_engine()
        assert isinstance(engine, MockEngine)

    def test_get_engine_unknown_raises(self):
        """Test that getting an unknown engine raises ValueError."""
        EngineRegistry.clear()
        EngineRegistry.register(MockEngine)

        with pytest.raises(ValueError) as exc_info:
            EngineRegistry.get_engine("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "mock-engine" in str(exc_info.value)

    def test_get_engine_empty_registry_raises(self):
        """Test that getting an engine from empty registry raises RuntimeError."""
        EngineRegistry.clear()

        with pytest.raises(RuntimeError) as exc_info:
            EngineRegistry.get_engine()

        assert "No comparison engines registered" in str(exc_info.value)

    def test_list_engines(self):
        """Test listing all registered engines."""
        EngineRegistry.clear()
        EngineRegistry.register(MockEngine)
        EngineRegistry.register(AnotherMockEngine)

        engines = EngineRegistry.list_engines()
        assert "mock-engine" in engines
        assert "another-mock" in engines
        assert len(engines) == 2

    def test_set_default_engine(self):
        """Test setting the default engine."""
        EngineRegistry.clear()
        EngineRegistry.register(MockEngine)
        EngineRegistry.register(AnotherMockEngine)

        EngineRegistry.set_default_engine("another-mock")
        assert EngineRegistry.get_default_engine_name() == "another-mock"

    def test_set_default_unknown_raises(self):
        """Test that setting unknown engine as default raises ValueError."""
        EngineRegistry.clear()
        EngineRegistry.register(MockEngine)

        with pytest.raises(ValueError):
            EngineRegistry.set_default_engine("nonexistent")

    def test_get_engine_with_kwargs(self):
        """Test that kwargs are passed to engine constructor."""
        EngineRegistry.clear()
        EngineRegistry.register(MockEngine)

        engine = EngineRegistry.get_engine("mock-engine", target_path="/custom/path")
        assert engine.target_path == "/custom/path"

    def test_clear_registry(self):
        """Test clearing the registry."""
        EngineRegistry.clear()
        EngineRegistry.register(MockEngine)
        EngineRegistry.register(AnotherMockEngine)

        assert len(EngineRegistry.list_engines()) == 2

        EngineRegistry.clear()

        assert len(EngineRegistry.list_engines()) == 0
        assert EngineRegistry.get_default_engine_name() is None


class TestConvenienceFunctions:
    """Tests for the module-level convenience functions."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Save and restore registry state around each test."""
        saved_engines = EngineRegistry._engines.copy()
        saved_default = EngineRegistry._default_engine

        yield

        EngineRegistry._engines = saved_engines
        EngineRegistry._default_engine = saved_default

    def test_get_engine_function(self):
        """Test the get_engine convenience function."""
        EngineRegistry.clear()
        EngineRegistry.register(MockEngine, default=True)

        engine = get_engine()
        assert isinstance(engine, MockEngine)

        engine = get_engine("mock-engine")
        assert isinstance(engine, MockEngine)

    def test_list_engines_function(self):
        """Test the list_engines convenience function."""
        EngineRegistry.clear()
        EngineRegistry.register(MockEngine)
        EngineRegistry.register(AnotherMockEngine)

        engines = list_engines()
        assert "mock-engine" in engines
        assert "another-mock" in engines


class TestBuiltInEnginesRegistration:
    """Tests for built-in engine auto-registration."""

    def test_builtin_engines_registered(self):
        """Test that built-in engines are registered on import."""
        # Re-import to ensure registration happens
        from python_redlines import registry

        engines = EngineRegistry.list_engines()
        assert "openxml-powertools" in engines
        assert "docxodus" in engines

    def test_openxml_powertools_is_default(self):
        """Test that openxml-powertools is the default engine."""
        from python_redlines import registry

        default = EngineRegistry.get_default_engine_name()
        assert default == "openxml-powertools"
