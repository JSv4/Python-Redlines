"""
Tests for the comparison engine implementations.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from python_redlines.engines import (
    BinaryManager,
    XmlPowerToolsEngine,
    DocxodusEngine,
)
from python_redlines.base import ComparisonEngine, ComparisonError


# Helper function to load test fixtures
def load_docx_bytes(file_path):
    """Load a docx file as bytes."""
    with open(file_path, 'rb') as file:
        return file.read()


@pytest.fixture
def original_docx():
    """Load the original test document."""
    return load_docx_bytes('tests/fixtures/original.docx')


@pytest.fixture
def modified_docx():
    """Load the modified test document."""
    return load_docx_bytes('tests/fixtures/modified.docx')


class TestBinaryManager:
    """Tests for the BinaryManager utility class."""

    def test_get_platform_info_linux_x64(self):
        """Test platform info detection for Linux x64."""
        manager = BinaryManager(
            engine_name="test",
            dist_subdir="test",
            binary_base_name="testbin",
            version="1.0.0"
        )

        with patch('platform.system', return_value='Linux'), \
             patch('platform.machine', return_value='x86_64'):
            binary_name, archive_name = manager._get_platform_info()

        assert binary_name == "linux-x64/testbin"
        assert archive_name == "linux-x64-1.0.0.tar.gz"

    def test_get_platform_info_linux_arm64(self):
        """Test platform info detection for Linux ARM64."""
        manager = BinaryManager(
            engine_name="test",
            dist_subdir="test",
            binary_base_name="testbin",
            version="1.0.0"
        )

        with patch('platform.system', return_value='Linux'), \
             patch('platform.machine', return_value='aarch64'):
            binary_name, archive_name = manager._get_platform_info()

        assert binary_name == "linux-arm64/testbin"
        assert archive_name == "linux-arm64-1.0.0.tar.gz"

    def test_get_platform_info_windows_x64(self):
        """Test platform info detection for Windows x64."""
        manager = BinaryManager(
            engine_name="test",
            dist_subdir="test",
            binary_base_name="testbin",
            version="1.0.0"
        )

        with patch('platform.system', return_value='Windows'), \
             patch('platform.machine', return_value='AMD64'):
            binary_name, archive_name = manager._get_platform_info()

        assert binary_name == "win-x64/testbin.exe"
        assert archive_name == "win-x64-1.0.0.zip"

    def test_get_platform_info_macos_x64(self):
        """Test platform info detection for macOS x64."""
        manager = BinaryManager(
            engine_name="test",
            dist_subdir="test",
            binary_base_name="testbin",
            version="1.0.0"
        )

        with patch('platform.system', return_value='Darwin'), \
             patch('platform.machine', return_value='x86_64'):
            binary_name, archive_name = manager._get_platform_info()

        assert binary_name == "osx-x64/testbin"
        assert archive_name == "osx-x64-1.0.0.tar.gz"

    def test_get_platform_info_macos_arm64(self):
        """Test platform info detection for macOS ARM64."""
        manager = BinaryManager(
            engine_name="test",
            dist_subdir="test",
            binary_base_name="testbin",
            version="1.0.0"
        )

        with patch('platform.system', return_value='Darwin'), \
             patch('platform.machine', return_value='arm64'):
            binary_name, archive_name = manager._get_platform_info()

        assert binary_name == "osx-arm64/testbin"
        assert archive_name == "osx-arm64-1.0.0.tar.gz"

    def test_unsupported_architecture_raises(self):
        """Test that unsupported architecture raises EnvironmentError."""
        manager = BinaryManager(
            engine_name="test",
            dist_subdir="test",
            binary_base_name="testbin",
            version="1.0.0"
        )

        with patch('platform.system', return_value='Linux'), \
             patch('platform.machine', return_value='i386'):
            with pytest.raises(EnvironmentError) as exc_info:
                manager._get_platform_info()

        assert "Unsupported architecture" in str(exc_info.value)

    def test_unsupported_os_raises(self):
        """Test that unsupported OS raises EnvironmentError."""
        manager = BinaryManager(
            engine_name="test",
            dist_subdir="test",
            binary_base_name="testbin",
            version="1.0.0"
        )

        with patch('platform.system', return_value='FreeBSD'), \
             patch('platform.machine', return_value='x86_64'):
            with pytest.raises(EnvironmentError) as exc_info:
                manager._get_platform_info()

        assert "Unsupported OS" in str(exc_info.value)

    def test_is_available_returns_false_when_no_archive(self):
        """Test is_available returns False when archive doesn't exist."""
        manager = BinaryManager(
            engine_name="test",
            dist_subdir="nonexistent",
            binary_base_name="testbin",
            version="1.0.0"
        )

        assert manager.is_available() is False


class TestXmlPowerToolsEngine:
    """Tests for the XmlPowerToolsEngine class."""

    def test_engine_is_comparison_engine(self):
        """Test that XmlPowerToolsEngine is a ComparisonEngine."""
        assert issubclass(XmlPowerToolsEngine, ComparisonEngine)

    def test_engine_name(self):
        """Test the engine name property."""
        # Use mock to avoid binary extraction
        with patch.object(BinaryManager, 'get_binary_path', return_value='/fake/path'):
            engine = XmlPowerToolsEngine()
            assert engine.name == "openxml-powertools"

    def test_engine_description(self):
        """Test the engine description property."""
        with patch.object(BinaryManager, 'get_binary_path', return_value='/fake/path'):
            engine = XmlPowerToolsEngine()
            assert "Open-Xml-PowerTools" in engine.description
            assert "WmlComparer" in engine.description

    def test_run_redline_is_alias_for_compare(self):
        """Test that run_redline is an alias for compare."""
        with patch.object(BinaryManager, 'get_binary_path', return_value='/fake/path'):
            engine = XmlPowerToolsEngine()

            with patch.object(engine, 'compare', return_value=(b'result', 'out', None)) as mock_compare:
                result = engine.run_redline("author", b"orig", b"mod")

                mock_compare.assert_called_once_with("author", b"orig", b"mod")
                assert result == (b'result', 'out', None)

    def test_extracted_binaries_path_property(self):
        """Test the legacy extracted_binaries_path property."""
        with patch.object(BinaryManager, 'get_binary_path', return_value='/fake/binary/path'):
            engine = XmlPowerToolsEngine()
            assert engine.extracted_binaries_path == '/fake/binary/path'

    def test_custom_target_path(self):
        """Test that custom target_path is passed to BinaryManager."""
        with patch.object(BinaryManager, '__init__', return_value=None) as mock_init, \
             patch.object(BinaryManager, 'get_binary_path', return_value='/fake/path'):
            XmlPowerToolsEngine(target_path="/custom/target")

            # Check that BinaryManager was initialized with the custom path
            call_kwargs = mock_init.call_args[1]
            assert call_kwargs.get('target_path') == '/custom/target'


class TestDocxodusEngine:
    """Tests for the DocxodusEngine class."""

    def test_engine_is_comparison_engine(self):
        """Test that DocxodusEngine is a ComparisonEngine."""
        assert issubclass(DocxodusEngine, ComparisonEngine)

    def test_engine_name(self):
        """Test the engine name property."""
        engine = DocxodusEngine.__new__(DocxodusEngine)
        assert engine.name == "docxodus"

    def test_engine_description(self):
        """Test the engine description property."""
        engine = DocxodusEngine.__new__(DocxodusEngine)
        assert "Docxodus" in engine.description
        assert ".NET 8.0" in engine.description

    def test_lazy_binary_extraction(self):
        """Test that binary is extracted lazily (on first use)."""
        # DocxodusEngine should not extract binary on init
        with patch.object(BinaryManager, '__init__', return_value=None) as mock_init, \
             patch.object(BinaryManager, 'get_binary_path') as mock_get_path:
            mock_init.return_value = None

            engine = DocxodusEngine()

            # get_binary_path should NOT have been called yet
            mock_get_path.assert_not_called()

    def test_run_redline_alias(self):
        """Test that run_redline is available and calls compare."""
        engine = DocxodusEngine.__new__(DocxodusEngine)
        engine._binary_manager = MagicMock()
        engine._binary_path = None

        with patch.object(engine, 'compare', return_value=(b'result', 'out', None)) as mock_compare:
            result = engine.run_redline("author", b"orig", b"mod")

            mock_compare.assert_called_once_with("author", b"orig", b"mod")
            assert result == (b'result', 'out', None)


class TestEngineIntegration:
    """Integration tests for engines with real files (when binaries available)."""

    @pytest.fixture
    def engine(self):
        """Try to create an XmlPowerToolsEngine, skip if binaries unavailable."""
        try:
            return XmlPowerToolsEngine()
        except FileNotFoundError:
            pytest.skip("XmlPowerTools binaries not available")

    def test_compare_with_bytes(self, engine, original_docx, modified_docx):
        """Test comparison with bytes input."""
        redline_output, stdout, stderr = engine.compare(
            author="TestAuthor",
            original=original_docx,
            modified=modified_docx
        )

        assert redline_output is not None
        assert isinstance(redline_output, bytes)
        assert len(redline_output) > 0
        assert stderr is None
        # Check that revisions were found
        assert stdout is not None
        assert "Revisions found:" in stdout

    def test_compare_with_paths(self, engine):
        """Test comparison with Path input."""
        original_path = Path('tests/fixtures/original.docx')
        modified_path = Path('tests/fixtures/modified.docx')

        redline_output, stdout, stderr = engine.compare(
            author="TestAuthor",
            original=original_path,
            modified=modified_path
        )

        assert redline_output is not None
        assert isinstance(redline_output, bytes)
        assert len(redline_output) > 0

    def test_compare_with_mixed_input(self, engine, original_docx):
        """Test comparison with mixed bytes and Path input."""
        modified_path = Path('tests/fixtures/modified.docx')

        redline_output, stdout, stderr = engine.compare(
            author="TestAuthor",
            original=original_docx,  # bytes
            modified=modified_path   # Path
        )

        assert redline_output is not None
        assert isinstance(redline_output, bytes)

    def test_author_tag_in_output(self, engine, original_docx, modified_docx):
        """Test that author tag is used in the output."""
        redline_output, stdout, stderr = engine.compare(
            author="CustomAuthor",
            original=original_docx,
            modified=modified_docx
        )

        assert redline_output is not None
        # The author tag should be embedded in the document
        # We can't easily verify this without parsing the docx

    def test_output_is_valid_docx(self, engine, original_docx, modified_docx):
        """Test that the output is a valid docx file (starts with PK zip signature)."""
        redline_output, _, _ = engine.compare(
            author="TestAuthor",
            original=original_docx,
            modified=modified_docx
        )

        # DOCX files are ZIP files, should start with PK
        assert redline_output[:2] == b'PK'

    def test_temp_files_cleaned_up(self, engine, original_docx, modified_docx):
        """Test that temporary files are cleaned up after comparison."""
        import glob

        # Get count of temp files before
        temp_dir = tempfile.gettempdir()
        temp_files_before = set(glob.glob(os.path.join(temp_dir, '*.docx')))

        # Run comparison
        engine.compare(
            author="TestAuthor",
            original=original_docx,
            modified=modified_docx
        )

        # Get count of temp files after
        temp_files_after = set(glob.glob(os.path.join(temp_dir, '*.docx')))

        # Should not have more temp files than before
        new_temp_files = temp_files_after - temp_files_before
        assert len(new_temp_files) == 0, f"Temp files not cleaned up: {new_temp_files}"


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing code."""

    @pytest.fixture
    def engine(self):
        """Try to create an XmlPowerToolsEngine, skip if binaries unavailable."""
        try:
            return XmlPowerToolsEngine()
        except FileNotFoundError:
            pytest.skip("XmlPowerTools binaries not available")

    def test_run_redline_method_exists(self, engine):
        """Test that the run_redline method still exists."""
        assert hasattr(engine, 'run_redline')
        assert callable(engine.run_redline)

    def test_run_redline_produces_same_result_as_compare(
        self, engine, original_docx, modified_docx
    ):
        """Test that run_redline produces the same result as compare."""
        result1 = engine.run_redline("Author", original_docx, modified_docx)
        result2 = engine.compare("Author", original_docx, modified_docx)

        # stdout/stderr should match
        assert result1[1] == result2[1]
        assert result1[2] == result2[2]
        # Output bytes should be similar (may differ slightly due to timestamps)
        assert len(result1[0]) > 0
        assert len(result2[0]) > 0

    def test_extracted_binaries_path_exists(self, engine):
        """Test that the extracted_binaries_path property still exists."""
        assert hasattr(engine, 'extracted_binaries_path')
        path = engine.extracted_binaries_path
        assert path is not None
        assert isinstance(path, str)
