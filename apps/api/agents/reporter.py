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
            if analysis.get("status") == "error":
                md_content += f"### Error\n{analysis.get('summary', 'Unknown error occurred.')}\n"
            else:
                md_content += f"## Developer Score: {analysis.get('score', 'N/A')}/100\n\n"
                md_content += f"### Summary\n{analysis.get('summary', '')}\n\n"
                md_content += f"### Tech Stack\n"
                for tech in analysis.get('tech_stack', []):
                    md_content += f"- {tech}\n"
                md_content += f"\n### Deep Insights\n{analysis.get('raw_insights', '')}\n"
            
        elif report_type == "startup":
            if analysis.get("status") == "error":
                md_content += f"### Error\n{analysis.get('summary', 'Unknown error occurred.')}\n"
            else:
                md_content += f"### Executive Summary\n{analysis.get('summary', '')}\n\n"
                md_content += "### SWOT Analysis\n"
                swot = analysis.get('swot_analysis', {})
                md_content += f"**Strengths:** {', '.join(swot.get('strengths', []))}\n"
                md_content += f"**Weaknesses:** {', '.join(swot.get('weaknesses', []))}\n"
                md_content += f"**Opportunities:** {', '.join(swot.get('opportunities', []))}\n"
                md_content += f"**Threats:** {', '.join(swot.get('threats', []))}\n"

            
        elif report_type == "email":
            email = analysis.get("email", "Unknown")

            if analysis.get("status") == "invalid_email":
                md_content += f"# Input Validation Error\n\n"
                md_content += f"**Target Query:** `{email}`\n\n"
                md_content += f"> ⚠️ **Error:** {analysis.get('summary', 'Invalid email address.')}\n\n"
                md_content += f"Please verify the email format (e.g. `user@example.com`) and try again.\n"
                return md_content

            domain = analysis.get("domain", "")
            possible_name = analysis.get("possible_name")
            confidence_score = analysis.get("confidence_score", 0)
            categorization = analysis.get("categorization", "low")
            confidence_category = analysis.get("confidence_category", "no_evidence").upper()
            signals = analysis.get("signals_found", [])
            gravatar = analysis.get("gravatar", {})
            whois = analysis.get("whois", {})
            breaches = analysis.get("breaches", [])
            social_profiles = analysis.get("social_profiles", [])
            confirmed_accounts = analysis.get("confirmed_accounts", [])
            candidate_accounts = analysis.get("candidate_accounts", [])
            github_accounts = analysis.get("github_accounts", [])
            web_mentions = analysis.get("web_mentions", [])

            md_content += f"# Identity Intelligence & OSINT Report\n\n"
            md_content += f"**Target Email:** `{email}`\n\n"

            # Identity card
            md_content += "## Identity Summary\n\n"
            if possible_name:
                md_content += f"**Identified Name:** {possible_name}\n\n"
            if gravatar.get("avatar_url"):
                md_content += f"![Gravatar]({gravatar['avatar_url']} \"Gravatar Avatar\")\n\n"
            md_content += f"**Domain:** {domain}\n\n"
            md_content += f"**Confidence Tier:** `[{confidence_category}]` ({confidence_score}/100 — {categorization.capitalize()})\n\n"
            md_content += f"**Verified Signals:** {len(signals)}\n\n"

            # Signal badges
            if signals:
                md_content += "### Verified Signals Detected\n\n"
                signal_emojis = {
                    "gravatar_profile": "🟣 Gravatar Profile (Cryptographic MD5 match)",
                    "github_presence": "🟢 GitHub Presence (Exact commit / profile email match)",
                    "social_media_presence": "🔵 Social Media Presence (Verified mention)",
                    "web_mentions": "🌐 Web Mentions (Exact email match)",
                    "breach_records": "🔴 Breach Records (Verified dump entry)",
                    "news_mentions": "📰 News Mentions (Verified publication)",
                    "domain_registration": "🏢 Domain Registration (WHOIS record)",
                    "pgp_key": "🔐 OpenPGP Key (Public keyserver UID match)",
                    "pastebin_mentions": "📋 Pastebin Mentions (Public dump)",
                }
                for signal in signals:
                    emoji = signal_emojis.get(signal, f"• {signal}")
                    md_content += f"- {emoji}\n"
                md_content += "\n"

            # Analysis
            md_content += f"## Analyst Assessment\n\n{analysis.get('summary', '')}\n\n"

            # Confirmed Accounts Section
            md_content += "## Confirmed Accounts & Profiles (Verified/Probable)\n\n"
            has_confirmed_entries = False

            if gravatar.get("has_profile"):
                has_confirmed_entries = True
                md_content += f"### Gravatar Profile `[VERIFIED]`\n"
                md_content += f"- **Display Name:** {gravatar.get('display_name', 'Exists')}\n"
                if gravatar.get("evidence"):
                    md_content += f"- **Evidence:** {gravatar['evidence']}\n"
                if gravatar.get("profile_url"):
                    md_content += f"- **Link:** [{gravatar['profile_url']}]({gravatar['profile_url']})\n"
                md_content += "\n"

            if confirmed_accounts:
                has_confirmed_entries = True
                md_content += f"### GitHub Confirmed Accounts\n"
                for acc in confirmed_accounts:
                    login = acc.get("login", "unknown")
                    conf_cat = acc.get("confidence_category", "verified").upper()
                    profile_url = acc.get("profile_url", f"https://github.com/{login}")
                    evidence = acc.get("evidence", "Direct author email match.")
                    md_content += f"- `[{conf_cat}]` [{login}]({profile_url})\n  - *Evidence:* {evidence}\n"
                md_content += "\n"

            if whois.get("has_data") and whois.get("confidence_category") in ("verified", "probable"):
                has_confirmed_entries = True
                md_content += "### Domain Registration (WHOIS)\n"
                if whois.get("registrant_name"):
                    md_content += f"- **Registrant:** {whois['registrant_name']}\n"
                if whois.get("registrant_org"):
                    md_content += f"- **Organization:** {whois['registrant_org']}\n"
                if whois.get("registrant_email"):
                    md_content += f"- **Registrant Email:** {whois['registrant_email']}\n"
                if whois.get("created_date"):
                    md_content += f"- **Domain Created:** {whois['created_date']}\n"
                if whois.get("evidence"):
                    md_content += f"- **Evidence:** {whois['evidence']}\n"
                md_content += "\n"

            if not has_confirmed_entries:
                md_content += "*No directly confirmed accounts found for this email address.*\n\n"

            # Unverified Candidate Leads Section
            if candidate_accounts or any(not s.get("is_confirmed", False) for s in social_profiles):
                md_content += "## Candidate Leads & Inferred Handles (Unverified)\n\n"
                md_content += "> ℹ️ **Notice:** The following items are inferred handle matches or potential leads. They have **NOT** been verified to belong to the target email.\n\n"

                if candidate_accounts:
                    md_content += "### Candidate GitHub Accounts\n"
                    for acc in candidate_accounts:
                        login = acc.get("login", "unknown")
                        profile_url = acc.get("profile_url", f"https://github.com/{login}")
                        evidence = acc.get("evidence", "Username matches email prefix; no email link verified.")
                        md_content += f"- `[CANDIDATE]` [{login}]({profile_url}) — *{evidence}*\n"
                    md_content += "\n"

                for sp in social_profiles:
                    if not sp.get("is_confirmed", False):
                        platform = sp.get("platform", "Platform")
                        url = sp.get("url", "")
                        title = sp.get("title", "")
                        evidence = sp.get("evidence", "Platform handle match only.")
                        if url:
                            md_content += f"- `[CANDIDATE]` **{platform}:** [{title or platform}]({url}) — *{evidence}*\n"
                        else:
                            md_content += f"- `[CANDIDATE]` **{platform}:** {title or platform} — *{evidence}*\n"
                md_content += "\n"

            # Security Concerns (Breaches)
            if breaches:
                md_content += "## ⚠️ Security Exposure & Breaches\n\n"
                for b in breaches:
                    md_content += f"- `[VERIFIED]` **{b.get('name', 'Breach')}**"
                    if b.get("breach_date"):
                        md_content += f" ({b['breach_date']})"
                    if b.get("data_classes"):
                        md_content += f"\n  - Exposed Data: {', '.join(b['data_classes'])}"
                    if b.get("evidence"):
                        md_content += f"\n  - Evidence: {b['evidence']}"
                    md_content += "\n"
                md_content += "\n"

            # Web Mentions
            if web_mentions:
                md_content += "## Public Web Mentions\n\n"
                for wm in web_mentions[:5]:
                    title = wm.get("title", "Untitled")
                    url = wm.get("url", "")
                    if url:
                        md_content += f"- [{title}]({url})\n"
                    else:
                        md_content += f"- {title}\n"
                md_content += "\n"

            # Footer
            md_content += "---\n"
            md_content += f"*Identity intelligence synthesized by DevScout AI using strictly verified public OSINT sources.*\n"

                    
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
                    
        elif report_type == "reddit":
            if analysis.get("status") == "error":
                md_content += f"### Error\n{analysis.get('summary', 'Unknown error occurred.')}\n"
            else:
                md_content += f"### Community Sentiment: {analysis.get('sentiment', 'Unknown')}\n\n"
                md_content += f"### Summary\n{analysis.get('summary', '')}\n\n"
                md_content += "### Key Pain Points\n"
                for p in analysis.get('pain_points', []):
                    md_content += f"- {p}\n"
                md_content += "\n### Feature Requests & Ideas\n"
                for f in analysis.get('feature_requests', []):
                    md_content += f"- {f}\n"

        elif report_type == "idea":
            if analysis.get("status") == "error":
                md_content += f"### Error\n{analysis.get('summary', 'Unknown error occurred.')}\n"
            else:
                score = analysis.get('viability_score', 0)
                md_content += f"## Idea Viability Score: {score}/100\n\n"
                md_content += f"**Market Demand:** {analysis.get('market_demand', 'Unknown')}\n\n"
                md_content += f"### Summary\n{analysis.get('summary', '')}\n\n"
                md_content += "### Potential Competitors\n"
                for c in analysis.get('competitors', []):
                    md_content += f"- {c}\n"

        elif report_type == "social":
            md_content += f"### Global Sentiment: {analysis.get('global_sentiment', 'Unknown')}\n\n"
            md_content += f"### Overall Summary\n{analysis.get('overall_summary', '')}\n\n"
            md_content += f"#### Western Perspective (Twitter/Reddit/GitHub)\n{analysis.get('western_perspective', '')}\n\n"
            md_content += f"#### Eastern Perspective (Bilibili)\n{analysis.get('eastern_perspective', '')}\n"

        elif report_type == "npm":
            if analysis.get("status") == "error":
                md_content += f"### Error\n{analysis.get('summary', 'Unknown error occurred.')}\n"
            else:
                md_content += f"### Package: {analysis.get('name', 'Unknown')}\n"
                md_content += f"**Popularity:** {analysis.get('popularity_tier', 'N/A')}  |  **Reliability Index:** {analysis.get('reliability_index', 'N/A')}\n\n"
                md_content += f"### Summary\n{analysis.get('summary', '')}\n\n"
                md_content += f"### Primary Use Case\n{analysis.get('use_case', 'N/A')}\n"
            
        elif report_type == "linkedin":
            if analysis.get("status") == "error":
                md_content += f"### Error\n{analysis.get('summary', 'Unknown error occurred.')}\n"
            else:
                md_content += f"### Professional Summary\n{analysis.get('summary', '')}\n\n"
                md_content += f"**Experience Level:** {analysis.get('experience_level', 'Unknown')}\n\n"
                skills = analysis.get("skills", [])
                if skills:
                    md_content += "### Top Skills Detected\n"
                    for s in skills:
                        md_content += f"- {s}\n"

            
        elif report_type == "hackernews":
            if analysis.get("status") == "error":
                md_content += f"### Error\n{analysis.get('summary', 'Unknown error occurred.')}\n"
            else:
                md_content += f"## Global Sentiment: {analysis.get('sentiment', 'Unknown')}\n\n"
                md_content += f"### Summary\n{analysis.get('summary', '')}\n\n"
                md_content += "### Top Themes\n"
                for theme in analysis.get('top_themes', []):
                    md_content += f"- {theme}\n"
                md_content += "\n### Notable Discussions\n"
                for discussion in analysis.get('notable_discussions', []):
                    md_content += f"- {discussion}\n"

        elif report_type == "github-repo":
            if analysis.get("status") == "error":
                md_content += f"### Error\n{analysis.get('summary', 'Unknown error occurred.')}\n"
            else:
                md_content += f"## Repo Score: {analysis.get('health_score', 0)}/100\n\n"
                md_content += f"### Summary\n{analysis.get('summary', '')}\n\n"
                md_content += "### Tech Stack\n"
                raw_languages = analysis.get('languages', {})
                if raw_languages:
                    for lang, bytes_count in raw_languages.items():
                        md_content += f"- {lang}: {bytes_count:,} bytes\n"
                else:
                    primary = analysis.get('language', 'Unknown')
                    md_content += f"- {primary}\n"
                md_content += "\n### Top Contributors\n"
                for contrib in analysis.get('contributors', []):
                    md_content += f"- [{contrib.get('login', 'Unknown')}](https://github.com/{contrib.get('login', '')}) — {contrib.get('contributions', 0):,} commits\n"
                md_content += "\n### Key Insights\n"
                for insight in analysis.get('insights', []):
                    md_content += f"- {insight}\n"
                md_content += f"\n### Primary Use Case\n{analysis.get('primary_use_case', 'N/A')}\n"

        else:
            md_content += "Report generation for this type is not yet implemented.\n"
            md_content += str(analysis)

        return md_content
