from typing import Dict
from loguru import logger

class ReporterAgent:
    """
    Synthesizes the analyzed data into a final, shareable report.
    Generates Markdown and handles citation mapping.
    """
    def generate_markdown_report(self, analysis: Dict, report_type: str) -> str:
        logger.info(f"Generating {report_type} report...")
        md_content = f"# DevScout AI Research Report: {report_type.capitalize()}\n\n"
        
        if report_type == "developer":
            md_content += f"## Developer Score: {analysis.get('score', 'N/A')}/100\n\n"
            md_content += f"### Summary\n{analysis.get('summary', '')}\n\n"
            md_content += f"### Tech Stack\n"
            for tech in analysis.get('tech_stack', []):
                md_content += f"- {tech}\n"
            md_content += f"\n### Deep Insights\n{analysis.get('raw_insights', '')}\n"
            
        elif report_type == "startup":
            md_content += f"### Executive Summary\n{analysis.get('summary', '')}\n\n"
            md_content += "### SWOT Analysis\n"
            swot = analysis.get('swot_analysis', {})
            md_content += f"**Strengths:** {', '.join(swot.get('strengths', []))}\n"
            md_content += f"**Weaknesses:** {', '.join(swot.get('weaknesses', []))}\n"
            md_content += f"**Opportunities:** {', '.join(swot.get('opportunities', []))}\n"
            md_content += f"**Threats:** {', '.join(swot.get('threats', []))}\n"
            
        else:
            md_content += "Report generation for this type is not yet implemented.\n"
            md_content += str(analysis)

        return md_content
