from typing import Dict
from loguru import logger
import os
import json
from dotenv import load_dotenv

# Try to load google-generativeai for LLM analysis
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

load_dotenv()

# Configure Gemini if available
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if HAS_GENAI and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class AnalyzerAgent:
    """
    Analyzes real raw data gathered by the Researcher Agent.
    Uses LLMs (Gemini) if an API key is available, otherwise uses robust heuristics
    to calculate real metrics based on the fetched data (Zero mocks).
    """
    def __init__(self):
        self.use_llm = HAS_GENAI and bool(GEMINI_API_KEY)
        if self.use_llm:
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def analyze_developer(self, github_data: Dict) -> Dict:
        logger.info("Analyzing real developer profile data...")
        
        profile = github_data.get("profile", {})
        repos = github_data.get("recent_repos", [])
        
        # 1. Real Data Extraction
        name = profile.get("name") or profile.get("login", "Unknown User")
        bio = profile.get("bio", "No bio provided on GitHub.")
        followers = profile.get("followers", 0)
        public_repos = profile.get("public_repos", 0)
        
        total_stars = 0
        tech_counts = {}
        for repo in repos:
            # We fetch real stargazers count from the Agent Reach response
            total_stars += repo.get("stargazers_count", 0)
            lang = repo.get("language")
            if lang:
                tech_counts[lang] = tech_counts.get(lang, 0) + 1
                
        # Sort tech stack strictly by frequency of use in recent repos
        tech_stack = [lang for lang, count in sorted(tech_counts.items(), key=lambda item: item[1], reverse=True)]
        
        # Calculate a real base score (Heuristic based on actual metrics)
        # Baseline 50 + (stars * 2) + (followers * 1), capped at 99
        calculated_score = min(99, 50 + (total_stars * 2) + followers)
        if public_repos == 0:
            calculated_score = 0
        
        if self.use_llm:
            logger.info("Using Gemini LLM for Deep Developer Analysis")
            prompt = f"""
            Analyze the following real GitHub developer data and provide a professional summary and deep insights.
            Name: {name}
            Bio: {bio}
            Followers: {followers}
            Total Public Repos: {public_repos}
            Recent Repos Stars: {total_stars}
            Top Languages: {', '.join(tech_stack)}
            
            Return ONLY a valid JSON object with the following keys:
            - summary: A 2-sentence professional summary of this developer.
            - raw_insights: 3 bullet points of deep insights about their skills based on the languages and stats.
            """
            try:
                response = self.model.generate_content(prompt)
                res_text = response.text.replace('```json', '').replace('```', '').strip()
                llm_data = json.loads(res_text)
                
                return {
                    "score": calculated_score,
                    "tech_stack": tech_stack,
                    "summary": llm_data.get("summary", ""),
                    "raw_insights": llm_data.get("raw_insights", "")
                }
            except Exception as e:
                logger.error(f"LLM parsing failed: {e}. Falling back to strict data extraction.")

        # Fallback / No LLM Key provided
        logger.info("No Gemini API key found. Using strict heuristic analysis on real data.")
        return {
            "score": calculated_score,
            "tech_stack": tech_stack,
            "summary": f"{name} is a developer with {public_repos} public repos, {followers} followers, and {total_stars} stars across their most recent repositories.",
            "raw_insights": f"Bio provided: {bio}\n\nTop languages utilized: {', '.join(tech_stack) if tech_stack else 'None detected'}."
        }

    def analyze_startup(self, web_data: str) -> Dict:
        logger.info("Analyzing real startup website content...")
        
        # 1. Real Data Extraction (Limit length for processing to top 3000 chars)
        content_snippet = web_data[:3000] if web_data else "No content retrieved."
        
        if self.use_llm and web_data:
            logger.info("Using Gemini LLM for deep Startup SWOT Analysis")
            prompt = f"""
            Analyze the following real website content for a startup/company. 
            Extract a short summary and a SWOT analysis based ONLY on the provided text.
            
            Website Content:
            {content_snippet}
            
            Return ONLY a valid JSON object with the following structure:
            {{
                "summary": "1-2 sentence executive summary of what they do",
                "swot_analysis": {{
                    "strengths": ["point 1", "point 2"],
                    "weaknesses": ["point 1"],
                    "opportunities": ["point 1"],
                    "threats": ["point 1"]
                }}
            }}
            """
            try:
                response = self.model.generate_content(prompt)
                res_text = response.text.replace('```json', '').replace('```', '').strip()
                llm_data = json.loads(res_text)
                
                return {
                    "summary": llm_data.get("summary", "Could not parse summary."),
                    "swot_analysis": llm_data.get("swot_analysis", {})
                }
            except Exception as e:
                logger.error(f"LLM parsing failed: {e}. Falling back to strict data extraction.")

        # Fallback / No LLM Key provided
        logger.info("No Gemini API key found. Returning raw extracted text.")
        
        if not web_data:
            return {
                "swot_analysis": {
                    "strengths": [],
                    "weaknesses": ["Data Extraction Failed"],
                    "opportunities": ["Check if the URL is accessible or blocks bots"],
                    "threats": ["The target website took too long to respond or returned no text."]
                },
                "summary": "Error: Failed to extract text from the website. The site may be blocking bots or took too long to load."
            }
            
        return {
            "swot_analysis": {
                "strengths": ["Successfully ingested real text data via Agent Reach/Jina"],
                "weaknesses": ["No GEMINI_API_KEY provided in .env to generate AI SWOT analysis"],
                "opportunities": ["Add an API key to enable LLM-powered SWOT generation"],
                "threats": ["Displaying raw extracted text instead of synthesized points"]
            },
            "summary": f"Raw Extracted Text (First 300 chars): {content_snippet[:300]}..."
        }

    def analyze_email(self, email_data: Dict) -> Dict:
        logger.info("Analyzing email OSINT data...")
        email = email_data.get("email", "Unknown")
        gh_accounts = email_data.get("github_accounts", [])
        
        found = len(gh_accounts) > 0
        summary = f"OSINT scan complete for {email}."
        
        if found:
            summary += f" Found {len(gh_accounts)} associated GitHub account(s)."
        else:
            summary += " No public GitHub accounts or major developer footprints found for this exact email."

        if self.use_llm:
            prompt = f"""
            Act as an OSINT investigator. Analyze the following data found for the email {email}.
            GitHub Accounts Found: {json.dumps(gh_accounts)}
            
            Provide a short, professional summary of the digital footprint for this email address.
            Return ONLY a valid JSON object with a single "summary" key.
            """
            try:
                response = self.model.generate_content(prompt)
                res_text = response.text.replace('```json', '').replace('```', '').strip()
                llm_data = json.loads(res_text)
                summary = llm_data.get("summary", summary)
            except Exception as e:
                logger.error(f"LLM parsing failed for email analysis: {e}")

        return {
            "email": email,
            "footprint_found": found,
            "github_accounts": [acc.get("login") for acc in gh_accounts],
            "summary": summary
        }

    def analyze_youtube(self, yt_data: Dict) -> Dict:
        logger.info("Analyzing YouTube video data...")
        
        # 1. Real Data Extraction
        title = yt_data.get("title", "Unknown Title")
        channel = yt_data.get("uploader", "Unknown Channel")
        views = yt_data.get("view_count", 0)
        likes = yt_data.get("like_count", 0)
        description = yt_data.get("description", "No description provided.")
        tags = yt_data.get("tags", [])
        
        if not title or title == "Unknown Title":
            return {
                "status": "error",
                "summary": "Failed to extract video information. The video might be private, age-restricted, or invalid."
            }

        desc_snippet = description[:2000] # Limit for LLM context

        if self.use_llm:
            logger.info("Using Gemini LLM for deep YouTube Analysis")
            prompt = f"""
            Analyze the following YouTube video metadata.
            Title: {title}
            Channel: {channel}
            Views: {views}
            Tags: {', '.join(tags[:10])}
            Description:
            {desc_snippet}
            
            Return ONLY a valid JSON object with the following structure:
            {{
                "summary": "A 2-3 sentence summary of what this video is likely about based on the title and description.",
                "target_audience": "Who is this video for? (e.g., Beginners, Software Engineers, Gamers)"
            }}
            """
            try:
                response = self.model.generate_content(prompt)
                res_text = response.text.replace('```json', '').replace('```', '').strip()
                llm_data = json.loads(res_text)
                
                return {
                    "status": "success",
                    "title": title,
                    "channel": channel,
                    "metrics": {"views": views, "likes": likes},
                    "tags": tags[:10],
                    "summary": llm_data.get("summary", "Could not generate summary."),
                    "target_audience": llm_data.get("target_audience", "Unknown")
                }
            except Exception as e:
                logger.error(f"LLM parsing failed for youtube analysis: {e}")

        # Fallback without LLM
        return {
            "status": "success",
            "title": title,
            "channel": channel,
            "metrics": {"views": views, "likes": likes},
            "tags": tags[:10],
            "summary": f"Video titled '{title}' by {channel}. Description snippet: {description[:150]}...",
            "target_audience": "Requires LLM API Key to determine."
        }

    def analyze_reddit(self, reddit_data: Dict) -> Dict:
        logger.info("Analyzing Reddit OSINT data...")
        raw_text = reddit_data.get("raw_output", "")
        
        if not raw_text or len(raw_text.strip()) < 10:
            return {"status": "error", "summary": "Failed to extract sufficient Reddit data."}
            
        text_snippet = raw_text[:3000]

        if self.use_llm:
            logger.info("Using Gemini LLM for Reddit Analysis")
            prompt = f"""
            Analyze the following search results from Reddit regarding a specific topic.
            Identify user sentiment, common pain points, and potential feature requests.
            
            Reddit Search Results:
            {text_snippet}
            
            Return ONLY a valid JSON object with the following structure:
            {{
                "sentiment": "Positive/Neutral/Negative",
                "pain_points": ["point 1", "point 2"],
                "feature_requests": ["idea 1", "idea 2"],
                "summary": "2-3 sentence overview of the community discussion."
            }}
            """
            try:
                response = self.model.generate_content(prompt)
                res_text = response.text.replace('```json', '').replace('```', '').strip()
                return json.loads(res_text)
            except Exception as e:
                logger.error(f"LLM parsing failed for Reddit analysis: {e}")

        return {
            "sentiment": "Unknown (Needs LLM)",
            "pain_points": ["Raw data extracted successfully but requires LLM API key for processing"],
            "feature_requests": ["Add GEMINI_API_KEY to see actual insights"],
            "summary": f"Raw Output Snippet: {text_snippet[:200]}..."
        }

    def analyze_idea(self, idea_data: Dict) -> Dict:
        logger.info("Analyzing SaaS Idea Validation data...")
        raw_text = idea_data.get("raw_output", "")
        
        if not raw_text or len(raw_text.strip()) < 10:
            return {"status": "error", "summary": "Failed to extract market validation data."}
            
        text_snippet = raw_text[:3000]

        if self.use_llm:
            logger.info("Using Gemini LLM for Idea Validation")
            prompt = f"""
            Analyze the following web search results regarding a SaaS product idea.
            Identify market demand, potential competitors, and an overall viability score (1-100).
            
            Search Results:
            {text_snippet}
            
            Return ONLY a valid JSON object with the following structure:
            {{
                "viability_score": 80,
                "competitors": ["comp 1", "comp 2"],
                "market_demand": "High/Medium/Low",
                "summary": "2-3 sentence overview of the market viability."
            }}
            """
            try:
                response = self.model.generate_content(prompt)
                res_text = response.text.replace('```json', '').replace('```', '').strip()
                return json.loads(res_text)
            except Exception as e:
                logger.error(f"LLM parsing failed for Idea analysis: {e}")

        return {
            "viability_score": 0,
            "competitors": ["Needs LLM API Key to determine"],
            "market_demand": "Unknown",
            "summary": f"Raw Output Snippet: {text_snippet[:200]}..."
        }

    def analyze_social_tracker(self, tracker_data: Dict) -> Dict:
        logger.info("Analyzing cross-platform social tracking data...")
        keyword = tracker_data.get("keyword", "Unknown")
        
        if self.use_llm:
            logger.info("Using Gemini LLM for Social Tracking Analysis")
            prompt = f"""
            Analyze the following cross-platform social tracking data for the keyword: "{keyword}".
            You are comparing Western platforms (Twitter, Reddit, GitHub) against Eastern platforms (Bilibili) if data is available.
            
            Twitter Data: {tracker_data.get('twitter')}
            Reddit Data: {tracker_data.get('reddit')}
            GitHub Data: {tracker_data.get('github')}
            Bilibili Data: {tracker_data.get('bilibili')}
            
            Return ONLY a valid JSON object with the following structure:
            {{
                "global_sentiment": "Positive/Neutral/Negative",
                "western_perspective": "1-2 sentence summary of what Twitter/Reddit/GitHub users are saying.",
                "eastern_perspective": "1-2 sentence summary of what Bilibili users are saying (or 'No data available').",
                "overall_summary": "A brief conclusion on the global mindshare of this keyword."
            }}
            """
            try:
                response = self.model.generate_content(prompt)
                res_text = response.text.replace('```json', '').replace('```', '').strip()
                return json.loads(res_text)
            except Exception as e:
                logger.error(f"LLM parsing failed for social tracking analysis: {e}")

        # Fallback without LLM
        return {
            "global_sentiment": "Needs LLM",
            "western_perspective": f"Raw Data Snippet: {tracker_data.get('reddit', '')[:100]}...",
            "eastern_perspective": f"Raw Data Snippet: {tracker_data.get('bilibili', '')[:100]}...",
            "overall_summary": "Extracted raw data from multiple platforms but requires GEMINI_API_KEY for true synthesis."
        }
