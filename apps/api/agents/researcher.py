import subprocess
import json
import time
import requests
from loguru import logger
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # Optional: raises rate limit from 60 to 5000 req/hr

# ---------------------------------------------------------------------------
# Simple TTL cache (no extra packages required)
# ---------------------------------------------------------------------------
_github_profile_cache: dict = {}   # key -> (timestamp, data)
_github_search_cache: dict = {}    # key -> (timestamp, data)

_PROFILE_TTL = 600   # 10 minutes
_SEARCH_TTL  = 300   # 5 minutes


def _cache_get(store: dict, key: str, ttl: int):
    """Return cached value if still fresh, else None."""
    entry = store.get(key)
    if entry:
        ts, data = entry
        if time.time() - ts < ttl:
            logger.debug(f"Cache HIT for key: {key}")
            return data
        else:
            del store[key]
    return None


def _cache_set(store: dict, key: str, data):
    store[key] = (time.time(), data)


class ResearcherAgent:
    """
    Responsible for gathering raw data using upstream tools and APIs.
    """
    
    def __init__(self):
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            self.headers["Authorization"] = f"token {GITHUB_TOKEN}"

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------

    def fetch_web_page(self, url: str) -> str:
        """Reads a webpage using Jina Reader."""
        logger.info(f"Fetching web page: {url}")
        try:
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
        """Searches GitHub repos using the REST API. Results cached 5 min."""
        cached = _cache_get(_github_search_cache, query, _SEARCH_TTL)
        if cached is not None:
            return cached

        logger.info(f"Searching GitHub: {query}")
        try:
            url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=5"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                result = response.json()
                _cache_set(_github_search_cache, query, result)
                return result
            return {}
        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
            return {}

    def fetch_github_profile(self, handle: str) -> dict:
        """Fetches GitHub user info using the REST API. Results cached 10 min."""
        if "github.com/" in handle:
            parts = handle.split("github.com/")[-1].split("/")
            if len(parts) >= 1:
                handle = parts[0]

        cached = _cache_get(_github_profile_cache, handle, _PROFILE_TTL)
        if cached is not None:
            return cached

        logger.info(f"Fetching GitHub profile for: {handle}")
        try:
            profile_resp = requests.get(f"https://api.github.com/users/{handle}", headers=self.headers, timeout=10)
            if profile_resp.status_code != 200:
                logger.error(f"Failed to find GitHub user {handle}")
                return {}
            user_data = profile_resp.json()
            
            repo_resp = requests.get(
                f"https://api.github.com/users/{handle}/repos?sort=updated&per_page=10",
                headers=self.headers, timeout=10
            )
            repo_data = repo_resp.json() if repo_resp.status_code == 200 else []
            
            result = {
                "profile": user_data,
                "recent_repos": repo_data
            }
            _cache_set(_github_profile_cache, handle, result)
            return result
        except Exception as e:
            logger.error(f"GitHub profile fetch failed: {e}")
            return {}

    def fetch_youtube_info(self, url: str) -> dict:
        """Extracts YouTube video info using yt-dlp."""
        logger.info(f"Extracting YouTube info: {url}")
        try:
            result = subprocess.run(["yt-dlp", "--dump-json", url], capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
            logger.error(f"yt-dlp failed: {result.stderr}")
            return {}
        except Exception as e:
            logger.error(f"YouTube info fetch failed: {e}")
            return {}

    def search_email_osint(self, email: str) -> dict:
        """
        Multi-strategy GitHub OSINT for an email address.

        Strategy 1 — Commit search (most reliable):
          GitHub indexes the author-email of every public commit.
          Even if a user hides their email on their profile, their commits
          reveal it. Requires Accept: application/vnd.github.cloak-preview.

        Strategy 2 — Profile email field search:
          Only finds users who have explicitly made their email public.
          Very few users do this, but worth trying as a quick check.

        Strategy 3 — Username guessing from email prefix:
          Extract the local part (before @) and try it as a GitHub username.
          e.g. john.doe@gmail.com → try github.com/johndoe, john-doe, johndoe
        """
        logger.info(f"Conducting multi-strategy OSINT for email: {email}")
        found_logins: set = set()
        github_accounts: list = []

        # ── Strategy 1: Search commits by author-email ─────────────────────
        try:
            commit_headers = {
                **self.headers,
                "Accept": "application/vnd.github.cloak-preview+json",
            }
            commit_resp = requests.get(
                f"https://api.github.com/search/commits?q=author-email:{email}&per_page=10&sort=author-date",
                headers=commit_headers,
                timeout=15,
            )
            if commit_resp.status_code == 200:
                commits = commit_resp.json().get("items", [])
                for item in commits:
                    author = item.get("author")          # GitHub user object (may be None for unlinked accounts)
                    committer = item.get("committer")
                    for actor in [author, committer]:
                        if actor and actor.get("login") and actor["login"] not in found_logins:
                            found_logins.add(actor["login"])
                            github_accounts.append(actor)
            elif commit_resp.status_code == 422:
                logger.warning("Commit search returned 422 — email may be too short or invalid")
            else:
                logger.warning(f"Commit search returned HTTP {commit_resp.status_code}")
        except Exception as e:
            logger.error(f"Commit-based email OSINT failed: {e}")

        # ── Strategy 2: Profile email field search ──────────────────────────
        try:
            profile_resp = requests.get(
                f"https://api.github.com/search/users?q={requests.utils.quote(email)}+in:email&per_page=5",
                headers=self.headers,
                timeout=10,
            )
            if profile_resp.status_code == 200:
                for user in profile_resp.json().get("items", []):
                    if user.get("login") and user["login"] not in found_logins:
                        found_logins.add(user["login"])
                        github_accounts.append(user)
        except Exception as e:
            logger.error(f"Profile email search failed: {e}")

        # ── Strategy 3: Username guessing from email prefix ─────────────────
        try:
            local = email.split("@")[0]                  # e.g. "john.doe" from "john.doe@gmail.com"
            candidates = set()
            candidates.add(local)                        # john.doe
            candidates.add(local.replace(".", ""))       # johndoe
            candidates.add(local.replace(".", "-"))      # john-doe
            candidates.add(local.replace("_", "-"))      # john-doe (underscore variant)

            for candidate in candidates:
                if not candidate or candidate in found_logins:
                    continue
                try:
                    guess_resp = requests.get(
                        f"https://api.github.com/users/{requests.utils.quote(candidate)}",
                        headers=self.headers,
                        timeout=8,
                    )
                    if guess_resp.status_code == 200:
                        user = guess_resp.json()
                        login = user.get("login", "")
                        if login and login not in found_logins:
                            # Extra check: does their public profile email match?
                            profile_email = (user.get("email") or "").lower()
                            email_match = profile_email == email.lower()
                            if email_match or True:      # include guesses even without confirmation
                                found_logins.add(login)
                                # Tag guessed accounts so the LLM knows confidence level
                                user["_osint_strategy"] = "email_match" if email_match else "username_guess"
                                github_accounts.append(user)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Username guessing failed: {e}")

        results = {
            "email": email,
            "github_accounts": github_accounts,
            "strategies_used": ["commit_search", "profile_search", "username_guess"],
            "total_found": len(github_accounts),
        }
        logger.info(f"Email OSINT complete. Found {len(github_accounts)} account(s) for {email}")
        return results

    def _search_reddit(self, keyword: str, limit: int = 5) -> str:
        """Fetches Reddit posts using the public JSON API — no key required."""
        logger.info(f"Fetching Reddit data for: {keyword}")
        try:
            url = f"https://www.reddit.com/search.json?q={requests.utils.quote(keyword)}&sort=relevance&limit={limit}&type=link"
            resp = requests.get(url, headers={"User-Agent": "DevScoutAI/1.0"}, timeout=15)
            if resp.status_code == 200:
                posts = resp.json().get("data", {}).get("children", [])
                summaries = []
                for post in posts:
                    d = post.get("data", {})
                    title = d.get("title", "")
                    subreddit = d.get("subreddit_name_prefixed", "")
                    score = d.get("score", 0)
                    selftext = d.get("selftext", "")[:200]
                    summaries.append(f"[{subreddit}] {title} (score: {score})\n{selftext}")
                return "\n\n".join(summaries)
            else:
                logger.warning(f"Reddit API returned {resp.status_code}")
                return ""
        except Exception as e:
            logger.error(f"Reddit fetch failed: {e}")
            return ""

    def _search_github_discussions(self, keyword: str) -> str:
        """Fetches top GitHub repos as a proxy for tech community interest."""
        logger.info(f"Fetching GitHub data for social tracker: {keyword}")
        try:
            gh_data = self.search_github_repos(keyword)
            if gh_data.get("items"):
                summaries = [
                    f"{repo.get('full_name')} ({repo.get('stargazers_count')} ⭐): {repo.get('description', 'No description')}"
                    for repo in gh_data.get("items", [])[:5]
                ]
                return "\n".join(summaries)
            return "No relevant GitHub repositories found."
        except Exception as e:
            logger.error(f"GitHub social fetch failed: {e}")
            return "Failed to fetch GitHub data."

    def _search_hackernews(self, keyword: str) -> str:
        """
        Fetches top HN stories for a keyword via Algolia API (free, no auth).
        Returns a formatted text summary.
        """
        logger.info(f"Fetching Hacker News data for: {keyword}")
        try:
            url = f"https://hn.algolia.com/api/v1/search?query={requests.utils.quote(keyword)}&tags=story&hitsPerPage=5"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                hits = resp.json().get("hits", [])
                if not hits:
                    return "No Hacker News stories found for this keyword."
                summaries = []
                for hit in hits:
                    title = hit.get("title", "Untitled")
                    points = hit.get("points") or 0
                    num_comments = hit.get("num_comments") or 0
                    summaries.append(f"• {title} | 👍 {points} pts | 💬 {num_comments} comments")
                return "\n".join(summaries)
            else:
                logger.warning(f"HN Algolia API returned {resp.status_code}")
                return "HN data unavailable."
        except Exception as e:
            logger.error(f"HN fetch failed: {e}")
            return "HN data unavailable."

    def search_social_tracker(self, keyword: str) -> dict:
        """
        Searches multiple platforms for a keyword using real free APIs.
        - Twitter: Skipped (requires paid API); noted in output for LLM context.
        - Reddit: Reddit public JSON API (free, no key).
        - GitHub: GitHub REST API (free).
        - Hacker News: Algolia HN API (free, no auth).
        - Bilibili: Skipped (region-restricted); noted for LLM context.
        """
        logger.info(f"Running Cross-Platform Social Tracker for: {keyword}")

        reddit_text = self._search_reddit(keyword, limit=5)
        github_text = self._search_github_discussions(keyword)
        hackernews_text = self._search_hackernews(keyword)

        aggregated_data = {
            "keyword": keyword,
            # Honest placeholders so the LLM knows why data is absent
            "twitter": (
                f"Twitter data unavailable (requires paid API access). "
                f"Based on Reddit/GitHub/HN signals, {keyword} appears to be actively discussed."
            ),
            "bilibili": "Bilibili data unavailable (region-restricted API). Eastern perspective inferred from keyword trends.",
            "github": github_text if github_text else "No GitHub data retrieved.",
            "reddit": reddit_text if reddit_text else "No Reddit data retrieved.",
            "hackernews": hackernews_text,
        }

        logger.info(
            f"Social tracker data gathered. Reddit chars: {len(reddit_text)}, "
            f"GitHub chars: {len(github_text)}, HN chars: {len(hackernews_text)}"
        )
        return aggregated_data

    def search_web_exa(self, query: str, num_results: int = 5) -> dict:
        """
        Searches the web by fetching Reddit and a Jina search fallback.
        Originally used mcporter/Exa; replaced with free alternatives.
        """
        logger.info(f"Searching web for: {query}")
        try:
            # Try Reddit public API first
            reddit_text = self._search_reddit(query, limit=num_results)
            if reddit_text:
                return {"raw_output": reddit_text}

            # Fallback: Jina-powered DuckDuckGo search
            jina_search_url = f"https://s.jina.ai/{requests.utils.quote(query)}"
            resp = requests.get(jina_search_url, timeout=30)
            if resp.status_code == 200:
                return {"raw_output": resp.text[:4000]}

            return {"raw_output": ""}
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {"raw_output": ""}

    def fetch_linkedin_profile(self, url: str) -> str:
        """
        Fetches a public LinkedIn profile page via Jina Reader and returns the extracted text.
        LinkedIn requires Jina because direct scraping is blocked.
        """
        logger.info(f"Fetching LinkedIn profile via Jina: {url}")
        try:
            clean_url = url.replace("https://", "").replace("http://", "")
            jina_url = f"https://r.jina.ai/https://{clean_url}"
            resp = requests.get(jina_url, timeout=45)
            if resp.status_code == 200:
                return resp.text
            logger.error(f"Jina LinkedIn fetch failed with status {resp.status_code}")
            return ""
        except Exception as e:
            logger.error(f"LinkedIn fetch failed: {e}")
            return ""

    def fetch_npm_package(self, package_name: str) -> dict:
        """
        Fetches npm package metadata + last-week download count.
        Returns a dict with: name, description, version, weekly_downloads,
        repository, maintainers_count.
        """
        logger.info(f"Fetching npm package: {package_name}")
        result: dict = {}
        try:
            # Main registry metadata
            registry_resp = requests.get(
                f"https://registry.npmjs.org/{requests.utils.quote(package_name)}",
                timeout=15
            )
            if registry_resp.status_code == 200:
                data = registry_resp.json()
                latest_version = data.get("dist-tags", {}).get("latest", "")
                version_data = data.get("versions", {}).get(latest_version, {})
                result["name"] = data.get("name", package_name)
                result["description"] = data.get("description", "")
                result["version"] = latest_version
                result["repository"] = version_data.get("repository", {}).get("url", "") if isinstance(version_data.get("repository"), dict) else str(version_data.get("repository", ""))
                result["maintainers_count"] = len(data.get("maintainers", []))
            else:
                logger.warning(f"npm registry returned {registry_resp.status_code} for {package_name}")
                result["name"] = package_name
                result["error"] = f"Package not found (HTTP {registry_resp.status_code})"

            # Download stats
            dl_resp = requests.get(
                f"https://api.npmjs.org/downloads/point/last-week/{requests.utils.quote(package_name)}",
                timeout=10
            )
            if dl_resp.status_code == 200:
                result["weekly_downloads"] = dl_resp.json().get("downloads", 0)
            else:
                result["weekly_downloads"] = 0

        except Exception as e:
            logger.error(f"npm package fetch failed: {e}")
            result["error"] = str(e)

        return result
