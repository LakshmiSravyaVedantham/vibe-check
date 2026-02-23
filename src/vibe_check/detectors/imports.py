"""Detector for hallucinated/non-existent imports in Python files."""

import ast
import importlib.util
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Set

# Well-known stdlib modules for Python 3.9+
STDLIB_MODULES: Set[str] = (
    set(sys.stdlib_module_names)
    if hasattr(sys, "stdlib_module_names")
    else {
        "abc",
        "aifc",
        "argparse",
        "array",
        "ast",
        "asynchat",
        "asyncio",
        "asyncore",
        "atexit",
        "audioop",
        "base64",
        "bdb",
        "binascii",
        "binhex",
        "bisect",
        "builtins",
        "bz2",
        "calendar",
        "cgi",
        "cgitb",
        "chunk",
        "cmath",
        "cmd",
        "code",
        "codecs",
        "codeop",
        "collections",
        "colorsys",
        "compileall",
        "concurrent",
        "configparser",
        "contextlib",
        "contextvars",
        "copy",
        "copyreg",
        "cProfile",
        "csv",
        "ctypes",
        "curses",
        "dataclasses",
        "datetime",
        "dbm",
        "decimal",
        "difflib",
        "dis",
        "doctest",
        "email",
        "encodings",
        "enum",
        "errno",
        "faulthandler",
        "fcntl",
        "filecmp",
        "fileinput",
        "fnmatch",
        "fractions",
        "ftplib",
        "functools",
        "gc",
        "getopt",
        "getpass",
        "gettext",
        "glob",
        "grp",
        "gzip",
        "hashlib",
        "heapq",
        "hmac",
        "html",
        "http",
        "idlelib",
        "imaplib",
        "importlib",
        "inspect",
        "io",
        "ipaddress",
        "itertools",
        "json",
        "keyword",
        "linecache",
        "locale",
        "logging",
        "lzma",
        "mailbox",
        "marshal",
        "math",
        "mimetypes",
        "mmap",
        "modulefinder",
        "multiprocessing",
        "netrc",
        "nis",
        "nntplib",
        "numbers",
        "operator",
        "os",
        "ossaudiodev",
        "pathlib",
        "pdb",
        "pickle",
        "pickletools",
        "pipes",
        "pkgutil",
        "platform",
        "plistlib",
        "poplib",
        "posix",
        "posixpath",
        "pprint",
        "profile",
        "pstats",
        "pty",
        "pwd",
        "py_compile",
        "pyclbr",
        "pydoc",
        "queue",
        "quopri",
        "random",
        "re",
        "readline",
        "reprlib",
        "resource",
        "rlcompleter",
        "runpy",
        "sched",
        "secrets",
        "select",
        "selectors",
        "shelve",
        "shlex",
        "shutil",
        "signal",
        "site",
        "smtpd",
        "smtplib",
        "sndhdr",
        "socket",
        "socketserver",
        "spwd",
        "sqlite3",
        "sre_compile",
        "sre_constants",
        "sre_parse",
        "ssl",
        "stat",
        "statistics",
        "string",
        "stringprep",
        "struct",
        "subprocess",
        "sunau",
        "symtable",
        "sys",
        "sysconfig",
        "syslog",
        "tabnanny",
        "tarfile",
        "telnetlib",
        "tempfile",
        "termios",
        "test",
        "textwrap",
        "threading",
        "time",
        "timeit",
        "tkinter",
        "token",
        "tokenize",
        "tomllib",
        "trace",
        "traceback",
        "tracemalloc",
        "tty",
        "turtle",
        "turtledemo",
        "types",
        "typing",
        "unicodedata",
        "unittest",
        "urllib",
        "uu",
        "uuid",
        "venv",
        "warnings",
        "wave",
        "weakref",
        "webbrowser",
        "winreg",
        "winsound",
        "wsgiref",
        "xdrlib",
        "xml",
        "xmlrpc",
        "zipapp",
        "zipfile",
        "zipimport",
        "zlib",
        "zoneinfo",
        "_thread",
    }
)

# Commonly known third-party packages that are safe to not flag
KNOWN_THIRD_PARTY: Set[str] = {
    "click",
    "rich",
    "pathspec",
    "requests",
    "flask",
    "django",
    "fastapi",
    "sqlalchemy",
    "pydantic",
    "numpy",
    "pandas",
    "matplotlib",
    "seaborn",
    "scikit-learn",
    "sklearn",
    "tensorflow",
    "torch",
    "keras",
    "scipy",
    "pytest",
    "black",
    "isort",
    "flake8",
    "pylint",
    "mypy",
    "setuptools",
    "wheel",
    "pip",
    "virtualenv",
    "celery",
    "redis",
    "boto3",
    "botocore",
    "paramiko",
    "cryptography",
    "jwt",
    "passlib",
    "bcrypt",
    "aiohttp",
    "httpx",
    "uvicorn",
    "gunicorn",
    "starlette",
    "alembic",
    "psycopg2",
    "pymysql",
    "motor",
    "pymongo",
    "elasticsearch",
    "loguru",
    "structlog",
    "attrs",
    "cattrs",
    "marshmallow",
    "cerberus",
    "voluptuous",
    "jsonschema",
    "arrow",
    "pendulum",
    "dateutil",
    "pytz",
    "babel",
    "pillow",
    "PIL",
    "lxml",
    "bs4",
    "beautifulsoup4",
    "scrapy",
    "selenium",
    "playwright",
    "yaml",
    "toml",
    "dotenv",
    "environ",
    "decouple",
    "dynaconf",
    "openai",
    "anthropic",
    "langchain",
    "transformers",
    "huggingface_hub",
    "tqdm",
    "colorama",
    "tabulate",
    "prettytable",
    "termcolor",
    "pytest_cov",
    "coverage",
    "hypothesis",
    "faker",
    "factory_boy",
    "mock",
    "responses",
    "httpretty",
    "vcrpy",
    "freezegun",
    "werkzeug",
    "jinja2",
    "mako",
    "chameleon",
    "itsdangerous",
    "stripe",
    "twilio",
    "sendgrid",
    "mailchimp",
    "slack_sdk",
    "google",
    "googleapiclient",
    "tweepy",
    "github",
    "gitlab",
    "docker",
    "kubernetes",
    "terraform",
    "ansible",
    "airflow",
    "prefect",
    "dagster",
    "luigi",
    "dask",
    "ray",
    "spark",
    "pyspark",
    "cv2",
    "skimage",
    "imageio",
    "moviepy",
    "nltk",
    "spacy",
    "gensim",
    "textblob",
    "sympy",
    "statsmodels",
    "xgboost",
    "lightgbm",
    "catboost",
}

# Patterns that are clearly hallucinated (AI makes these up frequently)
SUSPICIOUS_MODULE_PATTERNS = [
    "utils.helpers",
    "helpers.utils",
    "common.utils",
    "app.utils",
    "core.utils",
    "lib.utils",
    "tools.helpers",
    "utilities.common",
]


@dataclass
class DetectorResult:
    """Result from a single detector run."""

    score: float
    findings: List[str] = field(default_factory=list)
    detector_name: str = "unknown"


def _extract_imports(tree: ast.AST) -> List[str]:
    """Extract top-level module names from import statements."""
    module_names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Get root module name (e.g., "os.path" -> "os")
                root = alias.name.split(".")[0]
                module_names.append(root)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                module_names.append(root)
    return module_names


def _is_importable(module_name: str) -> bool:
    """Check if a module can be imported (is installed)."""
    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    except (ModuleNotFoundError, ValueError):
        return False


def _looks_hallucinated(module_name: str) -> bool:
    """Heuristic: does this module name look like something an AI would make up?"""
    name_lower = module_name.lower()

    # AI often invents modules with these patterns
    hallucination_patterns = [
        "advanced_",
        "smart_",
        "auto_",
        "magic_",
        "super_",
        "ultra_",
        "enhanced_",
        "improved_",
        "better_",
        "fast_utils",
        "easy_",
        "simple_",
        "quick_",
        "helper_module",
        "utility_module",
        "tools_module",
        "common_module",
        "shared_utils",
        "global_config",
        "app_config",
        "base_config",
        "project_utils",
        "project_helpers",
    ]
    return any(name_lower.startswith(pat) or name_lower.endswith(pat.rstrip("_")) for pat in hallucination_patterns)


def detect(filepath: str, content: str, ast_tree: Optional[ast.AST] = None) -> DetectorResult:
    """Detect hallucinated/non-existent imports in Python files."""
    findings: List[str] = []

    # Only meaningful for Python files
    if not filepath.endswith(".py"):
        return DetectorResult(score=0.0, findings=[], detector_name="imports")

    if ast_tree is None:
        try:
            ast_tree = ast.parse(content)
        except SyntaxError:
            return DetectorResult(score=0.0, findings=[], detector_name="imports")

    module_names = _extract_imports(ast_tree)
    if not module_names:
        return DetectorResult(score=0.0, findings=[], detector_name="imports")

    suspicious: List[str] = []
    unresolvable: List[str] = []

    for module in set(module_names):
        # Skip known safe modules
        if module in STDLIB_MODULES or module in KNOWN_THIRD_PARTY:
            continue
        # Skip relative imports (single dot)
        if not module:
            continue

        if _looks_hallucinated(module):
            suspicious.append(module)
        elif not _is_importable(module):
            # Could be a local module or hallucinated
            unresolvable.append(module)

    if suspicious:
        findings.append(f"Suspicious module names (likely hallucinated): {', '.join(sorted(suspicious))}")

    if unresolvable:
        findings.append(
            "Unresolvable imports (not in stdlib/known packages, may be local or hallucinated): "
            + ", ".join(sorted(unresolvable))
        )

    # Score: suspicious modules are a stronger signal than unresolvable ones
    total_imports = len(set(module_names))
    suspicious_ratio = len(suspicious) / total_imports if total_imports > 0 else 0.0
    unresolvable_ratio = len(unresolvable) / total_imports if total_imports > 0 else 0.0

    score = min(1.0, suspicious_ratio * 0.8 + unresolvable_ratio * 0.3)

    return DetectorResult(score=score, findings=findings, detector_name="imports")
