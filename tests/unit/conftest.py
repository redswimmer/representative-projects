import sys
from pathlib import Path

# The assertion file lives inside the promptfoo suite (hyphenated, non-package
# path), so make its directory importable for the tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "evals" / "extract-problems" / "asserts"))
