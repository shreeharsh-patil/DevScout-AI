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

