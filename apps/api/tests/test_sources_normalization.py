import json
import pytest
from fastapi.testclient import TestClient

from main import app
from database import Report, SessionLocal, ensure_tables
from sources import SourceCollector
from agents.reporter import ReporterAgent
from agents.researcher import ResearcherAgent
from agents.email_osint import EmailOSINT


@pytest.fixture(autouse=True)
def setup_db():
    ensure_tables()
    yield
    db = SessionLocal()
    try:
        db.query(Report).filter(Report.job_id.like("test_src_%")).delete()
        db.commit()
    finally:
        db.close()


class TestSourceCollector:
    """Test core source collection, deduplication, and markdown generation."""

    def test_source_deduplication(self):
        collector = SourceCollector()
        s1 = collector.add_source(
            title="React Repo",
            url="https://github.com/facebook/react",
            platform="github",
            source_type="git_repository",
            snippet="React library"
        )
        assert s1["source_id"] == "1"

        # Add duplicate URL with different casing / whitespace
        s2 = collector.add_source(
            title="Duplicate React",
            url="https://github.com/facebook/react/",
            platform="github",
            source_type="git_repository"
        )
        assert s2["source_id"] == "1"

        # Add second distinct source
        s3 = collector.add_source(
            title="npm package",
            url="https://www.npmjs.com/package/react",
            platform="npm",
            source_type="package_registry"
        )
        assert s3["source_id"] == "2"

        sources = collector.get_sources()
        assert len(sources) == 2
        assert sources[0]["source_id"] == "1"
        assert sources[1]["source_id"] == "2"

    def test_sources_prompt_formatting(self):
        collector = SourceCollector()
        collector.add_source(
            title="GitHub Profile",
            url="https://github.com/torvalds",
            platform="github",
            source_type="user_profile",
            snippet="Creator of Linux"
        )
        prompt_text = collector.format_sources_for_prompt()
        assert "[1] GitHub Profile" in prompt_text
        assert "https://github.com/torvalds" in prompt_text
        assert "Creator of Linux" in prompt_text

    def test_sources_markdown_section_generation(self):
        collector = SourceCollector()
        collector.add_source(
            title="GitHub Repository: torvalds/linux",
            url="https://github.com/torvalds/linux",
            platform="github",
            source_type="git_repository",
            snippet="Linux kernel source tree"
        )
        collector.add_source(
            title="Linux Kernel Archives",
            url="https://kernel.org",
            platform="web",
            source_type="web_page",
            snippet="Official kernel release portal"
        )
        md = collector.format_markdown_sources_section()
        assert "## 📚 Sources & Verification" in md
        assert "| **[1]** |" in md
        assert "torvalds/linux" in md
        assert "[github.com/torvalds/linux]" in md
        assert "### 🔍 Source Snippets & Evidence" in md
        assert "Linux kernel source tree" in md


class TestAgentSourcesIntegration:
    """Test researcher agents and reporter integration with sources."""

    def test_reporter_appends_sources_section(self):
        reporter = ReporterAgent()
        analysis = {
            "status": "success",
            "score": 95,
            "summary": "High-performing open-source developer.",
            "tech_stack": ["Python", "Rust", "Go"],
            "raw_insights": "Active committer.",
            "sources": [
                {
                    "source_id": "1",
                    "title": "GitHub Profile: octocat",
                    "url": "https://github.com/octocat",
                    "platform": "github",
                    "source_type": "user_profile",
                    "snippet": "GitHub mascot and developer."
                },
                {
                    "source_id": "2",
                    "title": "GitHub API",
                    "url": "https://api.github.com/users/octocat",
                    "platform": "github",
                    "source_type": "rest_api"
                }
            ]
        }

        report_md = reporter.generate_markdown_report(analysis, "developer")
        assert "## 📚 Sources & Verification" in report_md
        assert "octocat" in report_md
        assert "https://github.com/octocat" in report_md

    def test_database_and_status_endpoint_stores_sources(self):
        client = TestClient(app)
        db = SessionLocal()
        job_id = "test_src_persistence_01"
        sample_sources = [
            {
                "source_id": "1",
                "title": "npm package: express",
                "url": "https://www.npmjs.com/package/express",
                "platform": "npm",
                "source_type": "package_registry",
                "snippet": "Fast, unopinionated, minimalist web framework"
            }
        ]

        try:
            job = Report(
                job_id=job_id,
                research_type="npm",
                query="express",
                status="completed",
                stage="completed",
                report_markdown="# npm Report: Express\n\n## 📚 Sources & Verification\n",
                sources=json.dumps(sample_sources)
            )
            db.add(job)
            db.commit()
        finally:
            db.close()

        res = client.get(f"/api/v1/research/status/{job_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["job_id"] == job_id
        assert "sources" in data
        assert len(data["sources"]) == 1
        assert data["sources"][0]["source_id"] == "1"
        assert data["sources"][0]["title"] == "npm package: express"
        assert data["sources"][0]["platform"] == "npm"
