from loguru import logger
from typing import Dict
from .researcher import ResearcherAgent
from .analyzer import AnalyzerAgent
from .reporter import ReporterAgent

class AgentOrchestrator:
    """
    Coordinates the multi-agent system to run research jobs.
    Routes the query to the correct agents and synthesizes the report.
    """
    def __init__(self):
        self.researcher = ResearcherAgent()
        self.analyzer = AnalyzerAgent()
        self.reporter = ReporterAgent()

    def run_pipeline(self, query: str, research_type: str) -> Dict:
        logger.info(f"Orchestrator starting pipeline for {research_type}: {query}")
        
        raw_data = {}
        analysis = {}
        report = ""

        try:
            if research_type == "developer":
                # Assuming query is a github handle
                raw_data = self.researcher.fetch_github_profile(query)
                analysis = self.analyzer.analyze_developer(raw_data)
                report = self.reporter.generate_markdown_report(analysis, research_type)
                
            elif research_type == "startup":
                # Assuming query is a URL
                raw_data = {"website_text": self.researcher.fetch_web_page(query)}
                analysis = self.analyzer.analyze_startup(raw_data["website_text"])
                report = self.reporter.generate_markdown_report(analysis, research_type)
                
            elif research_type == "email":
                # Assuming query is an email address
                raw_data = self.researcher.search_email_osint(query)
                analysis = self.analyzer.analyze_email(raw_data)
                report = self.reporter.generate_markdown_report(analysis, research_type)
                
            elif research_type == "youtube":
                # Assuming query is a YouTube URL
                raw_data = self.researcher.fetch_youtube_info(query)
                analysis = self.analyzer.analyze_youtube(raw_data)
                report = self.reporter.generate_markdown_report(analysis, research_type)
                
            elif research_type == "reddit":
                raw_data = self.researcher.search_web_exa(f"site:reddit.com {query}", num_results=10)
                analysis = self.analyzer.analyze_reddit(raw_data)
                report = self.reporter.generate_markdown_report(analysis, research_type)
                
            elif research_type == "idea":
                raw_data = self.researcher.search_web_exa(f"{query} startup competitors market", num_results=10)
                analysis = self.analyzer.analyze_idea(raw_data)
                report = self.reporter.generate_markdown_report(analysis, research_type)
                
            elif research_type == "social":
                raw_data = self.researcher.search_social_tracker(query)
                analysis = self.analyzer.analyze_social_tracker(raw_data)
                report = self.reporter.generate_markdown_report(analysis, research_type)
            
            else:
                raise ValueError(f"Unsupported research type: {research_type}")

            logger.info("Pipeline completed successfully.")
            return {
                "status": "completed",
                "report": report,
                "raw_data": raw_data,
                "analysis": analysis
            }

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
