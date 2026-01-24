"""
Engine registry for dynamic comparison engine selection.

This module provides a registry pattern for discovering and instantiating
comparison engines at runtime, allowing users to choose which backend
to use for document comparison.
"""

from typing import Dict, List, Optional, Type

from .base import ComparisonEngine


class EngineRegistry:
    """
    Registry for managing comparison engine implementations.

    The registry allows engines to be registered, discovered, and instantiated
    by name, enabling runtime selection of comparison backends.

    Example usage:
        # Get the default engine
        engine = EngineRegistry.get_engine()

        # Get a specific engine by name
        engine = EngineRegistry.get_engine('docxodus')

        # List available engines
        engines = EngineRegistry.list_available_engines()
    """

    _engines: Dict[str, Type[ComparisonEngine]] = {}
    _default_engine: Optional[str] = None

    @classmethod
    def register(
        cls,
        engine_class: Type[ComparisonEngine],
        default: bool = False
    ) -> None:
        """
        Register a comparison engine class.

        Args:
            engine_class: The engine class to register (must be a ComparisonEngine subclass)
            default: If True, set this as the default engine
        """
        # Create a temporary instance to get the name
        # We use a try/except since the engine might fail if binaries aren't available
        try:
            temp_instance = object.__new__(engine_class)
            # Call the name property getter directly without full initialization
            name = engine_class.name.fget(temp_instance)
        except Exception:
            # Fallback: use class name lowercased
            name = engine_class.__name__.lower().replace('engine', '')

        cls._engines[name] = engine_class

        if default or cls._default_engine is None:
            cls._default_engine = name

    @classmethod
    def get_engine(
        cls,
        name: Optional[str] = None,
        **kwargs
    ) -> ComparisonEngine:
        """
        Get an instance of a comparison engine.

        Args:
            name: Name of the engine to get. If None, returns the default engine.
            **kwargs: Additional arguments to pass to the engine constructor.

        Returns:
            An instance of the requested comparison engine.

        Raises:
            ValueError: If the requested engine is not registered.
            RuntimeError: If no engines are registered.
        """
        if not cls._engines:
            raise RuntimeError(
                "No comparison engines registered. "
                "Make sure the engines module is imported."
            )

        if name is None:
            name = cls._default_engine

        if name not in cls._engines:
            available = ', '.join(cls._engines.keys())
            raise ValueError(
                f"Unknown engine '{name}'. Available engines: {available}"
            )

        return cls._engines[name](**kwargs)

    @classmethod
    def list_engines(cls) -> List[str]:
        """
        List all registered engine names.

        Returns:
            List of registered engine names.
        """
        return list(cls._engines.keys())

    @classmethod
    def list_available_engines(cls) -> List[str]:
        """
        List engines that are actually available (binaries installed).

        Returns:
            List of available engine names.
        """
        available = []
        for name, engine_class in cls._engines.items():
            try:
                # Try to create instance without initializing binaries
                instance = engine_class.__new__(engine_class)
                # Manually set up the binary manager to check availability
                from .engines import BinaryManager
                from .__about__ import __version__

                if name == 'openxml-powertools':
                    manager = BinaryManager(
                        engine_name="XmlPowerTools",
                        dist_subdir="openxml-powertools",
                        binary_base_name="redlines",
                        version=__version__
                    )
                elif name == 'docxodus':
                    manager = BinaryManager(
                        engine_name="Docxodus",
                        dist_subdir="docxodus",
                        binary_base_name="redline",
                        version=__version__
                    )
                else:
                    # For other engines, try full instantiation
                    engine_class()
                    available.append(name)
                    continue

                if manager.is_available():
                    available.append(name)
            except Exception:
                pass

        return available

    @classmethod
    def get_default_engine_name(cls) -> Optional[str]:
        """
        Get the name of the default engine.

        Returns:
            Name of the default engine, or None if no engines registered.
        """
        return cls._default_engine

    @classmethod
    def set_default_engine(cls, name: str) -> None:
        """
        Set the default engine by name.

        Args:
            name: Name of the engine to set as default.

        Raises:
            ValueError: If the engine is not registered.
        """
        if name not in cls._engines:
            available = ', '.join(cls._engines.keys())
            raise ValueError(
                f"Unknown engine '{name}'. Available engines: {available}"
            )
        cls._default_engine = name

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered engines. Mainly useful for testing.
        """
        cls._engines.clear()
        cls._default_engine = None


def get_engine(name: Optional[str] = None, **kwargs) -> ComparisonEngine:
    """
    Convenience function to get a comparison engine instance.

    Args:
        name: Name of the engine to get. If None, returns the default engine.
              Available engines: 'openxml-powertools', 'docxodus'
        **kwargs: Additional arguments to pass to the engine constructor.

    Returns:
        An instance of the requested comparison engine.

    Example:
        # Get the default engine
        engine = get_engine()

        # Get a specific engine
        engine = get_engine('docxodus')

        # Compare documents
        redline_bytes, stdout, stderr = engine.compare(
            author="John Doe",
            original=original_bytes,
            modified=modified_bytes
        )
    """
    return EngineRegistry.get_engine(name, **kwargs)


def list_engines() -> List[str]:
    """
    List all registered comparison engine names.

    Returns:
        List of engine names (e.g., ['openxml-powertools', 'docxodus'])
    """
    return EngineRegistry.list_engines()


def list_available_engines() -> List[str]:
    """
    List comparison engines that have their binaries installed.

    Returns:
        List of available engine names.
    """
    return EngineRegistry.list_available_engines()


# Auto-register engines when this module is imported
def _auto_register_engines():
    """Register all known engines."""
    from .engines import XmlPowerToolsEngine, DocxodusEngine

    # Register XmlPowerToolsEngine as the default (for backward compatibility)
    EngineRegistry.register(XmlPowerToolsEngine, default=True)
    EngineRegistry.register(DocxodusEngine)


_auto_register_engines()
