"""
Test suite for the Fluence CLI.

This package contains various tests for the Fluence CLI, including:
- Smoke tests: End-to-end tests of basic functionality
- Unit tests: Tests of individual components
"""

# Version of the test suite
__version__ = "0.1.0"

# Import commonly used testing utilities to make them available
import os
import sys
import json
import unittest
from pathlib import Path

# Add project root to path to make imports easier in test files
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))