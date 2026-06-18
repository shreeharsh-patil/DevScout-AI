import subprocess
import json
import requests
from loguru import logger

class ResearcherAgent:
    """
    Responsible for gathering raw data using upstream tools and APIs.
    """
    
    def __init__(self):
        pass

    def fetch_web_page(self, url: str) -> str:
        """Reads a webpage using Jina Reader."""
        logger.info(f"Fetching web page: {url}")
        try:
            # Clean up the URL if needed
            clean_url = url.replace("https://", "").replace("http://", "")
            jina_url = f"https://r.jina.ai/https://{clean_url}"
            response = requests.get(jina_url, timeout=45)
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Jina Reader failed with status {response.status_code}")
                return ""
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return ""

    def search_github_repos(self, query: str) -> dict:
        """Searches GitHub repos using the REST API."""
        logger.info(f"Searching GitHub: {query}")
        try:
            url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=5"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
            return {}

    def fetch_github_profile(self, handle: str) -> dict:
        """Fetches GitHub user info using the REST API."""
        # Extract username if a full GitHub URL is provided
        if "github.com/" in handle:
            parts = handle.split("github.com/")[-1].split("/")
            if len(parts) >= 1:
                handle = parts[0]

        logger.info(f"Fetching GitHub profile for: {handle}")
        try:
            headers = {"Accept": "application/vnd.github.v3+json"}
            
            # Fetch profile
            profile_resp = requests.get(f"https://api.github.com/users/{handle}", headers=headers, timeout=10)
            if profile_resp.status_code != 200:
                logger.error(f"Failed to find GitHub user {handle}")
                return {}
            user_data = profile_resp.json()
            
            # Fetch recent repos
            repo_resp = requests.get(f"https://api.github.com/users/{handle}/repos?sort=updated&per_page=10", headers=headers, timeout=10)
            repo_data = repo_resp.json() if repo_resp.status_code == 200 else []
            
            return {
                "profile": user_data,
                "recent_repos": repo_data
            }
        except Exception as e:
            logger.error(f"GitHub profile fetch failed: {e}")
            return {}

    def fetch_youtube_info(self, url: str) -> dict:
        """Extracts YouTube video info using yt-dlp."""
        logger.info(f"Extracting YouTube info: {url}")
        try:
            result = subprocess.run(["yt-dlp", "--dump-json", url], capture_output=True, text=True)
            return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"YouTube info fetch failed: {e}")
            return {}

    def search_email_osint(self, email: str) -> dict:
        """Searches public APIs (like GitHub) to find footprints of an email."""
        logger.info(f"Conducting OSINT for email: {email}")
        results = {"email": email, "github_accounts": []}
        try:
            # Check GitHub for users associated with this email
            headers = {"Accept": "application/vnd.github.v3+json"}
            resp = requests.get(f"https://api.github.com/search/users?q={email} in:email", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results["github_accounts"] = data.get("items", [])
        except Exception as e:
            logger.error(f"Email OSINT failed: {e}")
            
        return results

    def search_web_exa(self, query: str, num_results: int = 5) -> dict:
        """Searches the web using Exa AI via Agent Reach's mcporter integration."""
        logger.info(f"Searching Exa for: {query}")
        try:
            # We use subprocess to call mcporter which has the Exa MCP configured
            cmd = f"mcporter call 'exa.web_search_exa(query: \"{query}\", numResults: {num_results})'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return {"raw_output": result.stdout}
        except Exception as e:
            logger.error(f"Exa search failed: {e}")
            return {"raw_output": ""}

    def search_social_tracker(self, keyword: str) -> dict:
        """Searches multiple platforms (Twitter, Bilibili, GitHub, Reddit) for a keyword."""
        logger.info(f"Running Cross-Platform Social Tracker for: {keyword}")
        aggregated_data = {
            "keyword": keyword,
            "twitter": "Not configured or failed to fetch.",
            "bilibili": "Failed to fetch.",
            "github": "Failed to fetch.",
            "reddit": "Failed to fetch."
        }
        
        # 1. Twitter (via twitter-cli)
        try:
            logger.info("Fetching Twitter data...")
            tw_result = subprocess.run(["twitter", "search", keyword, "-n", "3"], capture_output=True, text=True, timeout=15)
            if tw_result.returncode == 0 and tw_result.stdout.strip():
                aggregated_data["twitter"] = tw_result.stdout[:1500]
        except Exception as e:
            logger.warning(f"Twitter search failed (might need cookie config): {e}")

        # 2. Bilibili (via bili-cli)
        try:
            logger.info("Fetching Bilibili data...")
            bili_result = subprocess.run(["bili", "search", keyword, "--type", "video", "-n", "3"], capture_output=True, text=True, timeout=15)
            if bili_result.returncode == 0 and bili_result.stdout.strip():
                aggregated_data["bilibili"] = bili_result.stdout[:1500]
        except Exception as e:
            logger.warning(f"Bilibili search failed: {e}")

        # 3. GitHub (reusing existing API call)
        logger.info("Fetching GitHub data...")
        gh_data = self.search_github_repos(keyword)
        if gh_data.get("items"):
            # Extract top 3 repos' descriptions
            gh_summaries = [f"{repo.get('full_name')} ({repo.get('stargazers_count')} stars): {repo.get('description')}" for repo in gh_data.get("items")[:3]]
            aggregated_data["github"] = "\n".join(gh_summaries)
            
        # 4. Reddit (via Exa)
        logger.info("Fetching Reddit data...")
        reddit_data = self.search_web_exa(f"site:reddit.com {keyword}", num_results=3)
        if reddit_data.get("raw_output"):
            aggregated_data["reddit"] = reddit_data.get("raw_output")[:1500]

        return aggregated_data

