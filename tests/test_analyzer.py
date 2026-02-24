"""Tests for the core analyzer module."""

import os
import textwrap

import pytest

from vibe_check.analyzer import FileResult, analyze_file, analyze_path


class TestAnalyzeFile:
    def test_analyze_clean_python_file(self, tmp_path, clean_code):
        filepath = tmp_path / "clean.py"
        filepath.write_text(clean_code)
        result = analyze_file(str(filepath), base_path=str(tmp_path))
        assert isinstance(result, FileResult)
        assert not result.error
        assert not result.skipped
        assert result.vibe_score >= 0
        assert result.vibe_score <= 100

    def test_analyze_returns_file_result_with_breakdown(self, tmp_path, security_issues_code):
        filepath = tmp_path / "bad.py"
        filepath.write_text(security_issues_code)
        result = analyze_file(str(filepath), base_path=str(tmp_path))
        assert result.score_breakdown is not None
        assert result.vibe_score > 0

    def test_skip_empty_file(self, tmp_path):
        filepath = tmp_path / "empty.py"
        filepath.write_text("")
        result = analyze_file(str(filepath))
        assert result.skipped

    def test_analyze_nonexistent_file(self, tmp_path):
        result = analyze_file(str(tmp_path / "nonexistent.py"))
        assert result.error is not None

    def test_analyze_javascript_file(self, tmp_path):
        code = textwrap.dedent(
            """
            function processData(data) {
                // TODO: implement
                var result = data;
                return result;
            }
        """
        )
        filepath = tmp_path / "test.js"
        filepath.write_text(code)
        result = analyze_file(str(filepath))
        assert not result.error
        assert result.vibe_score >= 0

    def test_relative_path_computed_correctly(self, tmp_path, clean_code):
        subdir = tmp_path / "src"
        subdir.mkdir()
        filepath = subdir / "module.py"
        filepath.write_text(clean_code)
        result = analyze_file(str(filepath), base_path=str(tmp_path))
        assert result.relative_path == os.path.join("src", "module.py")

    def test_all_findings_combines_detector_results(self, tmp_path, security_issues_code):
        filepath = tmp_path / "sec.py"
        filepath.write_text(security_issues_code)
        result = analyze_file(str(filepath))
        assert isinstance(result.all_findings, list)
        # Security issues should generate findings
        assert len(result.all_findings) > 0


class TestAnalyzePath:
    def test_scan_directory(self, tmp_path, clean_code, security_issues_code):
        (tmp_path / "clean.py").write_text(clean_code)
        (tmp_path / "bad.py").write_text(security_issues_code)
        results = analyze_path(str(tmp_path))
        assert len(results) >= 2
        paths = [r.relative_path for r in results]
        assert any("clean.py" in p for p in paths)
        assert any("bad.py" in p for p in paths)

    def test_threshold_filters_low_scores(self, tmp_path, clean_code):
        (tmp_path / "clean.py").write_text(clean_code)
        results = analyze_path(str(tmp_path), threshold=90)
        # clean code should not exceed threshold of 90
        for r in results:
            if not r.skipped and not r.error:
                assert r.vibe_score >= 90

    def test_results_sorted_by_score_descending(self, tmp_path, clean_code, security_issues_code):
        (tmp_path / "clean.py").write_text(clean_code)
        (tmp_path / "bad.py").write_text(security_issues_code)
        results = analyze_path(str(tmp_path))
        analyzed = [r for r in results if not r.skipped and not r.error]
        if len(analyzed) >= 2:
            scores = [r.vibe_score for r in analyzed]
            assert scores == sorted(scores, reverse=True)

    def test_scan_single_file(self, tmp_path, clean_code):
        filepath = tmp_path / "module.py"
        filepath.write_text(clean_code)
        results = analyze_path(str(filepath))
        assert len(results) == 1
        assert results[0].relative_path == "module.py"

    def test_invalid_path_raises_value_error(self):
        with pytest.raises(ValueError):
            analyze_path("/nonexistent/path/that/does/not/exist")

    def test_ignores_pycache(self, tmp_path, clean_code):
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "module.cpython-311.pyc").write_bytes(b"bytecode")
        (tmp_path / "real.py").write_text(clean_code)
        results = analyze_path(str(tmp_path))
        paths = [r.relative_path for r in results]
        assert not any("__pycache__" in p for p in paths)

    def test_extra_ignore_patterns(self, tmp_path, clean_code):
        (tmp_path / "module.py").write_text(clean_code)
        (tmp_path / "ignore_me.py").write_text(clean_code)
        results = analyze_path(str(tmp_path), ignore_patterns=["ignore_me.py"])
        paths = [r.relative_path for r in results]
        assert not any("ignore_me.py" in p for p in paths)
