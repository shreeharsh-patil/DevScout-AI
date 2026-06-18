import subprocess
import json
from loguru import logger

class ResearcherAgent:
    """
    Responsible for gathering raw data using Agent Reach's upstream tools.
    """
    
    def __init__(self):
        pass

    def fetch_web_page(self, url: str) -> str:
        """Reads a webpage using Jina Reader."""
        logger.info(f"Fetching web page: {url}")
        try:
            result = subprocess.run(["curl", "-s", f"https://r.jina.ai/{url}"], capture_output=True, text=True)
            return result.stdout
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return ""

    def search_github_repos(self, query: str) -> dict:
        """Searches GitHub repos using gh CLI."""
        logger.info(f"Searching GitHub: {query}")
        try:
            result = subprocess.run(
                ["gh", "search", "repos", query, "--sort", "stars", "--limit", "5", "--json", "fullName,description,stargazersCount,url"],
                capture_output=True, text=True
            )
            return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
            return {}

    def fetch_github_profile(self, handle: str) -> dict:
        """Fetches GitHub user info using gh CLI."""
        logger.info(f"Fetching GitHub profile for: {handle}")
        try:
            # Using gh api to get user info
            result = subprocess.run(["gh", "api", f"/users/{handle}"], capture_output=True, text=True)
            user_data = json.loads(result.stdout)
            
            # Get their repos
            repo_result = subprocess.run(["gh", "api", f"/users/{handle}/repos?sort=updated&per_page=10"], capture_output=True, text=True)
            repo_data = json.loads(repo_result.stdout)
            
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
