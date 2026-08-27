import pytest
from agents.analyzer import AnalyzerAgent
from agents.reporter import ReporterAgent


class TestAnalyzersSafetyAndFallbacks:
    """Test that analyzers safely handle missing/empty data without fabricating conclusions."""

    def setup_method(self):
        self.analyzer = AnalyzerAgent()
        self.analyzer.use_llm = False
        self.reporter = ReporterAgent()

    def test_developer_analyzer_missing_data(self):
        # When profile is empty or missing login
        result = self.analyzer.analyze_developer({})
        assert result["status"] == "error"
        assert result["score"] == 0
        assert "not be found" in result["summary"] or "No public" in result["raw_insights"]

        report = self.reporter.generate_markdown_report(result, "developer")
        assert "Error" in report

    def test_startup_analyzer_empty_data(self):
        result = self.analyzer.analyze_startup("")
        assert result["status"] == "error"
        assert "unavailable" in result["summary"].lower() or "failed" in result["summary"].lower()

        report = self.reporter.generate_markdown_report(result, "startup")
        assert "Error" in report

    def test_youtube_analyzer_error_data(self):
        result = self.analyzer.analyze_youtube({"error": "Video private or unavailable"})
        assert result["status"] == "error"
        
        report = self.reporter.generate_markdown_report(result, "youtube")
        assert "Error" in report

    def test_reddit_analyzer_empty_data(self):
        result = self.analyzer.analyze_reddit({"raw_output": ""})
        assert result["status"] == "error"

        report = self.reporter.generate_markdown_report(result, "reddit")
        assert "Error" in report

    def test_idea_analyzer_empty_data(self):
        result = self.analyzer.analyze_idea({"raw_output": ""})
        assert result["status"] == "error"

        report = self.reporter.generate_markdown_report(result, "idea")
        assert "Error" in report

    def test_linkedin_analyzer_empty_data(self):
        result = self.analyzer.analyze_linkedin("")
        assert result["status"] == "error"
        assert "unavailable" in result["summary"].lower()

        report = self.reporter.generate_markdown_report(result, "linkedin")
        assert "Error" in report

    def test_npm_analyzer_missing_package(self):
        result = self.analyzer.analyze_npm({"error": "Package not found on npm registry."})
        assert result["status"] == "error"
        assert result["health_score"] == 0

        report = self.reporter.generate_markdown_report(result, "npm")
        assert "Error" in report

    def test_hackernews_analyzer_empty_data(self):
        result = self.analyzer.analyze_hackernews({"raw_output": ""})
        assert result["status"] == "error"

        report = self.reporter.generate_markdown_report(result, "hackernews")
        assert "Error" in report

    def test_github_repo_analyzer_error(self):
        result = self.analyzer.analyze_github_repo({"error": "Repository not found on GitHub."})
        assert result["status"] == "error"

        report = self.reporter.generate_markdown_report(result, "github-repo")
        assert "Error" in report
