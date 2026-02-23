"""vibe-check: Detect how much of your codebase was vibe-coded by AI."""

__version__ = "0.1.0"
__author__ = "sravyalu"

from vibe_check.analyzer import FileResult, analyze_path
from vibe_check.scoring import compute_vibe_score

__all__ = [
    "__version__",
    "analyze_path",
    "FileResult",
    "compute_vibe_score",
]
