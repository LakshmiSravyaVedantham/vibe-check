"""Tests for the CLI commands."""

import json
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from vibe_check.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sample_repo(tmp_path):
    """Create a temporary repo with a mix of file quality."""
    clean = textwrap.dedent("""
        \"\"\"Clean module.\"\"\"
        from decimal import Decimal


        def calculate_tax(amount: Decimal, rate: Decimal) -> Decimal:
            \"\"\"Return the tax amount for the given amount and rate.\"\"\"
            return amount * rate
    """)

    vibed = textwrap.dedent("""
        password = "hardcoded_password_123"
        api_key = "sk-thisisaverylongfakekey123"

        def process_data(data, result, temp):
            # TODO: implement this properly
            # set the output
            output = data
            return output

        def handle_request(data):
            # TODO: fix this
            pass
    """)

    (tmp_path / "clean.py").write_text(clean)
    (tmp_path / "vibed.py").write_text(vibed)
    return tmp_path


class TestScanCommand:
    def test_scan_default_format(self, runner, sample_repo):
        result = runner.invoke(main, ["scan", str(sample_repo)])
        # Exit code 0 (no high risk) or 2 (high risk found) are both valid
        assert result.exit_code in (0, 2)
        assert "vibe-check" in result.output.lower() or "file" in result.output.lower()

    def test_scan_json_format(self, runner, sample_repo):
        result = runner.invoke(main, ["scan", str(sample_repo), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "summary" in data
        assert "files" in data
        assert data["summary"]["analyzed_files"] >= 1

    def test_scan_json_has_correct_structure(self, runner, sample_repo):
        result = runner.invoke(main, ["scan", str(sample_repo), "--format", "json"])
        data = json.loads(result.output)
        assert "scan_path" in data
        assert "timestamp" in data
        assert "summary" in data
        summary = data["summary"]
        assert "repo_vibe_score" in summary
        assert "average_score" in summary
        assert "high_risk_files" in summary

    def test_scan_html_format_writes_file(self, runner, sample_repo, tmp_path):
        output_file = str(tmp_path / "report.html")
        result = runner.invoke(main, ["scan", str(sample_repo), "--format", "html", "--output", output_file])
        assert result.exit_code == 0
        assert Path(output_file).exists()
        html_content = Path(output_file).read_text()
        assert "vibe-check" in html_content.lower()
        assert "<html" in html_content

    def test_scan_with_threshold(self, runner, sample_repo):
        result = runner.invoke(main, ["scan", str(sample_repo), "--format", "json", "--threshold", "50"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        for file_data in data["files"]:
            if not file_data.get("skipped") and not file_data.get("error"):
                assert file_data["vibe_score"] >= 50

    def test_scan_nonexistent_path(self, runner):
        result = runner.invoke(main, ["scan", "/nonexistent/path/that/does/not/exist"])
        assert result.exit_code != 0

    def test_scan_with_ignore_pattern(self, runner, sample_repo):
        result = runner.invoke(
            main,
            ["scan", str(sample_repo), "--format", "json", "--ignore", "vibed.py"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        paths = [f["path"] for f in data["files"]]
        assert not any("vibed.py" in p for p in paths)


class TestReportCommand:
    def test_report_generates_html(self, runner, sample_repo, tmp_path):
        output_file = str(tmp_path / "out.html")
        result = runner.invoke(main, ["report", str(sample_repo), "--output", output_file])
        assert result.exit_code == 0
        assert Path(output_file).exists()
        html_content = Path(output_file).read_text()
        assert "<!DOCTYPE html>" in html_content

    def test_report_default_output_filename(self, runner, sample_repo):
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["report", str(sample_repo)])
            assert result.exit_code == 0
            assert Path("vibe-check-report.html").exists()


class TestVersionCommand:
    def test_version_command(self, runner):
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "vibe-check" in result.output
        assert "0.1.0" in result.output

    def test_version_flag(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
