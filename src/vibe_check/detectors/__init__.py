"""Detector modules for vibe-check analysis."""

from vibe_check.detectors.comments import detect as detect_comments
from vibe_check.detectors.imports import detect as detect_imports
from vibe_check.detectors.naming import detect as detect_naming
from vibe_check.detectors.placeholders import detect as detect_placeholders
from vibe_check.detectors.ratio import detect as detect_ratio
from vibe_check.detectors.repetitive import detect as detect_repetitive
from vibe_check.detectors.security import detect as detect_security

__all__ = [
    "detect_comments",
    "detect_imports",
    "detect_naming",
    "detect_placeholders",
    "detect_ratio",
    "detect_repetitive",
    "detect_security",
]
