"""
Tests for the base comparison engine classes.
"""

import pytest
from pathlib import Path
from typing import Tuple, Optional, Union

from python_redlines.base import ComparisonEngine, ComparisonError


class TestComparisonError:
    """Tests for the ComparisonError exception class."""

    def test_comparison_error_message_only(self):
        """Test ComparisonError with just a message."""
        error = ComparisonError("Something went wrong")
        assert error.message == "Something went wrong"
        assert error.stdout is None
        assert error.stderr is None
        assert str(error) == "Something went wrong"

    def test_comparison_error_with_stdout(self):
        """Test ComparisonError with stdout."""
        error = ComparisonError("Error occurred", stdout="output here")
        assert error.message == "Error occurred"
        assert error.stdout == "output here"
        assert error.stderr is None
        assert "stdout: output here" in str(error)

    def test_comparison_error_with_stderr(self):
        """Test ComparisonError with stderr."""
        error = ComparisonError("Error occurred", stderr="error details")
        assert error.message == "Error occurred"
        assert error.stdout is None
        assert error.stderr == "error details"
        assert "stderr: error details" in str(error)

    def test_comparison_error_with_both_outputs(self):
        """Test ComparisonError with both stdout and stderr."""
        error = ComparisonError(
            "Comparison failed",
            stdout="some output",
            stderr="some error"
        )
        assert error.message == "Comparison failed"
        assert error.stdout == "some output"
        assert error.stderr == "some error"
        error_str = str(error)
        assert "Comparison failed" in error_str
        assert "stdout: some output" in error_str
        assert "stderr: some error" in error_str

    def test_comparison_error_is_exception(self):
        """Test that ComparisonError is a proper Exception."""
        error = ComparisonError("test")
        assert isinstance(error, Exception)

        with pytest.raises(ComparisonError) as exc_info:
            raise ComparisonError("raised error", stdout="out", stderr="err")

        assert exc_info.value.message == "raised error"


class TestComparisonEngineInterface:
    """Tests for the ComparisonEngine abstract base class interface."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that ComparisonEngine cannot be directly instantiated."""
        with pytest.raises(TypeError):
            ComparisonEngine()

    def test_subclass_must_implement_name(self):
        """Test that subclasses must implement the name property."""
        class IncompleteEngine(ComparisonEngine):
            @property
            def description(self) -> str:
                return "test"

            def compare(self, author, original, modified):
                pass

            def is_available(self) -> bool:
                return True

        with pytest.raises(TypeError):
            IncompleteEngine()

    def test_subclass_must_implement_description(self):
        """Test that subclasses must implement the description property."""
        class IncompleteEngine(ComparisonEngine):
            @property
            def name(self) -> str:
                return "test"

            def compare(self, author, original, modified):
                pass

            def is_available(self) -> bool:
                return True

        with pytest.raises(TypeError):
            IncompleteEngine()

    def test_subclass_must_implement_compare(self):
        """Test that subclasses must implement the compare method."""
        class IncompleteEngine(ComparisonEngine):
            @property
            def name(self) -> str:
                return "test"

            @property
            def description(self) -> str:
                return "test"

            def is_available(self) -> bool:
                return True

        with pytest.raises(TypeError):
            IncompleteEngine()

    def test_subclass_must_implement_is_available(self):
        """Test that subclasses must implement the is_available method."""
        class IncompleteEngine(ComparisonEngine):
            @property
            def name(self) -> str:
                return "test"

            @property
            def description(self) -> str:
                return "test"

            def compare(self, author, original, modified):
                pass

        with pytest.raises(TypeError):
            IncompleteEngine()

    def test_complete_subclass_can_be_instantiated(self):
        """Test that a complete subclass can be instantiated."""
        class CompleteEngine(ComparisonEngine):
            @property
            def name(self) -> str:
                return "complete-engine"

            @property
            def description(self) -> str:
                return "A complete test engine"

            def compare(
                self,
                author: str,
                original: Union[bytes, Path],
                modified: Union[bytes, Path]
            ) -> Tuple[bytes, Optional[str], Optional[str]]:
                return b"result", "stdout", None

            def is_available(self) -> bool:
                return True

        engine = CompleteEngine()
        assert engine.name == "complete-engine"
        assert engine.description == "A complete test engine"
        assert engine.is_available() is True

        result, stdout, stderr = engine.compare("author", b"orig", b"mod")
        assert result == b"result"
        assert stdout == "stdout"
        assert stderr is None
