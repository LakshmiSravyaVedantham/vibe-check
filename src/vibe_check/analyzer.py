"""Core analysis engine for vibe-check."""

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pathspec

from vibe_check.detectors.comments import DetectorResult
from vibe_check.detectors.comments import detect as detect_comments
from vibe_check.detectors.imports import detect as detect_imports
from vibe_check.detectors.naming import detect as detect_naming
from vibe_check.detectors.placeholders import detect as detect_placeholders
from vibe_check.detectors.ratio import detect as detect_ratio
from vibe_check.detectors.repetitive import detect as detect_repetitive
from vibe_check.detectors.security import detect as detect_security
from vibe_check.scoring import ScoreBreakdown, compute_vibe_score

# Files/directories to always skip
DEFAULT_IGNORE_PATTERNS = [
    ".git/",
    ".venv/",
    "venv/",
    "env/",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.egg-info/",
    "dist/",
    "build/",
    ".tox/",
    ".mypy_cache/",
    ".pytest_cache/",
    "*.min.js",
    "*.min.css",
    "node_modules/",
    ".DS_Store",
    "*.lock",
    "*.log",
]

# File extensions to analyze
SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".h",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".sh",
    ".bash",
}

# Max file size to analyze (bytes)
MAX_FILE_SIZE = 500 * 1024  # 500 KB


@dataclass
class FileResult:
    """Analysis result for a single file."""

    filepath: str
    relative_path: str
    score_breakdown: Optional[ScoreBreakdown] = None
    detector_results: Dict[str, DetectorResult] = field(default_factory=dict)
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: str = ""

    @property
    def vibe_score(self) -> int:
        """Return the final vibe score (0-100) or 0 if unavailable."""
        if self.score_breakdown:
            return self.score_breakdown.final_score
        return 0

    @property
    def all_findings(self) -> List[str]:
        """Collect all findings across all detectors."""
        findings = []
        for result in self.detector_results.values():
            findings.extend(result.findings)
        return findings


def _load_gitignore(path: Path) -> Optional[pathspec.PathSpec]:
    """Load .gitignore patterns from the given directory."""
    gitignore_path = path / ".gitignore"
    if not gitignore_path.exists():
        return None
    try:
        lines = gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return pathspec.PathSpec.from_lines("gitignore", lines)
    except Exception:
        return None


def _build_ignore_spec(base_path: Path, extra_patterns: List[str], use_gitignore: bool) -> pathspec.PathSpec:
    """Build a combined ignore spec from defaults, .gitignore, and extra patterns."""
    all_patterns = list(DEFAULT_IGNORE_PATTERNS)
    all_patterns.extend(extra_patterns)

    if use_gitignore:
        gitignore = _load_gitignore(base_path)
        if gitignore:
            all_patterns.extend(
                line
                for line in (base_path / ".gitignore").read_text(encoding="utf-8", errors="ignore").splitlines()
                if line.strip() and not line.startswith("#")
            )

    return pathspec.PathSpec.from_lines("gitignore", all_patterns)


def _should_skip_file(rel_path: str, ignore_spec: pathspec.PathSpec) -> bool:
    """Return True if the file should be skipped."""
    return ignore_spec.match_file(rel_path)


def _analyze_python_file(filepath: str, content: str) -> Dict[str, DetectorResult]:
    """Run all detectors on a Python file using its parsed AST."""
    try:
        tree: Optional[ast.AST] = ast.parse(content)
    except SyntaxError:
        tree = None

    results = {
        "repetitive": detect_repetitive(filepath, content, tree),
        "naming": detect_naming(filepath, content, tree),
        "comments": detect_comments(filepath, content, tree),
        "imports": detect_imports(filepath, content, tree),
        "placeholders": detect_placeholders(filepath, content, tree),
        "ratio": detect_ratio(filepath, content, tree),
        "security": detect_security(filepath, content, tree),
    }
    return results


def _analyze_generic_file(filepath: str, content: str) -> Dict[str, DetectorResult]:
    """Run text-based detectors on non-Python files."""
    results = {
        "repetitive": detect_repetitive(filepath, content, None),
        "naming": detect_naming(filepath, content, None),
        "comments": detect_comments(filepath, content, None),
        "imports": detect_imports(filepath, content, None),
        "placeholders": detect_placeholders(filepath, content, None),
        "ratio": detect_ratio(filepath, content, None),
        "security": detect_security(filepath, content, None),
    }
    return results


def analyze_file(filepath: str, base_path: Optional[str] = None) -> FileResult:
    """Analyze a single file and return a FileResult."""
    path = Path(filepath)

    if base_path:
        try:
            rel_path = str(path.relative_to(base_path))
        except ValueError:
            rel_path = filepath
    else:
        rel_path = path.name

    # Size check
    try:
        file_size = path.stat().st_size
    except OSError as e:
        return FileResult(filepath=filepath, relative_path=rel_path, error=str(e))

    if file_size == 0:
        return FileResult(filepath=filepath, relative_path=rel_path, skipped=True, skip_reason="empty file")

    if file_size > MAX_FILE_SIZE:
        return FileResult(
            filepath=filepath,
            relative_path=rel_path,
            skipped=True,
            skip_reason=f"file too large ({file_size // 1024}KB > {MAX_FILE_SIZE // 1024}KB)",
        )

    # Read content
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        return FileResult(filepath=filepath, relative_path=rel_path, error=str(e))

    if not content.strip():
        return FileResult(filepath=filepath, relative_path=rel_path, skipped=True, skip_reason="empty content")

    # Run appropriate detectors
    ext = path.suffix.lower()
    try:
        if ext == ".py":
            detector_results = _analyze_python_file(filepath, content)
        else:
            detector_results = _analyze_generic_file(filepath, content)
    except Exception as e:
        return FileResult(filepath=filepath, relative_path=rel_path, error=f"analysis error: {e}")

    # Compute score
    raw_scores = {name: result.score for name, result in detector_results.items()}
    score_breakdown = compute_vibe_score(raw_scores)

    return FileResult(
        filepath=filepath,
        relative_path=rel_path,
        score_breakdown=score_breakdown,
        detector_results=detector_results,
    )


def analyze_path(
    scan_path: str,
    threshold: int = 0,
    ignore_patterns: Optional[List[str]] = None,
    use_gitignore: bool = True,
) -> List[FileResult]:
    """
    Walk the given path and analyze all supported source files.

    Args:
        scan_path: Directory or file path to analyze
        threshold: Only return files with vibe score >= threshold
        ignore_patterns: Additional patterns to ignore
        use_gitignore: Whether to respect .gitignore files

    Returns:
        List of FileResult objects sorted by vibe score descending
    """
    path = Path(scan_path).resolve()
    extra_patterns = ignore_patterns or []

    # Handle single file
    if path.is_file():
        result = analyze_file(str(path), base_path=str(path.parent))
        if result.vibe_score >= threshold:
            return [result]
        return []

    if not path.is_dir():
        raise ValueError(f"Path does not exist: {scan_path}")

    ignore_spec = _build_ignore_spec(path, extra_patterns, use_gitignore)

    results: List[FileResult] = []

    for root, dirs, files in os.walk(str(path)):
        root_path = Path(root)

        # Filter out ignored directories in-place to prevent os.walk from descending
        dirs[:] = [d for d in dirs if not _should_skip_file(str((root_path / d).relative_to(path)) + "/", ignore_spec)]

        for filename in files:
            file_path = root_path / filename
            ext = file_path.suffix.lower()

            if ext not in SUPPORTED_EXTENSIONS:
                continue

            try:
                rel_path = str(file_path.relative_to(path))
            except ValueError:
                rel_path = filename

            if _should_skip_file(rel_path, ignore_spec):
                continue

            result = analyze_file(str(file_path), base_path=str(path))

            if result.skipped or result.error:
                results.append(result)
                continue

            if result.vibe_score >= threshold:
                results.append(result)

    # Sort by vibe score descending, with errors/skipped at end
    results.sort(key=lambda r: (0 if r.skipped or r.error else 1, r.vibe_score), reverse=True)
    return results
