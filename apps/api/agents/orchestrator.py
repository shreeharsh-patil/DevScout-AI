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
                web_text = self.researcher.fetch_web_page(query)
                from sources import SourceCollector
                sc = SourceCollector()
                sc.add_source(
                    title=f"Startup Website: {query}",
                    url=query if query.startswith("http") else f"https://{query}",
                    platform="web",
                    source_type="web_page",
                    snippet=web_text[:300] if web_text else "Website content fetched."
                )
                raw_data = {"website_text": web_text, "sources": sc.get_sources()}
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_startup(raw_data["website_text"])
                analysis["sources"] = raw_data.get("sources", [])
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "email":
                raw_data = self.researcher.search_email_osint(query)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_email(raw_data)
                analysis["sources"] = raw_data.get("sources", [])
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "youtube":
                raw_data = self.researcher.fetch_youtube_info(query)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_youtube(raw_data)
                analysis["sources"] = raw_data.get("sources", [])
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "reddit":
                raw_data = self.researcher.search_web_exa(f"site:reddit.com {query}", num_results=10)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_reddit(raw_data)
                analysis["sources"] = raw_data.get("sources", [])
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "idea":
                raw_data = self.researcher.search_web_exa(f"{query} startup competitors market", num_results=10)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_idea(raw_data)
                analysis["sources"] = raw_data.get("sources", [])
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "social":
                raw_data = self.researcher.search_social_tracker(query)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_social_tracker(raw_data)
                analysis["sources"] = raw_data.get("sources", [])
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "linkedin":
                prof_text = self.researcher.fetch_linkedin_profile(query)
                from sources import SourceCollector
                sc = SourceCollector()
                sc.add_source(
                    title=f"LinkedIn Profile: {query}",
                    url=query if query.startswith("http") else f"https://{query}",
                    platform="linkedin",
                    source_type="profile_page",
                    snippet=prof_text[:300] if prof_text else "LinkedIn profile text."
                )
                raw_data = {"profile_text": prof_text, "sources": sc.get_sources()}
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_linkedin(raw_data["profile_text"])
                analysis["sources"] = raw_data.get("sources", [])
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "npm":
                raw_data = self.researcher.fetch_npm_package(query)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_npm(raw_data)
                analysis["sources"] = raw_data.get("sources", [])
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "hackernews":
                raw_data = self.researcher.search_web_exa(f"site:news.ycombinator.com {query}", num_results=10)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_hackernews(raw_data)
                analysis["sources"] = raw_data.get("sources", [])
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
                analysis["sources"] = raw_data.get("sources", [])
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            elif research_type == "repository":
                raw_data = self.researcher.fetch_repository_intelligence(query)
                _notify_stage("analyzing")
                analysis = self.analyzer.analyze_repository(raw_data)
                analysis["sources"] = raw_data.get("sources", [])
                _notify_stage("reporting")
                report = self.reporter.generate_markdown_report(analysis, research_type)

            else:
                raise ValueError(f"Unsupported research type: {research_type}")

            # Ensure sources are propagated
            sources = analysis.get("sources") or raw_data.get("sources") or []
            analysis["sources"] = sources

            _notify_stage("completed")
            logger.info("Pipeline completed successfully.")
            return {
                "status": "completed",
                "report": report,
                "raw_data": raw_data,
                "analysis": analysis,
                "sources": sources
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

