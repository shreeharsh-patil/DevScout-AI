from typing import Dict, List
from loguru import logger
import os
import json
from dotenv import load_dotenv

# Try to load google-generativeai for LLM analysis
try:
    import google.generativeai as genai
    import google.api_core.exceptions
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

load_dotenv()

# Configure Gemini if available
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if HAS_GENAI and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Tech-stack keyword detection list (used in analyze_startup)
TECH_KEYWORDS = [
    "React", "Next.js", "Vue", "Angular", "Svelte", "Nuxt",
    "Python", "Django", "Flask", "FastAPI",
    "Node", "Express", "NestJS",
    "TypeScript", "JavaScript",
    "Ruby", "Rails",
    "Go", "Rust", "Java", "Kotlin", "Swift",
    "AWS", "GCP", "Azure", "Vercel", "Netlify", "Heroku",
    "Docker", "Kubernetes",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Supabase", "Firebase",
    "Stripe", "Shopify", "Twilio",
    "GraphQL", "REST", "gRPC",
    "TailwindCSS", "Bootstrap",
    "OpenAI", "Anthropic", "Gemini",
]


class AnalyzerAgent:
    """
    Analyzes real raw data gathered by the Researcher Agent.
    Uses LLMs (Gemini) if an API key is available, otherwise uses robust heuristics
    to calculate real metrics based on the fetched data (Zero mocks).
    """
    def __init__(self):
        self.use_llm = HAS_GENAI and bool(GEMINI_API_KEY)
        if self.use_llm:
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.model = None

    def _safe_generate(self, prompt: str) -> str:
        """
        Wraps model.generate_content with rate-limit detection.
        Raises RuntimeError('RATE_LIMITED') on ResourceExhausted.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except google.api_core.exceptions.ResourceExhausted:
            logger.warning("Gemini rate limit hit (ResourceExhausted).")
            raise RuntimeError("RATE_LIMITED")
        except Exception:
            raise

    def analyze_developer(self, github_data: Dict) -> Dict:
        logger.info("Analyzing real developer profile data...")
        
        profile = github_data.get("profile", {}) if isinstance(github_data, dict) else {}
        repos = github_data.get("recent_repos", []) if isinstance(github_data, dict) else []
        
        if not profile or not profile.get("login"):
            return {
                "status": "error",
                "summary": "GitHub user profile could not be found or retrieved.",
                "score": 0,
                "tech_stack": [],
                "raw_insights": "No public GitHub profile data available."
            }

        # 1. Real Data Extraction
        name = profile.get("name") or profile.get("login", "Unknown User")
        bio = profile.get("bio", "No bio provided on GitHub.")
        followers = profile.get("followers", 0)
        public_repos = profile.get("public_repos", 0)
        
        total_stars = 0
        tech_counts = {}
        for repo in repos:
            total_stars += repo.get("stargazers_count", 0)
            lang = repo.get("language")
            if lang:
                tech_counts[lang] = tech_counts.get(lang, 0) + 1
                
        # Sort tech stack strictly by frequency of use in recent repos
        tech_stack = [lang for lang, count in sorted(tech_counts.items(), key=lambda item: item[1], reverse=True)]
        
        # Calculate a real base score (Heuristic based on actual metrics)
        calculated_score = min(99, 50 + (total_stars * 2) + followers)
        if public_repos == 0:
            calculated_score = 0
        
        if self.use_llm:
            logger.info("Using Gemini LLM for Deep Developer Analysis")
            prompt = f"""
            Analyze the following real GitHub developer data and provide a professional summary and deep insights.
            CRITICAL ANTI-HALLUCINATION RULES:
            - Base all insights strictly on the languages, repository counts, stars, and bio provided below.
            - NEVER invent past employers, job titles, or skills not evidenced in this data.

            Name: {name}
            Bio: {bio}
            Followers: {followers}
            Total Public Repos: {public_repos}
            Recent Repos Stars: {total_stars}
            Top Languages: {', '.join(tech_stack) if tech_stack else 'None detected'}
            
            Return ONLY a valid JSON object with the following keys:
            - summary: A 2-sentence professional summary of this developer.
            - raw_insights: 3 bullet points of deep insights about their skills based on the languages and stats.
            """
            try:
                res_text = self._safe_generate(prompt)
                res_text = res_text.replace('```json', '').replace('```', '').strip()
                llm_data = json.loads(res_text)
                
                return {
                    "score": calculated_score,
                    "tech_stack": tech_stack,
                    "summary": llm_data.get("summary", ""),
                    "raw_insights": llm_data.get("raw_insights", "")
                }
            except RuntimeError as e:
                raise
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
        
        if not web_data or len(web_data.strip()) < 20:
            return {
                "status": "error",
                "summary": "Failed to extract website content. The site may be down, blocking automated access, or empty.",
                "swot_analysis": {
                    "strengths": [],
                    "weaknesses": ["Website content could not be retrieved."],
                    "opportunities": ["Verify domain connectivity."],
                    "threats": ["No public text data extracted."]
                },
                "tech_hints": []
            }

        # 1. Real Data Extraction (Limit length for processing to top 3000 chars)
        content_snippet = web_data[:3000]

        # Tech stack detection: scan raw text for known keywords
        tech_hints: List[str] = [kw for kw in TECH_KEYWORDS if kw.lower() in content_snippet.lower()]
        
        if self.use_llm and web_data:
            logger.info("Using Gemini LLM for deep Startup SWOT Analysis")
            prompt = f"""
            Analyze the following real website content for a startup/company. 
            Extract a short summary and a SWOT analysis based ONLY on the provided text.
            CRITICAL: Do NOT invent products, metrics, funding, or traction not explicitly mentioned in the text.
            
            Website Content:
            {content_snippet}
            
            Return ONLY a valid JSON object with the following structure:
            {{
                "summary": "1-2 sentence executive summary of what they do based strictly on the text",
                "swot_analysis": {{
                    "strengths": ["point 1", "point 2"],
                    "weaknesses": ["point 1"],
                    "opportunities": ["point 1"],
                    "threats": ["point 1"]
                }}
            }}
            """
            try:
                res_text = self._safe_generate(prompt)
                res_text = res_text.replace('```json', '').replace('```', '').strip()
                llm_data = json.loads(res_text)
                
                return {
                    "summary": llm_data.get("summary", "Could not parse summary."),
                    "swot_analysis": llm_data.get("swot_analysis", {}),
                    "tech_hints": tech_hints
                }
            except RuntimeError:
                raise
            except Exception as e:
                logger.error(f"LLM parsing failed: {e}. Falling back to strict data extraction.")

        # Fallback / No LLM Key provided
        logger.info("No Gemini API key found. Returning raw extracted text.")
        return {
            "swot_analysis": {
                "strengths": ["Successfully ingested text data via web extraction"],
                "weaknesses": ["No GEMINI_API_KEY provided in .env to generate AI SWOT analysis"],
                "opportunities": ["Add an API key to enable LLM-powered SWOT generation"],
                "threats": ["Displaying raw extracted text instead of synthesized points"]
            },
            "summary": f"Raw Extracted Text (First 300 chars): {content_snippet[:300]}...",
            "tech_hints": tech_hints
        }


    def analyze_email(self, email_data: Dict) -> Dict:
        logger.info("Analyzing comprehensive email identity profile...")
        email = email_data.get("email", "Unknown")

        # Handle validation failure directly
        if email_data.get("status") == "invalid_email":
            val_err = email_data.get("validation_error", "Malformed email address.")
            return {
                "email": email,
                "domain": "",
                "status": "invalid_email",
                "validation_error": val_err,
                "possible_name": None,
                "confidence_score": 0,
                "categorization": "none",
                "confidence_category": "no_evidence",
                "signals_found": [],
                "signal_count": 0,
                "summary": f"Input validation error: {val_err}. No OSINT scans were performed.",
                "gravatar": {"has_profile": False, "confidence_category": "no_evidence"},
                "whois": {"has_data": False, "confidence_category": "no_evidence"},
                "breaches": [],
                "web_mentions_count": 0,
                "web_mentions": [],
                "social_profiles": [],
                "news_mentions_count": 0,
                "news_mentions": [],
                "github_accounts": [],
                "confirmed_accounts": [],
                "candidate_accounts": [],
                "github_accounts_count": 0,
                "has_pgp_key": False,
                "pastebin_mentions_count": 0,
            }

        domain = email_data.get("domain", "")
        local = email_data.get("local_part", "")

        gravatar = email_data.get("gravatar", {})
        whois = email_data.get("whois", {})
        breaches = email_data.get("breaches", [])
        web_mentions = email_data.get("web_mentions", [])
        social_profiles = email_data.get("social_profiles", [])
        news_mentions = email_data.get("news_mentions", [])
        pgp_keys = email_data.get("pgp_keys", {})
        pastebin = email_data.get("pastebin", [])
        github = email_data.get("github", {})
        enrichment = email_data.get("data_enrichment", {})
        completeness = email_data.get("profile_completeness", {})

        confirmed_gh = github.get("confirmed_accounts", [])
        candidate_gh = github.get("candidate_accounts", [])
        all_gh = github.get("accounts", [])

        has_gravatar = gravatar.get("has_profile", False)
        has_breaches = len(breaches) > 0
        has_web = len(web_mentions) > 0
        has_social = len(social_profiles) > 0
        has_news = len(news_mentions) > 0
        has_confirmed_github = len(confirmed_gh) > 0
        has_whois = bool(whois.get("registrant_name") or whois.get("registrant_org"))
        has_pgp = pgp_keys.get("found", False)
        has_paste = len(pastebin) > 0

        possible_name = enrichment.get("possible_name")
        gravatar_name = gravatar.get("display_name")
        whois_name = whois.get("registrant_name")
        inferred_name = gravatar_name or whois_name or possible_name

        signals = completeness.get("verified_signals", [])
        confidence_score = completeness.get("score", 0)
        categorization = completeness.get("categorization", "low")
        confidence_category = completeness.get("confidence_category", "no_evidence")

        summary = f"Identity intelligence scan for {email}."
        if inferred_name and confidence_category in ("verified", "probable"):
            summary += f" Associated identity: {inferred_name}."
        elif inferred_name:
            summary += f" Possible name hint: {inferred_name} (unverified)."
        summary += f" Identified {len(signals)} verified public signal(s) ({confidence_category.capitalize()} confidence, {confidence_score}/100)."

        if self.use_llm and (has_confirmed_github or has_social or has_web or has_gravatar or has_breaches or candidate_gh):
            verified_summary = []
            if has_gravatar:
                verified_summary.append(f"Gravatar Profile: {gravatar.get('display_name', 'Exists')} (MD5 match)")
            if has_confirmed_github:
                verified_summary.append(f"Confirmed GitHub: {', '.join(a['login'] for a in confirmed_gh)} (Exact commit/profile email match)")
            if has_pgp:
                verified_summary.append(f"PGP Key: Verified UID match on public keyserver")
            if has_breaches:
                breach_names = [b.get("name", "Breach") for b in breaches[:3]]
                verified_summary.append(f"Data Breaches: {', '.join(breach_names)}")
            if has_whois:
                verified_summary.append(f"Domain WHOIS: {whois.get('registrant_name') or whois.get('registrant_org') or 'Registered'}")

            candidate_summary = []
            for c in candidate_gh:
                candidate_summary.append(f"GitHub handle '{c['login']}' (Guess from email prefix '{local}' — NO email match found)")

            prompt = f"""
            Act as a strict, evidence-based OSINT identity intelligence analyst.
            Analyze the following findings for the target email: {email}.

            CRITICAL SAFETY & GROUNDING RULES:
            1. STRICT EVIDENCE BOUNDARIES: Differentiate explicitly between CONFIRMED accounts (exact email match in commits, profile email, Gravatar MD5) and UNVERIFIED CANDIDATE LEADS (username guessed from email prefix).
            2. NEVER ASSERT GUESSES AS FACT: A username guessed from an email prefix must NEVER be described as an associated or confirmed account without verified proof.
            3. DO NOT FABRICATE: If a platform, metric, or profile was not discovered, state that it is unavailable. Never invent names, companies, handles, or URLs.
            4. Keep all summaries objective, factual, and strictly scoped to provided data.

            Target Email: {email}
            Domain: {domain}
            Inferred Name Hint: {inferred_name or "None"}
            Confidence Tier: {confidence_category.upper()} ({confidence_score}/100)

            Verified Findings:
            {chr(10).join('- ' + s for s in (verified_summary if verified_summary else ['None']))}

            Unverified Candidate Leads:
            {chr(10).join('- ' + s for s in (candidate_summary if candidate_summary else ['None']))}

            Return ONLY a valid JSON object with the following structure:
            {{
                "executive_summary": "2-3 sentence objective summary strictly citing verified findings",
                "likely_identity": "Verified name or 'Unconfirmed'",
                "key_findings": ["finding 1", "finding 2"],
                "candidate_notes": ["note 1 regarding candidate leads"] or [],
                "security_concerns": ["concern 1"] or [],
                "recommendation": "objective next steps",
                "identity_confidence": "Verified/Probable/Candidate/No Evidence"
            }}
            """
            try:
                res_text = self._safe_generate(prompt)
                res_text = res_text.replace('```json', '').replace('```', '').strip()
                llm_data = json.loads(res_text)
                llm_summary = llm_data.get("executive_summary", "")
                if llm_summary:
                    summary = llm_summary
            except RuntimeError as e:
                logger.warning(f"LLM rate limited for email analysis, using heuristic summary: {e}")
            except Exception as e:
                logger.error(f"LLM parsing failed for email analysis: {e}")

        return {
            "email": email,
            "domain": domain,
            "status": "valid",
            "possible_name": inferred_name,
            "confidence_score": confidence_score,
            "categorization": categorization,
            "confidence_category": confidence_category,
            "signals_found": signals,
            "signal_count": len(signals),
            "summary": summary,

            "gravatar": {
                "has_profile": has_gravatar,
                "display_name": gravatar.get("display_name"),
                "avatar_url": gravatar.get("avatar_url"),
                "profile_url": gravatar.get("profile_url"),
                "urls": gravatar.get("urls", []),
                "confidence_category": gravatar.get("confidence_category", "no_evidence"),
                "discovery_method": gravatar.get("discovery_method", "gravatar_md5_hash"),
                "evidence": gravatar.get("evidence", ""),
            },
            "whois": {
                "has_data": has_whois,
                "registrant_name": whois.get("registrant_name"),
                "registrant_org": whois.get("registrant_org"),
                "registrant_email": whois.get("registrant_email"),
                "created_date": whois.get("created_date"),
                "confidence_category": whois.get("confidence_category", "no_evidence"),
                "discovery_method": whois.get("discovery_method", "rdap_whois"),
                "evidence": whois.get("evidence", ""),
            },
            "breaches": [
                {
                    "name": b.get("name", "Unknown"),
                    "domain": b.get("domain", ""),
                    "breach_date": b.get("breach_date", ""),
                    "data_classes": b.get("data_classes", []),
                    "confidence_category": b.get("confidence_category", "verified"),
                    "discovery_method": b.get("discovery_method", "hibp"),
                    "evidence": b.get("evidence", ""),
                }
                for b in breaches
            ],
            "web_mentions_count": len(web_mentions),
            "web_mentions": web_mentions[:5],
            "social_profiles": [
                {
                    "platform": s.get("platform", "Unknown"),
                    "url": s.get("url", ""),
                    "title": s.get("title", ""),
                    "confidence_category": s.get("confidence_category", "candidate"),
                    "is_confirmed": s.get("is_confirmed", False),
                    "discovery_method": s.get("discovery_method", "targeted_social_search"),
                    "evidence": s.get("evidence", ""),
                }
                for s in social_profiles
            ],
            "news_mentions_count": len(news_mentions),
            "news_mentions": news_mentions[:3],
            "github_accounts": all_gh,
            "confirmed_accounts": confirmed_gh,
            "candidate_accounts": candidate_gh,
            "github_accounts_count": len(all_gh),
            "has_pgp_key": has_pgp,
            "pastebin_mentions_count": len(pastebin),
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

        desc_snippet = description[:2000]  # Limit for LLM context

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
                res_text = self._safe_generate(prompt)
                res_text = res_text.replace('```json', '').replace('```', '').strip()
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
            except RuntimeError:
                raise
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
                res_text = self._safe_generate(prompt)
                res_text = res_text.replace('```json', '').replace('```', '').strip()
                return json.loads(res_text)
            except RuntimeError:
                raise
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
                res_text = self._safe_generate(prompt)
                res_text = res_text.replace('```json', '').replace('```', '').strip()
                return json.loads(res_text)
            except RuntimeError:
                raise
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
            You are comparing Western platforms (Twitter, Reddit, GitHub, Hacker News) against Eastern platforms (Bilibili) if data is available.
            
            Twitter/HN Data: {tracker_data.get('twitter')}
            Reddit Data: {tracker_data.get('reddit')}
            GitHub Data: {tracker_data.get('github')}
            Hacker News Data: {tracker_data.get('hackernews')}
            Bilibili Data: {tracker_data.get('bilibili')}
            
            Return ONLY a valid JSON object with the following structure:
            {{
                "global_sentiment": "Positive/Neutral/Negative",
                "western_perspective": "1-2 sentence summary of what Twitter/Reddit/GitHub/HN users are saying.",
                "eastern_perspective": "1-2 sentence summary of what Bilibili users are saying (or 'No data available').",
                "overall_summary": "A brief conclusion on the global mindshare of this keyword."
            }}
            """
            try:
                res_text = self._safe_generate(prompt)
                res_text = res_text.replace('```json', '').replace('```', '').strip()
                return json.loads(res_text)
            except RuntimeError:
                raise
            except Exception as e:
                logger.error(f"LLM parsing failed for social tracking analysis: {e}")

        # Fallback without LLM
        return {
            "global_sentiment": "Needs LLM",
            "western_perspective": f"Raw Data Snippet: {tracker_data.get('reddit', '')[:100]}...",
            "eastern_perspective": f"Raw Data Snippet: {tracker_data.get('bilibili', '')[:100]}...",
            "overall_summary": "Extracted raw data from multiple platforms but requires GEMINI_API_KEY for true synthesis."
        }

    def analyze_npm_package(self, npm_data: Dict) -> Dict:
        logger.info("Analyzing npm package data...")
        name = npm_data.get("name", "Unknown")
        downloads = npm_data.get("weekly_downloads", 0)
        
        if self.use_llm:
            logger.info(f"Using Gemini LLM for npm analysis: {name}")
            prompt = f"""
            Analyze the following npm package metadata.
            Name: {name}
            Description: {npm_data.get('description')}
            Weekly Downloads: {downloads}
            Maintainers: {npm_data.get('maintainers_count')}
            
            Provide a professional analysis of this package's popularity, reliability, and use case.
            Return ONLY a valid JSON object with the following structure:
            {{
                "popularity_tier": "High/Medium/Low",
                "reliability_index": "1-100",
                "use_case": "What is this package best used for?",
                "summary": "2 sentence expert opinion."
            }}
            """
            try:
                response = self.model.generate_content(prompt)
                res_text = response.text.replace('```json', '').replace('```', '').strip()
                return json.loads(res_text)
            except Exception as e:
                logger.error(f"LLM parsing failed for npm analysis: {e}")

        return {
            "popularity_tier": "High" if downloads > 100000 else "Medium" if downloads > 1000 else "Low",
            "reliability_index": "N/A (Add API Key)",
            "use_case": "Extracted metadata available.",
            "summary": f"{name} has {downloads:,} weekly downloads. Description: {npm_data.get('description')[:100]}..."
        }

    def analyze_linkedin(self, profile_text: str) -> Dict:
        """Extracts structured data from a raw LinkedIn profile text."""
        logger.info("Analyzing LinkedIn profile text...")

        if not profile_text or len(profile_text.strip()) < 20:
            return {
                "status": "error",
                "summary": "LinkedIn profile data is unavailable (profile may be private, deleted, or blocked by authentication).",
                "skills": [],
                "experience_level": "Unavailable",
                "key_highlights": []
            }

        if self.use_llm and profile_text:
            logger.info("Using Gemini LLM for LinkedIn Profile Analysis")
            snippet = profile_text[:4000]
            prompt = f"""
            You are a professional recruiter. Analyze the following LinkedIn profile text and extract key information.
            CRITICAL: Rely strictly on the text provided below. Do not fabricate positions, companies, or credentials.

            LinkedIn Profile Text:
            {snippet}

            Return ONLY a valid JSON object with the following structure:
            {{
                "summary": "2-3 sentence professional summary of this person based strictly on the text.",
                "skills": ["skill1", "skill2", "skill3"],
                "experience_level": "Junior/Mid/Senior/Lead/Executive",
                "key_highlights": ["highlight 1", "highlight 2", "highlight 3"]
            }}
            """
            try:
                res_text = self._safe_generate(prompt)
                res_text = res_text.replace('```json', '').replace('```', '').strip()
                return json.loads(res_text)
            except RuntimeError:
                raise
            except Exception as e:
                logger.error(f"LLM parsing failed for LinkedIn analysis: {e}")

        # Fallback: return raw text snippet
        snippet = profile_text[:500]
        return {
            "summary": snippet,
            "skills": [],
            "experience_level": "Unknown (Needs LLM)",
            "key_highlights": ["Add GEMINI_API_KEY to .env for full LinkedIn analysis"]
        }

    def analyze_npm(self, npm_data: dict) -> Dict:
        """Summarizes an npm package's ecosystem health using Gemini."""
        logger.info("Analyzing npm package data...")

        if not npm_data or (isinstance(npm_data, dict) and npm_data.get("error")) or npm_data.get("name") in (None, "Unknown"):
            err_msg = npm_data.get("error", "Package not found on npm registry.") if isinstance(npm_data, dict) else "Package not found."
            return {
                "status": "error",
                "health_score": 0,
                "summary": err_msg,
                "popularity": "None",
                "maintenance_status": "Unknown",
                "recommendation": "Package not found or invalid."
            }

        if self.use_llm and npm_data:
            logger.info("Using Gemini LLM for npm Package Analysis")
            prompt = f"""
            Analyze the following npm package metadata and provide a health assessment.
            CRITICAL: Do not invent version history, download numbers, or maintainers not present in this metadata.

            Package Name: {npm_data.get('name')}
            Description: {npm_data.get('description')}
            Latest Version: {npm_data.get('version')}
            Weekly Downloads: {npm_data.get('weekly_downloads')}
            Repository: {npm_data.get('repository')}
            Maintainers Count: {npm_data.get('maintainers_count')}

            Return ONLY a valid JSON object with the following structure:
            {{
                "health_score": 75,
                "summary": "2-3 sentence overview of this package based on metadata.",
                "popularity": "High/Medium/Low",
                "maintenance_status": "Active/Moderate/Unmaintained",
                "recommendation": "Should developers use this package? Brief reasoning."
            }}
            """
            try:
                res_text = self._safe_generate(prompt)
                res_text = res_text.replace('```json', '').replace('```', '').strip()
                return json.loads(res_text)
            except RuntimeError:
                raise
            except Exception as e:
                logger.error(f"LLM parsing failed for npm analysis: {e}")

        # Fallback without LLM
        return {
            "health_score": 0,
            "summary": f"Package: {npm_data.get('name', 'Unknown')} v{npm_data.get('version', '?')} — {npm_data.get('description', 'No description')}",
            "popularity": "Unknown",
            "maintenance_status": "Unknown",
            "recommendation": "Add GEMINI_API_KEY to .env for AI-powered npm analysis."
        }

    def analyze_hackernews(self, hn_data: dict) -> dict:
        """Analyzes Hacker News search results for sentiment, themes, and notable discussions."""
        logger.info("Analyzing Hacker News data...")
        raw_text = hn_data.get("raw_output", "") if isinstance(hn_data, dict) else ""

        if not raw_text or len(raw_text.strip()) < 10:
            return {
                "status": "error",
                "summary": "No Hacker News discussions found for this topic.",
                "sentiment": "Neutral",
                "top_themes": [],
                "notable_discussions": []
            }

        text_snippet = raw_text[:3000]

        if self.use_llm:
            logger.info("Using Gemini LLM for Hacker News Analysis")
            prompt = f"""
            Analyze the following Hacker News search results for the given topic.
            Identify the overall community sentiment, recurring themes, and the most notable discussions.
            CRITICAL: Rely strictly on the provided HN excerpts. Do not invent discussions or viewpoints.

            Hacker News Results:
            {text_snippet}

            Return ONLY a valid JSON object with the following structure:
            {{
                "sentiment": "Positive/Neutral/Negative",
                "top_themes": ["theme 1", "theme 2", "theme 3"],
                "notable_discussions": ["discussion point 1", "discussion point 2", "discussion point 3"],
                "summary": "2-3 sentence overview of the HN community's perspective on this topic."
            }}
            """
            try:
                res_text = self._safe_generate(prompt)
                res_text = res_text.replace('```json', '').replace('```', '').strip()
                return json.loads(res_text)
            except RuntimeError:
                raise
            except Exception as e:
                logger.error(f"LLM parsing failed for HN analysis: {e}")

        # Fallback without LLM
        return {
            "sentiment": "Unknown (Needs LLM)",
            "top_themes": ["Raw data extracted successfully but requires LLM API key for processing"],
            "notable_discussions": ["Add GEMINI_API_KEY to see actual insights"],
            "summary": f"Raw Output Snippet: {text_snippet[:200]}..."
        }

    def analyze_github_repo(self, repo_data: dict) -> dict:
        """Analyzes a GitHub repository for health score, summary, and key insights."""
        logger.info(f"Analyzing GitHub repo: {repo_data.get('name', 'Unknown') if isinstance(repo_data, dict) else 'Unknown'}")

        if not repo_data or not isinstance(repo_data, dict) or repo_data.get("error") or not repo_data.get("name"):
            return {
                "status": "error",
                "summary": repo_data.get("error", "GitHub repository could not be found or retrieved.") if isinstance(repo_data, dict) else "Repository not found."
            }

        stars = repo_data.get("stars", 0)
        forks = repo_data.get("forks", 0)
        open_issues = repo_data.get("open_issues", 0)

        # Heuristic health score (used as fallback and as base for LLM)
        heuristic_score = min(99, stars // 100 + forks // 20 + (10 if open_issues < 100 else 0))

        if self.use_llm:
            logger.info("Using Gemini LLM for GitHub Repo Analysis")
            prompt = f"""
            Analyze the following GitHub repository data and provide a professional assessment.
            CRITICAL: Base your analysis strictly on the repository metrics and languages provided below. Do not invent contributors or features.

            Repository: {repo_data.get('name')}
            Description: {repo_data.get('description')}
            Stars: {stars}
            Forks: {forks}
            Open Issues: {open_issues}
            Watchers: {repo_data.get('watchers')}
            Primary Language: {repo_data.get('language')}
            Topics: {', '.join(repo_data.get('topics', []))}
            License: {repo_data.get('license')}
            Created: {repo_data.get('created_at')}
            Last Push: {repo_data.get('pushed_at')}
            Languages: {json.dumps(repo_data.get('languages', {}))}
            Top Contributors: {json.dumps(repo_data.get('contributors', []))}

            Return ONLY a valid JSON object with the following structure:
            {{
                "summary": "2-3 sentence professional summary of this repository.",
                "health_score": 75,
                "insights": ["insight 1", "insight 2", "insight 3"],
                "primary_use_case": "What is this repository primarily used for?"
            }}
            """
            try:
                res_text = self._safe_generate(prompt)
                res_text = res_text.replace('```json', '').replace('```', '').strip()
                return json.loads(res_text)
            except RuntimeError:
                raise
            except Exception as e:
                logger.error(f"LLM parsing failed for GitHub repo analysis: {e}")

        # Fallback without LLM
        top_lang = repo_data.get('language', 'Unknown')
        return {
            "summary": (
                f"{repo_data.get('name', 'This repository')} is a {top_lang} project with "
                f"{stars:,} stars and {forks:,} forks. "
                f"{repo_data.get('description', 'No description provided.')}"
            ),
            "health_score": heuristic_score,
            "insights": [
                f"Primary language: {top_lang}",
                f"Open issues: {open_issues} — {'well maintained' if open_issues < 100 else 'active backlog'}",
                f"License: {repo_data.get('license', 'None specified')}",
            ],
            "primary_use_case": "Add GEMINI_API_KEY to .env for AI-powered use case analysis."
        }

    def analyze_repository(self, repo_data: dict) -> dict:
        """
        Comprehensive repository analysis using ONLY retrieved data.
        Uses a transparent, deterministic scoring formula.
        No metrics are invented — every statement derives from collected data.
        """
        logger.info(f"Analyzing repository: {repo_data.get('name', 'Unknown') if isinstance(repo_data, dict) else 'Unknown'}")

        if not repo_data or not isinstance(repo_data, dict) or repo_data.get("error") or not repo_data.get("name"):
            return {
                "status": "error",
                "summary": repo_data.get("error", "Repository not found.") if isinstance(repo_data, dict) else "Repository not found."
            }

        # ── Extract all raw metrics ──
        stars = repo_data.get("stars", 0)
        forks = repo_data.get("forks", 0)
        watchers = repo_data.get("watchers", 0)
        open_issues = repo_data.get("open_issues", 0)
        age_days = repo_data.get("age_days", 0)
        last_activity_days = repo_data.get("last_activity_days", 9999)
        contributors = repo_data.get("contributors", [])
        releases = repo_data.get("releases", [])
        recent_commits = repo_data.get("recent_commits", [])
        open_issues_list = repo_data.get("open_issues_list", [])
        pull_requests = repo_data.get("pull_requests", [])
        open_prs_count = repo_data.get("open_prs_count", 0)
        languages = repo_data.get("languages", {})
        topics = repo_data.get("topics", [])
        readme = repo_data.get("readme", "")
        root_contents = repo_data.get("root_contents", [])
        dependencies = repo_data.get("dependencies", {})
        archived = repo_data.get("archived", False)
        is_fork = repo_data.get("fork", False)

        # ── Transparent scoring formula ──
        # Each component is 0-100, weighted, then combined.
        score_components = {}

        # 1. Community Adoption (0-100, weight 25%)
        #    Logarithmic scale: 1 star=0, 10=25, 100=50, 1000=75, 10000=90, 100000=100
        import math
        if stars <= 0:
            adoption = 0
        else:
            adoption = min(100, round(math.log10(max(stars, 1)) * 20))
        score_components["community_adoption"] = adoption

        # 2. Maintenance Activity (0-100, weight 25%)
        #    Based on days since last push, commit recency, and release cadence
        if archived:
            maintenance = 0
        elif last_activity_days <= 7:
            maintenance = 100
        elif last_activity_days <= 30:
            maintenance = 85
        elif last_activity_days <= 90:
            maintenance = 70
        elif last_activity_days <= 180:
            maintenance = 50
        elif last_activity_days <= 365:
            maintenance = 30
        else:
            maintenance = 10
        # Bonus for recent commits in the fetched batch
        if recent_commits:
            recent_count = sum(1 for c in recent_commits if c.get("date", "") >= "2025-01-01")
            maintenance = min(100, maintenance + recent_count * 3)
        score_components["maintenance_activity"] = maintenance

        # 3. Project Maturity (0-100, weight 20%)
        #    Based on age and release history
        if age_days >= 365 * 5:
            maturity = 90
        elif age_days >= 365 * 2:
            maturity = 75
        elif age_days >= 365:
            maturity = 60
        elif age_days >= 180:
            maturity = 45
        elif age_days >= 30:
            maturity = 30
        else:
            maturity = 15
        # Release bonus
        if len(releases) >= 10:
            maturity = min(100, maturity + 10)
        elif len(releases) >= 5:
            maturity = min(100, maturity + 5)
        score_components["project_maturity"] = maturity

        # 4. Contribution Activity (0-100, weight 15%)
        #    Based on contributor count and their commit distribution
        num_contributors = len(contributors)
        if num_contributors >= 50:
            contrib_activity = 90
        elif num_contributors >= 20:
            contrib_activity = 75
        elif num_contributors >= 10:
            contrib_activity = 60
        elif num_contributors >= 5:
            contrib_activity = 45
        elif num_contributors >= 2:
            contrib_activity = 30
        else:
            contrib_activity = 15
        # Distribution bonus: if contributions are spread (not all from one person)
        if num_contributors >= 3:
            top_contrib = contributors[0].get("contributions", 0) if contributors else 0
            total_contrib = sum(c.get("contributions", 0) for c in contributors)
            if total_contrib > 0:
                concentration = top_contrib / total_contrib
                if concentration < 0.5:
                    contrib_activity = min(100, contrib_activity + 15)  # Well distributed
                elif concentration < 0.7:
                    contrib_activity = min(100, contrib_activity + 8)
        score_components["contribution_activity"] = contrib_activity

        # 5. Documentation Quality (0-100, weight 10%)
        #    Based on README presence, length, and structure
        doc_score = 0
        if readme:
            readme_len = len(readme)
            if readme_len > 3000:
                doc_score = 70
            elif readme_len > 1000:
                doc_score = 50
            elif readme_len > 200:
                doc_score = 30
            else:
                doc_score = 15
            # Structure bonus: headings, code blocks, links
            if "## " in readme:
                doc_score = min(100, doc_score + 10)
            if "```" in readme:
                doc_score = min(100, doc_score + 10)
            if "http" in readme:
                doc_score = min(100, doc_score + 5)
        score_components["documentation_quality"] = doc_score

        # 6. Community Strength (0-100, weight 5%)
        #    Based on forks ratio, watchers, and topic tags
        fork_ratio = forks / max(stars, 1)
        community = 0
        if fork_ratio > 0.1:
            community += 40
        elif fork_ratio > 0.05:
            community += 25
        elif fork_ratio > 0.01:
            community += 15
        if watchers > 50:
            community += 30
        elif watchers > 10:
            community += 20
        elif watchers > 0:
            community += 10
        if len(topics) >= 5:
            community += 20
        elif len(topics) >= 2:
            community += 10
        elif len(topics) >= 1:
            community += 5
        score_components["community_strength"] = min(100, community)

        # ── Weighted composite score ──
        weights = {
            "community_adoption": 0.25,
            "maintenance_activity": 0.25,
            "project_maturity": 0.20,
            "contribution_activity": 0.15,
            "documentation_quality": 0.10,
            "community_strength": 0.05,
        }
        total_score = sum(score_components[k] * weights[k] for k in weights)
        total_score = max(0, min(100, round(total_score)))

        # ── Risk assessment (data-driven) ──
        risks = []
        if archived:
            risks.append("Repository is archived and no longer maintained.")
        if is_fork:
            risks.append("This is a fork, not the canonical repository.")
        if last_activity_days > 365:
            risks.append(f"No commits in {last_activity_days} days — appears abandoned.")
        elif last_activity_days > 180:
            risks.append(f"Last activity was {last_activity_days} days ago — declining activity.")
        if open_issues > 500:
            risks.append(f"High open issue count ({open_issues}) — potential maintenance burden.")
        if num_contributors <= 1:
            risks.append("Single contributor — bus factor risk.")
        if not readme or len(readme) < 100:
            risks.append("Missing or minimal README — poor onboarding documentation.")
        if not releases:
            risks.append("No releases found — versioning and stability unclear.")
        if repo_data.get("license") == "None" or not repo_data.get("license"):
            risks.append("No license specified — legal usage unclear.")

        # ── Strengths (data-driven) ──
        strengths = []
        if stars >= 10000:
            strengths.append(f"Very high adoption with {stars:,} stars.")
        elif stars >= 1000:
            strengths.append(f"Strong adoption with {stars:,} stars.")
        if last_activity_days <= 7:
            strengths.append("Very active — commits within the last week.")
        elif last_activity_days <= 30:
            strengths.append("Actively maintained — commits within the last month.")
        if num_contributors >= 20:
            strengths.append(f"Healthy contributor base ({num_contributors} contributors).")
        if releases:
            strengths.append(f"Regular release cadence ({len(releases)} releases found).")
        if readme and len(readme) > 1000:
            strengths.append("Well-documented with comprehensive README.")
        if languages and len(languages) > 1:
            strengths.append(f"Multi-language codebase ({len(languages)} languages).")
        if topics:
            strengths.append(f"Well-tagged ({len(topics)} topics) for discoverability.")
        if repo_data.get("license") and repo_data.get("license") != "None":
            strengths.append(f"Licensed under {repo_data.get('license')}.")

        # ── Technology stack from languages ──
        tech_stack = []
        if languages:
            total_bytes = sum(languages.values())
            for lang, bytes_count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
                pct = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
                if pct >= 1:  # Only include languages with >= 1% of codebase
                    tech_stack.append({"language": lang, "percentage": round(pct, 1), "bytes": bytes_count})

        # ── Contribution distribution �n        contrib_summary = []
        if contributors:
            total_contributions = sum(c.get("contributions", 0) for c in contributors)
            for c in contributors[:10]:
                contrib_pct = (c["contributions"] / total_contributions * 100) if total_contributions > 0 else 0
                contrib_summary.append({
                    "login": c["login"],
                    "contributions": c["contributions"],
                    "percentage": round(contrib_pct, 1),
                })

        # ── Project structure summary ──
        structure_summary = []
        if root_contents:
            dirs = [i["name"] for i in root_contents if i["type"] == "dir"]
            files = [i["name"] for i in root_contents if i["type"] == "file"]
            structure_summary = {
                "directories": dirs[:15],
                "files": files[:15],
                "has_common_manifests": bool(dependencies),
            }

        # ── Summary generation ──
        if self.use_llm:
            logger.info("Using Gemini LLM for Repository Intelligence Analysis")
            prompt = f"""
            You are a senior open-source analyst. Analyze the following repository data and provide a professional assessment.
            CRITICAL ANTI-HALLUCINATION RULES:
            - Base ALL insights strictly on the metrics provided below.
            - Do NOT invent features, contributors, or metrics not present in the data.
            - Every statement must be traceable to a specific data point.

            Repository: {repo_data.get('name')}
            URL: {repo_data.get('url', '')}
            Description: {repo_data.get('description', 'None')}
            Primary Language: {repo_data.get('language', 'None')}
            Stars: {stars:,}
            Forks: {forks:,}
            Watchers: {watchers:,}
            Open Issues: {open_issues:,}
            Open PRs: {open_prs_count}
            License: {repo_data.get('license', 'None')}
            Age: {age_days} days
            Days Since Last Activity: {last_activity_days}
            Total Contributors: {num_contributors}
            Releases: {len(releases)}
            Languages: {json.dumps({k: v for k, v in list(languages.items())[:10]})}
            Topics: {', '.join(topics[:10]) if topics else 'None'}
            Score: {total_score}/100
            Score Breakdown: {json.dumps(score_components)}

            Return ONLY a valid JSON object with:
            {{
                "summary": "2-3 sentence professional summary",
                "health_assessment": "One sentence on overall repository health",
                "maintenance_assessment": "One sentence on maintenance status",
                "technology_assessment": "One sentence on the tech stack and its implications",
                "community_assessment": "One sentence on the contributor ecosystem",
                "documentation_assessment": "One sentence on documentation quality",
                "notable_strengths": ["strength 1", "strength 2"],
                "key_risks": ["risk 1", "risk 2"],
                "recommendation": "Should a developer use/contribute to this? Brief reasoning."
            }}
            """
            try:
                res_text = self._safe_generate(prompt)
                res_text = res_text.replace('```json', '').replace('```', '').strip()
                llm_data = json.loads(res_text)
                # Merge LLM insights with deterministic data
                return {
                    "status": "completed",
                    "summary": llm_data.get("summary", ""),
                    "score": total_score,
                    "score_breakdown": score_components,
                    "weights": weights,
                    "health_assessment": llm_data.get("health_assessment", ""),
                    "maintenance_assessment": llm_data.get("maintenance_assessment", ""),
                    "technology_assessment": llm_data.get("technology_assessment", ""),
                    "community_assessment": llm_data.get("community_assessment", ""),
                    "documentation_assessment": llm_data.get("documentation_assessment", ""),
                    "notable_strengths": llm_data.get("notable_strengths", strengths),
                    "key_risks": llm_data.get("key_risks", risks),
                    "recommendation": llm_data.get("recommendation", ""),
                    # Deterministic data (always present regardless of LLM)
                    "repo_name": repo_data.get("name", ""),
                    "repo_url": repo_data.get("url", ""),
                    "description": repo_data.get("description", ""),
                    "stars": stars,
                    "forks": forks,
                    "watchers": watchers,
                    "open_issues": open_issues,
                    "open_prs_count": open_prs_count,
                    "language": repo_data.get("language", ""),
                    "license": repo_data.get("license", "None"),
                    "age_days": age_days,
                    "last_activity_days": last_activity_days,
                    "archived": archived,
                    "topics": topics,
                    "tech_stack": tech_stack,
                    "contributors_summary": contrib_summary,
                    "recent_commits": recent_commits,
                    "releases": releases,
                    "open_issues_list": open_issues_list,
                    "pull_requests": pull_requests,
                    "structure_summary": structure_summary,
                    "readme_excerpt": readme[:2000] if readme else "",
                }
            except RuntimeError:
                raise
            except Exception as e:
                logger.error(f"LLM parsing failed for repository analysis: {e}")

        # ── Fallback: deterministic analysis without LLM ──
        logger.info("No Gemini API key found. Using deterministic repository analysis.")

        summary_parts = []
        summary_parts.append(f"{repo_data.get('name', 'This repository')} is a {repo_data.get('language', 'Unknown')} project")
        summary_parts.append(f"with {stars:,} stars and {forks:,} forks.")
        if repo_data.get('description'):
            summary_parts.append(repo_data['description'])
        summary = " ".join(summary_parts)

        health = "healthy" if total_score >= 70 else "moderate" if total_score >= 40 else "low"
        health_assessment = f"Overall repository health is {health} (score: {total_score}/100)."

        if last_activity_days <= 30:
            maint = "actively maintained with recent commits"
        elif last_activity_days <= 180:
            maint = "moderately active"
        else:
            maint = f"last active {last_activity_days} days ago"
        maintenance_assessment = f"Maintenance status: {maint}."

        tech_assessment = f"Primary language is {repo_data.get('language', 'unknown')}."
        if tech_stack:
            lang_list = ", ".join(f"{t['language']} ({t['percentage']}%)" for t in tech_stack[:5])
            tech_assessment += f" Codebase composition: {lang_list}."

        community_assessment = f"{num_contributors} contributor(s) found."
        if contrib_summary:
            top = contrib_summary[0]
            community_assessment += f" Top contributor: {top['login']} ({top['contributions']} commits, {top['percentage']}%)."

        doc_assessment = "No README found."
        if readme:
            doc_len = len(readme)
            if doc_len > 3000:
                doc_assessment = f"Comprehensive README ({doc_len:,} characters) with structure and examples."
            elif doc_len > 1000:
                doc_assessment = f"Moderate README ({doc_len:,} characters)."
            else:
                doc_assessment = f"Minimal README ({doc_len} characters)."

        return {
            "status": "completed",
            "summary": summary,
            "score": total_score,
            "score_breakdown": score_components,
            "weights": weights,
            "health_assessment": health_assessment,
            "maintenance_assessment": maintenance_assessment,
            "technology_assessment": tech_assessment,
            "community_assessment": community_assessment,
            "documentation_assessment": doc_assessment,
            "notable_strengths": strengths[:5],
            "key_risks": risks[:5],
            "recommendation": f"{'Recommended' if total_score >= 60 else 'Use with caution'} — {health} repository with {stars:,} stars.",
            # Deterministic data
            "repo_name": repo_data.get("name", ""),
            "repo_url": repo_data.get("url", ""),
            "description": repo_data.get("description", ""),
            "stars": stars,
            "forks": forks,
            "watchers": watchers,
            "open_issues": open_issues,
            "open_prs_count": open_prs_count,
            "language": repo_data.get("language", ""),
            "license": repo_data.get("license", "None"),
            "age_days": age_days,
            "last_activity_days": last_activity_days,
            "archived": archived,
            "topics": topics,
            "tech_stack": tech_stack,
            "contributors_summary": contrib_summary,
            "recent_commits": recent_commits,
            "releases": releases,
            "open_issues_list": open_issues_list,
            "pull_requests": pull_requests,
            "structure_summary": structure_summary,
            "readme_excerpt": readme[:2000] if readme else "",
        }
