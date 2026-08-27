from typing import Dict, Optional, Callable
from loguru import logger
from .researcher import ResearcherAgent
from .analyzer import AnalyzerAgent
from .reporter import ReporterAgent

_RATE_LIMITED_RESPONSE = {
    "status": "rate_limited",
    "error": "Gemini free tier rate limit hit. Wait 60 seconds and retry."
}


class AgentOrchestrator:
    """
    Coordinates the multi-agent system to run research jobs.
    Routes the query to the correct agents and synthesizes the report.
    Supports stage callbacks for real-time progress tracking.
    """
    def __init__(self):
        self.researcher = ResearcherAgent()
        self.analyzer = AnalyzerAgent()
        self.reporter = ReporterAgent()

    def run_pipeline(
        self,
        query: str,
        research_type: str,
        on_stage_change: Optional[Callable[[str], None]] = None
    ) -> Dict:
        logger.info(f"Orchestrator starting pipeline for {research_type}: {query}")
        
        def _notify_stage(stage: str):
            if on_stage_change:
                try:
                    on_stage_change(stage)
                except Exception as ex:
                    logger.warning(f"Failed to trigger stage callback for '{stage}': {ex}")

        raw_data = {}
        analysis = {}
        report = ""

        try:
            # 1. Research Phase
            _notify_stage("researching")
            
            if research_type == "developer":
                raw_data = self.researcher.fetch_github_profile(query)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_developer(raw_data)
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)
                
            elif research_type == "startup":
                raw_data = {"website_text": self.researcher.fetch_web_page(query)}
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_startup(raw_data["website_text"])
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)
                
            elif research_type == "email":
                raw_data = self.researcher.search_email_osint(query)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_email(raw_data)
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)
                
            elif research_type == "youtube":
                raw_data = self.researcher.fetch_youtube_info(query)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_youtube(raw_data)
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)
                
            elif research_type == "reddit":
                raw_data = self.researcher.search_web_exa(f"site:reddit.com {query}", num_results=10)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_reddit(raw_data)
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)
                
            elif research_type == "idea":
                raw_data = self.researcher.search_web_exa(f"{query} startup competitors market", num_results=10)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_idea(raw_data)
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "social":
                raw_data = self.researcher.search_social_tracker(query)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_social_tracker(raw_data)
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "linkedin":
                raw_data = {"profile_text": self.researcher.fetch_linkedin_profile(query)}
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_linkedin(raw_data["profile_text"])
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "npm":
                raw_data = self.researcher.fetch_npm_package(query)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_npm(raw_data)
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "hackernews":
                raw_data = self.researcher.search_web_exa(f"site:news.ycombinator.com {query}", num_results=10)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_hackernews(raw_data)
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "github-repo":
                raw_data = self.researcher.fetch_github_repo(query)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_github_repo(raw_data)
                if "error" not in raw_data:
                    analysis.setdefault("languages", raw_data.get("languages", {}))
                    analysis.setdefault("contributors", raw_data.get("contributors", []))
                    analysis.setdefault("language", raw_data.get("language", ""))
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "repository":
                # Comprehensive repository intelligence
                raw_data = self.researcher.fetch_repository_intelligence(query)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_repository(raw_data)
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            else:
                raise ValueError(f"Unsupported research type: {research_type}")

            _notify_stage("completed")
            logger.info("Pipeline completed successfully.")
            return {
                "status": "completed",
                "report": report,
                "raw_data": raw_data,
                "analysis": analysis
            }

        except RuntimeError as e:
            if str(e) == "RATE_LIMITED":
                logger.warning("Pipeline caught RATE_LIMITED signal from analyzer.")
                return _RATE_LIMITED_RESPONSE
            logger.error(f"Pipeline RuntimeError: {e}")
            return {"status": "failed", "error": str(e)}

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

