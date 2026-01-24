"""
Abstract base class for document comparison engines.

This module provides the foundation for a pluggable comparison engine system,
allowing different backends (e.g., Open-Xml-PowerTools, Docxodus) to be used
interchangeably for generating redlined Word documents with tracked changes.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union, Tuple, Optional


class ComparisonEngine(ABC):
    """
    Abstract base class for document comparison engines.

    All comparison engines must implement the `compare` method which takes
    two Word documents and produces a redlined version with tracked changes.

    Example usage:
        engine = SomeComparisonEngine()
        redline_bytes, stdout, stderr = engine.compare(
            author="John Doe",
            original=original_doc_bytes,
            modified=modified_doc_bytes
        )
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the unique identifier name for this engine.

        Returns:
            str: Engine name (e.g., 'openxml-powertools', 'docxodus')
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Return a human-readable description of this engine.

        Returns:
            str: Description of the engine and its capabilities
        """
        pass

    @abstractmethod
    def compare(
        self,
        author: str,
        original: Union[bytes, Path],
        modified: Union[bytes, Path]
    ) -> Tuple[bytes, Optional[str], Optional[str]]:
        """
        Compare two Word documents and generate a redlined version with tracked changes.

        Args:
            author: The author name to attribute revisions to in the tracked changes.
            original: The original document, either as bytes or a Path to a .docx file.
            modified: The modified document, either as bytes or a Path to a .docx file.

        Returns:
            A tuple containing:
                - bytes: The redlined document as bytes
                - Optional[str]: Standard output from the comparison process (if any)
                - Optional[str]: Standard error from the comparison process (if any)

        Raises:
            FileNotFoundError: If a path is provided but the file doesn't exist.
            ComparisonError: If the comparison process fails.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this engine is available and properly configured.

        This method should verify that all required dependencies (e.g., binaries)
        are present and the engine can be used.

        Returns:
            bool: True if the engine is ready to use, False otherwise.
        """
        pass


class ComparisonError(Exception):
    """
    Exception raised when a document comparison fails.

    Attributes:
        message: Human-readable error message
        stdout: Standard output from the failed process (if available)
        stderr: Standard error from the failed process (if available)
    """

    def __init__(
        self,
        message: str,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self) -> str:
        parts = [self.message]
        if self.stdout:
            parts.append(f"stdout: {self.stdout}")
        if self.stderr:
            parts.append(f"stderr: {self.stderr}")
        return "\n".join(parts)
