"""Tests for individual detector modules."""

import textwrap

from vibe_check.detectors.comments import detect as detect_comments
from vibe_check.detectors.imports import detect as detect_imports
from vibe_check.detectors.naming import detect as detect_naming
from vibe_check.detectors.placeholders import detect as detect_placeholders
from vibe_check.detectors.ratio import detect as detect_ratio
from vibe_check.detectors.repetitive import detect as detect_repetitive
from vibe_check.detectors.security import detect as detect_security


class TestNamingDetector:
    def test_detects_generic_variable_names(self, generic_naming_code):
        result = detect_naming("test.py", generic_naming_code)
        assert result.score > 0.0
        assert result.detector_name == "naming"
        assert any("generic variable" in f.lower() or "generic" in f.lower() for f in result.findings)

    def test_detects_generic_function_names(self):
        code = textwrap.dedent(
            """
            def process_data(x):
                return x

            def handle_request(req):
                return req
        """
        )
        result = detect_naming("test.py", code)
        assert result.score > 0.0
        assert any("process_data" in f or "handle_request" in f for f in result.findings)

    def test_clean_naming_has_low_score(self, clean_code):
        result = detect_naming("test.py", clean_code)
        assert result.score < 0.3

    def test_returns_zero_for_empty_file(self):
        result = detect_naming("test.py", "")
        assert result.score == 0.0

    def test_works_on_non_python_file(self):
        content = "var data = result;\nlet temp = output;"
        result = detect_naming("test.js", content)
        assert result.detector_name == "naming"


class TestCommentsDetector:
    def test_detects_obvious_comments(self, over_commented_code):
        result = detect_comments("test.py", over_commented_code)
        assert result.score > 0.0
        assert result.detector_name == "comments"
        assert len(result.findings) > 0

    def test_increment_counter_comment(self):
        code = "# increment counter\ncounter += 1\n"
        result = detect_comments("test.py", code)
        assert result.score > 0.0
        assert any("increment" in f.lower() for f in result.findings)

    def test_return_result_comment(self):
        code = "# return the result\nreturn result\n"
        result = detect_comments("test.py", code)
        assert result.score > 0.0

    def test_high_comment_density(self):
        code = "\n".join(
            [
                "# comment one",
                "x = 1",
                "# comment two",
                "y = 2",
                "# comment three",
                "z = 3",
                "# comment four",
                "a = 4",
                "# comment five",
                "b = 5",
                "# comment six",
                "c = 6",
                "# comment seven",
                "d = 7",
                "# comment eight",
                "e = 8",
                "# comment nine",
                "f = 9",
                "# comment ten",
                "g = 10",
            ]
        )
        result = detect_comments("test.py", code)
        assert result.score > 0.0

    def test_clean_code_has_low_comment_score(self, clean_code):
        result = detect_comments("test.py", clean_code)
        assert result.score < 0.4


class TestPlaceholderDetector:
    def test_detects_todo_comments(self, placeholder_code):
        result = detect_placeholders("test.py", placeholder_code)
        assert result.score > 0.0
        assert result.detector_name == "placeholders"
        assert any("TODO" in f for f in result.findings)

    def test_detects_empty_function_bodies(self):
        code = textwrap.dedent(
            """
            def foo():
                pass

            def bar():
                pass
        """
        )
        result = detect_placeholders("test.py", code)
        assert result.score > 0.0
        assert any("pass" in f.lower() or "empty" in f.lower() for f in result.findings)

    def test_detects_raise_not_implemented(self):
        code = textwrap.dedent(
            """
            def abstract_method(self):
                raise NotImplementedError("subclass must implement")

            def another_stub(self):
                raise NotImplementedError
        """
        )
        result = detect_placeholders("test.py", code)
        assert result.score > 0.0
        assert any("NotImplementedError" in f or "stub" in f.lower() for f in result.findings)

    def test_detects_fixme(self):
        code = "# FIXME: this is broken\nx = 1\n"
        result = detect_placeholders("test.py", code)
        assert result.score > 0.0

    def test_clean_code_has_low_placeholder_score(self, clean_code):
        result = detect_placeholders("test.py", clean_code)
        assert result.score == 0.0


class TestSecurityDetector:
    def test_detects_hardcoded_password(self):
        code = 'password = "super_secret_pass"\n'
        result = detect_security("test.py", code)
        assert result.score > 0.0
        assert result.detector_name == "security"
        assert any("password" in f.lower() for f in result.findings)

    def test_detects_eval(self):
        code = "result = eval(user_input)\n"
        result = detect_security("test.py", code)
        assert result.score > 0.0
        assert any("eval" in f.lower() for f in result.findings)

    def test_detects_subprocess_shell_true(self, security_issues_code):
        result = detect_security("test.py", security_issues_code)
        assert result.score > 0.0
        assert any("shell=True" in f or "subprocess" in f.lower() for f in result.findings)

    def test_detects_sql_injection(self):
        code = 'cursor.execute("SELECT * FROM users WHERE name = " + name)\n'
        result = detect_security("test.py", code)
        assert result.score > 0.0

    def test_clean_code_has_zero_security_score(self, clean_code):
        result = detect_security("test.py", clean_code)
        assert result.score == 0.0

    def test_skips_non_python_ast_checks(self):
        code = 'eval("something")\nexec("code")\n'
        result = detect_security("test.js", code)
        assert result.detector_name == "security"


class TestRepetitiveDetector:
    def test_detects_identical_function_structures(self, repetitive_code):
        result = detect_repetitive("test.py", repetitive_code)
        assert result.score > 0.0
        assert result.detector_name == "repetitive"

    def test_unique_functions_have_low_score(self, clean_code):
        result = detect_repetitive("test.py", clean_code)
        assert result.score < 0.5

    def test_returns_zero_for_single_function(self):
        code = textwrap.dedent(
            """
            def my_function(x):
                return x * 2
        """
        )
        result = detect_repetitive("test.py", code)
        assert result.score == 0.0

    def test_works_on_syntax_error_file(self):
        code = "def broken(\n    syntax error here {\n"
        result = detect_repetitive("test.py", code)
        assert result.score == 0.0
        assert result.detector_name == "repetitive"


class TestImportsDetector:
    def test_skips_non_python_files(self):
        result = detect_imports("test.js", "import something from 'somewhere'")
        assert result.score == 0.0
        assert result.detector_name == "imports"

    def test_stdlib_imports_are_safe(self):
        code = "import os\nimport sys\nimport json\nfrom pathlib import Path\n"
        result = detect_imports("test.py", code)
        assert result.score == 0.0

    def test_detects_suspicious_module_names(self):
        code = "import advanced_helper\nimport smart_utils\nimport magic_processor\n"
        result = detect_imports("test.py", code)
        assert result.score > 0.0
        assert any("suspicious" in f.lower() or "hallucinated" in f.lower() for f in result.findings)

    def test_known_third_party_packages_are_safe(self):
        code = "import requests\nimport flask\nimport numpy\nimport pandas\n"
        result = detect_imports("test.py", code)
        assert result.score == 0.0


class TestRatioDetector:
    def test_detects_high_docstring_ratio(self, high_ratio_code):
        result = detect_ratio("test.py", high_ratio_code)
        assert result.score > 0.0
        assert result.detector_name == "ratio"

    def test_detects_boilerplate_docstrings(self, high_ratio_code):
        result = detect_ratio("test.py", high_ratio_code)
        assert any("boilerplate" in f.lower() or "filler" in f.lower() for f in result.findings)

    def test_clean_code_has_low_ratio_score(self, clean_code):
        result = detect_ratio("test.py", clean_code)
        assert result.score < 0.3

    def test_empty_file_returns_zero(self):
        result = detect_ratio("test.py", "   \n   ")
        assert result.score == 0.0

    def test_non_python_file_with_high_comments(self):
        code = "\n".join(["// comment"] * 20 + ["x = 1", "y = 2"])
        result = detect_ratio("test.js", code)
        assert result.detector_name == "ratio"
