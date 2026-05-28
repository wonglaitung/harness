"""
pytest configuration and fixtures for Harness tests.
"""

import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_python_file(temp_workspace):
    """Create a sample Python file for testing."""
    file_path = temp_workspace / "sample.py"
    file_path.write_text("""
def hello():
    return "Hello, World!"

def add(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
""")
    return file_path