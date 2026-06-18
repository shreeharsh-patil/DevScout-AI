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
            
        elif report_type == "email":
            md_content += f"### Email Footprint Analysis\n**Target:** {analysis.get('email', 'Unknown')}\n\n"
            md_content += f"**Status:** {'Footprint Found' if analysis.get('footprint_found') else 'No Major Footprint Detected'}\n\n"
            md_content += f"### Summary\n{analysis.get('summary', '')}\n\n"
            accounts = analysis.get('github_accounts', [])
            if accounts:
                md_content += "### Associated Public Developer Profiles\n"
                for acc in accounts:
                    md_content += f"- GitHub: [{acc}](https://github.com/{acc})\n"
                    
        elif report_type == "youtube":
            if analysis.get("status") == "error":
                md_content += f"### Error\n{analysis.get('summary', 'Unknown error occurred.')}\n"
            else:
                md_content += f"### Video: {analysis.get('title', 'Unknown')}\n"
                md_content += f"**Channel:** {analysis.get('channel', 'Unknown')}  |  **Views:** {analysis.get('metrics', {}).get('views', 0):,}\n\n"
                md_content += f"### Summary\n{analysis.get('summary', '')}\n\n"
                md_content += f"### Target Audience\n{analysis.get('target_audience', 'Unknown')}\n\n"
                
                tags = analysis.get('tags', [])
                if tags:
                    md_content += "### Key Tags\n"
                    md_content += ", ".join(tags) + "\n"
            
        else:
            md_content += "Report generation for this type is not yet implemented.\n"
            md_content += str(analysis)

        return md_content
