"""Pytest configuration."""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("AI_API_KEY", "test-key")
