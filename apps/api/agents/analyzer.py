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

