"""Detector for repetitive/copy-paste code structures."""

import ast
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DetectorResult:
    """Result from a single detector run."""

    score: float  # 0.0 - 1.0
    findings: List[str] = field(default_factory=list)
    detector_name: str = "unknown"


def _function_structural_hash(node: ast.FunctionDef) -> str:
    """Create a structure fingerprint for a function ignoring variable names."""
    parts = []
    for child in ast.walk(node):
        parts.append(type(child).__name__)
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def _similarity_ratio(sig_a: str, sig_b: str) -> float:
    """Return a rough similarity ratio between two structural fingerprints."""
    if sig_a == sig_b:
        return 1.0
    # Compare by checking shared characters at each position
    matches = sum(a == b for a, b in zip(sig_a, sig_b))
    return matches / max(len(sig_a), len(sig_b))


def _get_function_arg_count(node: ast.FunctionDef) -> int:
    """Return number of arguments a function has."""
    return len(node.args.args)


def _get_function_body_types(node: ast.FunctionDef) -> List[str]:
    """Return a list of AST node type names for direct body children."""
    return [type(child).__name__ for child in node.body]


def detect(filepath: str, content: str, ast_tree: Optional[ast.AST] = None) -> DetectorResult:
    """Detect repetitive/copy-paste structures in Python files."""
    findings: List[str] = []

    if ast_tree is None:
        try:
            ast_tree = ast.parse(content)
        except SyntaxError:
            return DetectorResult(score=0.0, findings=[], detector_name="repetitive")

    # Collect all function definitions at all levels
    functions = [node for node in ast.walk(ast_tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]

    if len(functions) < 2:
        return DetectorResult(score=0.0, findings=[], detector_name="repetitive")

    structural_hashes = [_function_structural_hash(f) for f in functions]  # type: ignore[arg-type]

    # Count duplicate structural hashes
    hash_counts: dict = {}
    for h, f in zip(structural_hashes, functions):
        if h not in hash_counts:
            hash_counts[h] = []
        hash_counts[h].append(f.name)

    duplicate_groups = {h: names for h, names in hash_counts.items() if len(names) >= 2}
    total_duplicated = sum(len(names) for names in duplicate_groups.values())

    if duplicate_groups:
        for names in duplicate_groups.values():
            findings.append(f"Structurally identical functions: {', '.join(names)}")

    # Detect functions with suspiciously similar body statement patterns
    body_patterns = [tuple(_get_function_body_types(f)) for f in functions]  # type: ignore[arg-type]
    pattern_counts: dict = {}
    for pat, f in zip(body_patterns, functions):
        if pat not in pattern_counts:
            pattern_counts[pat] = []
        pattern_counts[pat].append(f.name)

    near_duplicate_patterns = {p: names for p, names in pattern_counts.items() if len(names) >= 3}
    for names in near_duplicate_patterns.values():
        msg = f"Functions with identical body statement patterns: {', '.join(names)}"
        if msg not in findings:
            findings.append(msg)

    # Detect repeated blocks of code (line-level duplicate detection)
    lines = content.splitlines()
    line_blocks: dict = {}
    block_size = 5
    for i in range(len(lines) - block_size):
        block = tuple(line.strip() for line in lines[i : i + block_size] if line.strip())
        if len(block) >= block_size:
            key = hashlib.md5("\n".join(block).encode()).hexdigest()
            if key not in line_blocks:
                line_blocks[key] = []
            line_blocks[key].append(i + 1)

    repeated_blocks = {k: positions for k, positions in line_blocks.items() if len(positions) >= 2}
    for positions in repeated_blocks.values():
        findings.append(f"Repeated code block found at lines: {positions}")

    # Score calculation
    duplicate_ratio = total_duplicated / len(functions) if functions else 0.0
    block_penalty = min(1.0, len(repeated_blocks) * 0.15)
    score = min(1.0, duplicate_ratio * 0.7 + block_penalty * 0.3)

    return DetectorResult(score=score, findings=findings, detector_name="repetitive")
