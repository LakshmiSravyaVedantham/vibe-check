"""Detector for security anti-patterns common in AI-generated code."""

import ast
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Hardcoded secret patterns (regex)
HARDCODED_SECRET_PATTERNS: List[Tuple[str, str]] = [
    (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']', "Hardcoded password"),
    (r'(?i)(api_key|apikey|api_secret)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded API key"),
    (r'(?i)(secret_key|secret)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded secret key"),
    (r'(?i)(token|auth_token|access_token)\s*=\s*["\'][^"\']{10,}["\']', "Hardcoded token"),
    (r'(?i)(private_key|priv_key)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded private key"),
    (r'(?i)db_password\s*=\s*["\'][^"\']{3,}["\']', "Hardcoded database password"),
    (r'(?i)database_url\s*=\s*["\']postgresql://[^"\']+:[^@"\']+@', "Hardcoded database URL with credentials"),
    (r"(?i)mysql://\w+:\w+@", "Hardcoded MySQL connection string"),
    (r"(?i)mongodb://\w+:\w+@", "Hardcoded MongoDB connection string"),
    (r'(?i)(aws_access_key_id|aws_secret_access_key)\s*=\s*["\'][^"\']{16,}["\']', "Hardcoded AWS credentials"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID pattern"),
    (r"(?i)bearer\s+[a-z0-9\-_]{20,}", "Hardcoded Bearer token"),
    (r"(?i)basic\s+[a-z0-9+/=]{20,}", "Hardcoded Basic auth"),
    (r'(?i)(ssh_key|rsa_key)\s*=\s*["\']-----BEGIN', "Hardcoded RSA/SSH key"),
]

# Dangerous function calls
DANGEROUS_CALLS = [
    ("eval", "Use of eval() — code injection risk"),
    ("exec", "Use of exec() — code injection risk"),
    ("compile", "Use of compile() — potential code injection risk"),
    ("__import__", "Dynamic import with __import__() — potential injection risk"),
]

# SQL injection patterns
SQL_INJECTION_PATTERNS = [
    (r'(?i)execute\s*\(\s*["\'].*%s', "SQL query with %s string formatting"),
    (r'(?i)execute\s*\(\s*f["\'].*\{', "SQL query with f-string interpolation"),
    (r'(?i)execute\s*\(\s*["\'].*\+\s*\w', "SQL query with string concatenation"),
    (r'(?i)cursor\.execute\s*\(\s*"SELECT.*"\s*\+', "Direct SQL concatenation in cursor.execute"),
    (r'(?i)cursor\.execute\s*\(\s*f"', "F-string in cursor.execute"),
    (r'(?i)\.query\s*\(\s*f["\']', "F-string in .query()"),
    (r'(?i)raw\s*\(\s*f["\']', "F-string in raw() query"),
]


@dataclass
class DetectorResult:
    """Result from a single detector run."""

    score: float
    findings: List[str] = field(default_factory=list)
    detector_name: str = "unknown"


def _check_subprocess_shell(tree: ast.AST) -> List[str]:
    """Detect subprocess.call/run/Popen with shell=True."""
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Check for subprocess.call/run/Popen/check_call/check_output
        func = node.func
        is_subprocess_call = False

        if isinstance(func, ast.Attribute):
            if func.attr in ("call", "run", "Popen", "check_call", "check_output"):
                if isinstance(func.value, ast.Name) and func.value.id == "subprocess":
                    is_subprocess_call = True
        elif isinstance(func, ast.Name):
            if func.id in ("call", "Popen"):
                is_subprocess_call = True

        if is_subprocess_call:
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    findings.append("subprocess call with shell=True — command injection risk")
                    break

    return findings


def _check_eval_exec(tree: ast.AST) -> List[str]:
    """Detect direct eval() and exec() calls."""
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                findings.append(f"Direct use of {node.func.id}() — code execution from strings")
    return findings


def _check_pickle_loads(tree: ast.AST) -> List[str]:
    """Detect unsafe pickle.loads on untrusted data."""
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "loads":
                if isinstance(func.value, ast.Name) and func.value.id in ("pickle", "dill", "jsonpickle"):
                    findings.append(f"{func.value.id}.loads() — deserializing untrusted data is unsafe")
    return findings


def _check_assert_in_security_context(tree: ast.AST) -> List[str]:
    """Detect use of assert for input validation (can be disabled with -O flag)."""
    findings = []
    assert_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Assert))
    if assert_count > 5:
        findings.append(
            f"Heavy use of assert ({assert_count} times) for validation — "
            "assert statements can be disabled with Python -O flag"
        )
    return findings


def detect(filepath: str, content: str, ast_tree: Optional[ast.AST] = None) -> DetectorResult:
    """Detect security anti-patterns in the code."""
    findings: List[str] = []
    total_issues = 0

    # Text-based checks (work for all file types)
    for pattern, label in HARDCODED_SECRET_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            findings.append(f"SECURITY: {label} detected")
            total_issues += len(matches) * 3  # weighted heavily

    for pattern, label in SQL_INJECTION_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            findings.append(f"SECURITY: {label} ({len(matches)} instance(s))")
            total_issues += len(matches) * 2

    # AST-based checks for Python only
    if filepath.endswith(".py"):
        if ast_tree is None:
            try:
                ast_tree = ast.parse(content)
            except SyntaxError:
                score = min(1.0, total_issues * 0.1)
                return DetectorResult(score=score, findings=findings, detector_name="security")

        eval_findings = _check_eval_exec(ast_tree)
        for f in eval_findings:
            findings.append(f"SECURITY: {f}")
            total_issues += 2

        subprocess_findings = _check_subprocess_shell(ast_tree)
        for f in subprocess_findings:
            findings.append(f"SECURITY: {f}")
            total_issues += 2

        pickle_findings = _check_pickle_loads(ast_tree)
        for f in pickle_findings:
            findings.append(f"SECURITY: {f}")
            total_issues += 1

        assert_findings = _check_assert_in_security_context(ast_tree)
        for f in assert_findings:
            findings.append(f"SECURITY: {f}")
            total_issues += 1

    # Score: security issues have higher base penalty
    score = min(1.0, total_issues * 0.12)

    return DetectorResult(score=score, findings=findings, detector_name="security")
