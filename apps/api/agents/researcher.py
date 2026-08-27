import subprocess
import json
import time
import re
import requests
from loguru import logger
import os
from dotenv import load_dotenv

from sources import SourceCollector

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
            
            collector = SourceCollector()
            collector.add_source(
                title=f"GitHub Profile: {handle}",
                url=user_data.get("html_url") or f"https://github.com/{handle}",
                platform="github",
                source_type="user_profile",
                snippet=f"{user_data.get('name', handle)}: {user_data.get('bio', 'No bio provided.')}"
            )
            collector.add_source(
                title=f"GitHub User API Endpoint: {handle}",
                url=f"https://api.github.com/users/{handle}",
                platform="github",
                source_type="rest_api",
                snippet=f"Public repositories: {user_data.get('public_repos', 0)}, Followers: {user_data.get('followers', 0)}"
            )
            collector.add_source(
                title=f"GitHub Repositories List: {handle}",
                url=f"https://api.github.com/users/{handle}/repos?sort=updated&per_page=10",
                platform="github",
                source_type="rest_api",
                snippet=f"Fetched top {len(repo_data)} recent repositories."
            )

            result = {
                "profile": user_data,
                "recent_repos": repo_data,
                "sources": collector.get_sources()
            }
            _cache_set(_github_profile_cache, handle, result)
            return result
        except Exception as e:
            logger.error(f"GitHub profile fetch failed: {e}")
            return {}

    def fetch_youtube_info(self, url: str) -> dict:
        """Extracts YouTube video info and transcripts using yt-dlp."""
        logger.info(f"Extracting YouTube info: {url}")
        try:
            # Get metadata + attempt to fetch automatic/manual subs
            result = subprocess.run([
                "yt-dlp", 
                "--dump-json", 
                "--write-sub", 
                "--write-auto-sub", 
                "--sub-lang", "en,zh-Hans", 
                "--skip-download", 
                url
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                # Check for transcript availability
                data["_has_transcript"] = bool(data.get("subtitles") or data.get("automatic_captions"))
                
                collector = SourceCollector()
                collector.add_source(
                    title=f"YouTube Video: {data.get('title', 'Video')}",
                    url=url,
                    platform="youtube",
                    source_type="video_stream",
                    snippet=f"Uploader: {data.get('uploader', 'Unknown')} | Views: {data.get('view_count', 0):,} | Description: {data.get('description', '')[:200]}"
                )
                if data.get("uploader_url") or data.get("channel_url"):
                    collector.add_source(
                        title=f"YouTube Channel: {data.get('uploader', 'Channel')}",
                        url=data.get("uploader_url") or data.get("channel_url", ""),
                        platform="youtube",
                        source_type="channel_profile"
                    )
                data["sources"] = collector.get_sources()
                return data
            
            logger.error(f"yt-dlp failed: {result.stderr}")
            return {}
        except Exception as e:
            logger.error(f"YouTube info fetch failed: {e}")
            return {}


    def fetch_stack_overflow_user(self, email: str) -> dict:
        """Searches for a Stack Overflow user by email hash (MD5)."""
        import hashlib
        logger.info(f"Searching Stack Overflow for email: {email}")
        try:
            # SO doesn't allow direct email search, but Gravatar uses MD5 hash
            email_hash = hashlib.md5(email.strip().lower().encode()).hexdigest()
            # This is a heuristic: check if a user exists with this hash
            url = f"https://api.stackexchange.com/2.3/users?filter=!LnN.q_U)B7yZ5X.r)Cg*v.&site=stackoverflow&key=U4DMV*8nv6v6h9Z*44nOnw(("
            # SO API usually requires an email check via a different method or just finding accounts with matching data
            # For now, we'll search for users with matching display names or just use it as a placeholder for expansion
            return {"hash": email_hash, "note": "Stack Overflow direct email search is restricted; hash generated for Gravatar mapping."}
        except Exception as e:
            logger.error(f"Stack Overflow search failed: {e}")
            return {}

    def search_email_osint(self, email: str) -> dict:
        """
        Comprehensive email OSINT using 10+ data sources (behindtheemail.com style).
        Delegates to the EmailOSINT module which handles all sources.
        """
        from .email_osint import EmailOSINT
        engine = EmailOSINT()
        profile = engine.run_all(email)
        logger.info(f"Email OSINT complete for {email} — completeness: {profile.get('profile_completeness', {}).get('score', 0)}%")
        return profile

    def _search_hackernews(self, keyword: str, limit: int = 10) -> str:
        """Fetches top Hacker News stories using the HN Algolia API."""
        logger.info(f"Fetching Hacker News data for: {keyword}")
        try:
            url = f"https://hn.algolia.com/api/v1/search?query={requests.utils.quote(keyword)}&tags=story&hitsPerPage={limit}"
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                hits = resp.json().get("hits", [])
                summaries = []
                for hit in hits:
                    title = hit.get("title", "")
                    points = hit.get("points", 0)
                    story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                    summaries.append(f"• {title} ({points} pts) — {story_url}")
                return "\n".join(summaries)
            return ""
        except Exception as e:
            logger.error(f"Hacker News fetch failed: {e}")
            return ""

    def _search_reddit(self, keyword: str, limit: int = 5) -> str:
        """Fetches Reddit posts using the public JSON API."""
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
                    summaries.append(f"[{subreddit}] {title} (👍 {score})")
                return "\n".join(summaries)
            return ""
        except Exception as e:
            logger.error(f"Reddit fetch failed: {e}")
            return ""

    def _search_twitter(self, keyword: str, limit: int = 5) -> str:
        """Fetches tweets using live twitter-cli."""
        logger.info(f"Fetching Twitter data for: {keyword}")
        try:
            # Using twitter-cli installed in venv
            result = subprocess.run(["twitter", "search", keyword, "-n", str(limit)], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
            return "Twitter search returned no results (Auth might be required)."
        except Exception as e:
            logger.error(f"Twitter fetch failed: {e}")
            return "Twitter search failed."

    def _search_bilibili(self, keyword: str, limit: int = 5) -> str:
        """Fetches Bilibili videos using live bili-cli."""
        logger.info(f"Fetching Bilibili data for: {keyword}")
        try:
            result = subprocess.run(["bili", "search", keyword, "--type", "video", "-n", str(limit)], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
            return "Bilibili search returned no results."
        except Exception as e:
            logger.error(f"Bilibili fetch failed: {e}")
            return "Bilibili search failed."

    def search_social_tracker(self, keyword: str) -> dict:
        """
        Searches multiple platforms for a keyword using live tools and APIs.
        """
        logger.info(f"Running Live Cross-Platform Social Tracker for: {keyword}")

        reddit_text = self._search_reddit(keyword)
        twitter_text = self._search_twitter(keyword)
        bilibili_text = self._search_bilibili(keyword)
        github_text = self.search_github_repos(keyword)
        
        gh_summary = ""
        if github_text.get("items"):
            gh_summary = "\n".join([f"• {r['full_name']} ({r['stargazers_count']}⭐): {r['description']}" for r in github_text['items'][:3]])

        collector = SourceCollector()
        collector.add_source(
            title=f"Reddit Search API: {keyword}",
            url=f"https://www.reddit.com/search.json?q={requests.utils.quote(keyword)}",
            platform="reddit",
            source_type="search_api",
            snippet=reddit_text[:200]
        )
        collector.add_source(
            title=f"Hacker News Algolia Search: {keyword}",
            url=f"https://hn.algolia.com/api/v1/search?query={requests.utils.quote(keyword)}",
            platform="hackernews",
            source_type="search_api"
        )
        collector.add_source(
            title=f"GitHub Repositories Search API: {keyword}",
            url=f"https://api.github.com/search/repositories?q={requests.utils.quote(keyword)}",
            platform="github",
            source_type="search_api",
            snippet=gh_summary[:200]
        )

        aggregated_data = {
            "keyword": keyword,
            "twitter": twitter_text,
            "bilibili": bilibili_text,
            "github": gh_summary,
            "reddit": reddit_text,
            "hackernews": self._search_hackernews(keyword),
            "sources": collector.get_sources()
        }

        return aggregated_data

    def search_web_exa(self, query: str, num_results: int = 5) -> dict:
        """
        Searches the web using Jina Search API (DuckDuckGo powered).
        """
        logger.info(f"Searching web via Jina: {query}")
        try:
            jina_search_url = f"https://s.jina.ai/{requests.utils.quote(query)}"
            resp = requests.get(jina_search_url, timeout=30)
            if resp.status_code == 200:
                raw_text = resp.text[:5000]
                collector = SourceCollector()
                collector.add_source(
                    title=f"Web Search Query: {query}",
                    url=jina_search_url,
                    platform="web",
                    source_type="search_query",
                    snippet=f"Query: {query}"
                )
                urls = re.findall(r'https?://[^\s)\]"\'>]+', raw_text)
                for u in urls[:6]:
                    if "jina.ai" not in u:
                        collector.add_source(
                            title=f"Search Result Link: {u.split('//')[-1].split('/')[0]}",
                            url=u,
                            platform="web",
                            source_type="search_result"
                        )
                return {"raw_output": raw_text, "sources": collector.get_sources()}
            return {"raw_output": "", "sources": []}
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {"raw_output": "", "sources": []}

    def fetch_linkedin_profile(self, url: str) -> str:
        """Fetches a public LinkedIn profile page via Jina Reader."""
        logger.info(f"Fetching LinkedIn profile: {url}")
        try:
            clean_url = url.replace("https://", "").replace("http://", "")
            jina_url = f"https://r.jina.ai/https://{clean_url}"
            resp = requests.get(jina_url, timeout=45)
            return resp.text if resp.status_code == 200 else ""
        except Exception as e:
            logger.error(f"LinkedIn fetch failed: {e}")
            return ""

    def fetch_github_repo(self, query: str) -> dict:
        """
        Fetches detailed GitHub repository metadata, top contributors, and language breakdown.
        Accepts 'owner/repo' slug or a full GitHub URL.
        """
        # Parse owner/repo from either a URL or a direct slug
        if "github.com/" in query:
            slug = query.split("github.com/")[-1].strip("/")
        else:
            slug = query.strip("/")

        parts = slug.split("/")
        if len(parts) < 2:
            logger.error(f"Invalid GitHub repo query: {query}")
            return {"error": f"Cannot parse owner/repo from: {query}"}

        owner, repo = parts[0], parts[1]
        logger.info(f"Fetching GitHub repo: {owner}/{repo}")

        try:
            # Repo metadata
            repo_resp = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers=self.headers, timeout=10
            )
            if repo_resp.status_code != 200:
                logger.error(f"GitHub repo fetch failed with status {repo_resp.status_code}")
                return {"error": f"Repository '{owner}/{repo}' not found or inaccessible."}
            repo_data = repo_resp.json()


            # Top contributors
            contrib_resp = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/contributors?per_page=5",
                headers=self.headers, timeout=10
            )
            contributors = []
            if contrib_resp.status_code == 200:
                for c in contrib_resp.json():
                    contributors.append({
                        "login": c.get("login", ""),
                        "contributions": c.get("contributions", 0)
                    })

            # Language breakdown
            lang_resp = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/languages",
                headers=self.headers, timeout=10
            )
            languages = lang_resp.json() if lang_resp.status_code == 200 else {}

            license_info = repo_data.get("license") or {}

            collector = SourceCollector()
            collector.add_source(
                title=f"GitHub Repository: {repo_data.get('full_name', f'{owner}/{repo}')}",
                url=repo_data.get("html_url") or f"https://github.com/{owner}/{repo}",
                platform="github",
                source_type="git_repository",
                snippet=f"Stars: {repo_data.get('stargazers_count', 0):,} | Forks: {repo_data.get('forks_count', 0):,} | Desc: {repo_data.get('description', '')[:200]}"
            )
            collector.add_source(
                title=f"GitHub Repo API: {owner}/{repo}",
                url=f"https://api.github.com/repos/{owner}/{repo}",
                platform="github",
                source_type="rest_api",
                snippet=f"Primary Language: {repo_data.get('language', 'Unknown')} | Open Issues: {repo_data.get('open_issues_count', 0)}"
            )
            collector.add_source(
                title=f"Repository Languages Breakdown: {owner}/{repo}",
                url=f"https://api.github.com/repos/{owner}/{repo}/languages",
                platform="github",
                source_type="rest_api",
                snippet=f"Detected languages: {', '.join(list(languages.keys())[:5]) if languages else 'None'}"
            )
            if contributors:
                collector.add_source(
                    title=f"Top Contributors API: {owner}/{repo}",
                    url=f"https://api.github.com/repos/{owner}/{repo}/contributors",
                    platform="github",
                    source_type="rest_api",
                    snippet=f"Top contributors: {', '.join([c['login'] for c in contributors[:5]])}"
                )

            return {
                "name": repo_data.get("full_name", ""),
                "description": repo_data.get("description", ""),
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "open_issues": repo_data.get("open_issues_count", 0),
                "watchers": repo_data.get("watchers_count", 0),
                "language": repo_data.get("language", ""),
                "topics": repo_data.get("topics", []),
                "license": license_info.get("spdx_id", "None"),
                "created_at": repo_data.get("created_at", ""),
                "pushed_at": repo_data.get("pushed_at", ""),
                "contributors": contributors,
                "languages": languages,
                "sources": collector.get_sources()
            }
        except Exception as e:
            logger.error(f"GitHub repo fetch failed: {e}")
            return {"error": str(e)}


    def fetch_repository_intelligence(self, query: str) -> dict:
        """
        Comprehensive repository intelligence collection.
        Gathers metadata, recent activity, releases, expanded contributors,
        open issues, pull requests, README, project structure, and
        dependency information when discoverable.
        Accepts 'owner/repo' slug or a full GitHub URL.
        """
        # Parse owner/repo from either a URL or a direct slug
        if "github.com/" in query:
            slug = query.split("github.com/")[-1].strip("/")
        else:
            slug = query.strip("/")

        parts = slug.split("/")
        if len(parts) < 2:
            logger.error(f"Invalid repository query: {query}")
            return {"error": f"Cannot parse owner/repo from: {query}"}

        owner, repo = parts[0], parts[1]
        repo_path = f"{owner}/{repo}"
        logger.info(f"Fetching repository intelligence: {repo_path}")

        try:
            # ── 1. Core repository metadata ──
            repo_resp = requests.get(
                f"https://api.github.com/repos/{repo_path}",
                headers=self.headers, timeout=10
            )
            if repo_resp.status_code != 200:
                logger.error(f"GitHub repo fetch failed: {repo_resp.status_code}")
                return {"error": f"Repository '{repo_path}' not found or inaccessible."}
            repo_data = repo_resp.json()

            license_info = repo_data.get("license") or {}

            # ── 2. Contributors (top 30 for meaningful analysis) ──
            contributors = []
            try:
                contrib_resp = requests.get(
                    f"https://api.github.com/repos/{repo_path}/contributors?per_page=30",
                    headers=self.headers, timeout=10
                )
                if contrib_resp.status_code == 200:
                    for c in contrib_resp.json():
                        contributors.append({
                            "login": c.get("login", ""),
                            "contributions": c.get("contributions", 0),
                            "type": c.get("type", "User"),
                        })
            except Exception:
                pass

            # ── 3. Language breakdown ──
            languages = {}
            try:
                lang_resp = requests.get(
                    f"https://api.github.com/repos/{repo_path}/languages",
                    headers=self.headers, timeout=10
                )
                if lang_resp.status_code == 200:
                    languages = lang_resp.json()
            except Exception:
                pass

            # ── 4. Recent commits (last 10) ──
            recent_commits = []
            try:
                commits_resp = requests.get(
                    f"https://api.github.com/repos/{repo_path}/commits?per_page=10",
                    headers=self.headers, timeout=10
                )
                if commits_resp.status_code == 200:
                    for c in commits_resp.json():
                        commit_info = c.get("commit", {})
                        recent_commits.append({
                            "sha": c.get("sha", "")[:7],
                            "message": commit_info.get("message", "").split("\n")[0][:120],
                            "author": commit_info.get("author", {}).get("name", ""),
                            "date": commit_info.get("author", {}).get("date", ""),
                        })
            except Exception:
                pass

            # ── 5. Releases (last 10) ──
            releases = []
            try:
                releases_resp = requests.get(
                    f"https://api.github.com/repos/{repo_path}/releases?per_page=10",
                    headers=self.headers, timeout=10
                )
                if releases_resp.status_code == 200:
                    for r in releases_resp.json():
                        releases.append({
                            "tag_name": r.get("tag_name", ""),
                            "name": r.get("name", ""),
                            "published_at": r.get("published_at", ""),
                            "prerelease": r.get("prerelease", False),
                        })
            except Exception:
                pass

            # ── 6. Open issues (last 10, with labels) ──
            open_issues_list = []
            try:
                issues_resp = requests.get(
                    f"https://api.github.com/repos/{repo_path}/issues?state=open&per_page=10&sort=updated",
                    headers=self.headers, timeout=10
                )
                if issues_resp.status_code == 200:
                    for iss in issues_resp.json():
                        # Skip pull requests (GitHub API mixes them in issues endpoint)
                        if "pull_request" in iss:
                            continue
                        open_issues_list.append({
                            "number": iss.get("number", 0),
                            "title": iss.get("title", "").strip()[:100],
                            "labels": [l.get("name", "") for l in iss.get("labels", [])],
                            "created_at": iss.get("created_at", ""),
                            "comments": iss.get("comments", 0),
                        })
            except Exception:
                pass

            # ── 7. Pull requests (last 10, open) ──
            pull_requests = []
            try:
                pr_resp = requests.get(
                    f"https://api.github.com/repos/{repo_path}/pulls?state=open&per_page=10&sort=updated",
                    headers=self.headers, timeout=10
                )
                if pr_resp.status_code == 200:
                    for pr in pr_resp.json():
                        pull_requests.append({
                            "number": pr.get("number", 0),
                            "title": pr.get("title", "").strip()[:100],
                            "user": pr.get("user", {}).get("login", ""),
                            "created_at": pr.get("created_at", ""),
                            "additions": pr.get("additions", 0),
                            "deletions": pr.get("deletions", 0),
                        })
            except Exception:
                pass

            # ── 8. README ──
            readme_content = ""
            try:
                readme_resp = requests.get(
                    f"https://api.github.com/repos/{repo_path}/readme",
                    headers={**self.headers, "Accept": "application/vnd.github.v3.raw"},
                    timeout=15
                )
                if readme_resp.status_code == 200:
                    readme_content = readme_resp.text[:8000]  # Limit for context
            except Exception:
                pass

            # ── 9. Project structure (root directory listing) ──
            root_contents = []
            try:
                contents_resp = requests.get(
                    f"https://api.github.com/repos/{repo_path}/contents/",
                    headers=self.headers, timeout=10
                )
                if contents_resp.status_code == 200:
                    for item in contents_resp.json():
                        root_contents.append({
                            "name": item.get("name", ""),
                            "type": item.get("type", ""),
                            "size": item.get("size", 0),
                        })
            except Exception:
                pass

            # ── 10. Dependencies (discoverable from common manifest files) ──
            dependencies: dict = {}
            manifest_files = [
                "package.json",
                "requirements.txt",
                "Cargo.toml",
                "go.mod",
                "pom.xml",
                "Gemfile",
                "build.gradle",
            ]
            for mf in manifest_files:
                try:
                    dep_resp = requests.get(
                        f"https://api.github.com/repos/{repo_path}/contents/{mf}",
                        headers={**self.headers, "Accept": "application/vnd.github.v3.raw"},
                        timeout=10
                    )
                    if dep_resp.status_code == 200 and dep_resp.text.strip():
                        dependencies[mf] = dep_resp.text[:4000]  # Limit per file
                        break  # Only fetch the first manifest found
                except Exception:
                    continue

            # ── 11. Computed fields ──
            from datetime import datetime, timezone
            created = repo_data.get("created_at", "")
            pushed = repo_data.get("pushed_at", "")
            age_days = 0
            if created:
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    age_days = (datetime.now(timezone.utc) - created_dt).days
                except Exception:
                    pass

            last_activity_days = 0
            if pushed:
                try:
                    pushed_dt = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
                    last_activity_days = (datetime.now(timezone.utc) - pushed_dt).days
                except Exception:
                    pass

            # Total open PRs count (from repo metadata, not the paginated list)
            open_prs_count = 0
            try:
                pr_search_resp = requests.get(
                    f"https://api.github.com/search/issues?q=repo:{repo_path}+type:pr+state:open&per_page=1",
                    headers=self.headers, timeout=10
                )
                if pr_search_resp.status_code == 200:
                    open_prs_count = pr_search_resp.json().get("total_count", 0)
            except Exception:
                pass

            return {
                # Core metadata
                "name": repo_data.get("full_name", repo_path),
                "description": repo_data.get("description", ""),
                "url": repo_data.get("html_url", f"https://github.com/{repo_path}"),
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "watchers": repo_data.get("watchers_count", 0),
                "open_issues": repo_data.get("open_issues_count", 0),
                "language": repo_data.get("language", ""),
                "topics": repo_data.get("topics", []),
                "license": license_info.get("spdx_id", "None"),
                "default_branch": repo_data.get("default_branch", "main"),
                "archived": repo_data.get("archived", False),
                "fork": repo_data.get("fork", False),
                # Computed fields
                "created_at": created,
                "pushed_at": pushed,
                "age_days": age_days,
                "last_activity_days": last_activity_days,
                # Detailed data
                "languages": languages,
                "topics": repo_data.get("topics", []),
                "contributors": contributors,
                "recent_commits": recent_commits,
                "releases": releases,
                "open_issues_list": open_issues_list,
                "open_prs_count": open_prs_count,
                "pull_requests": pull_requests,
                "readme": readme_content,
                "root_contents": root_contents,
                "dependencies": dependencies,
                # Counts for scoring
                "total_contributors": len(contributors),
                "total_releases": len(releases),
                "total_commits_fetched": len(recent_commits),
            }

        except Exception as e:
            logger.error(f"Repository intelligence fetch failed: {e}")
            return {"error": str(e)}

    def fetch_npm_package(self, package_name: str) -> dict:
        """Fetches npm package metadata + downloads."""
        logger.info(f"Fetching npm package: {package_name}")
        result: dict = {}
        try:
            registry_resp = requests.get(f"https://registry.npmjs.org/{requests.utils.quote(package_name)}", timeout=15)
            if registry_resp.status_code == 200:
                data = registry_resp.json()
                latest = data.get("dist-tags", {}).get("latest", "")
                repo_url = data.get("repository", {}).get("url", "") if isinstance(data.get("repository"), dict) else ""
                if isinstance(repo_url, str) and repo_url.startswith("git+"):
                    repo_url = repo_url[4:]
                if isinstance(repo_url, str) and repo_url.endswith(".git"):
                    repo_url = repo_url[:-4]

                dl_resp = requests.get(f"https://api.npmjs.org/downloads/point/last-week/{requests.utils.quote(package_name)}", timeout=10)
                weekly_dl = dl_resp.json().get("downloads", 0) if dl_resp.status_code == 200 else 0

                collector = SourceCollector()
                collector.add_source(
                    title=f"npm Package: {data.get('name', package_name)}",
                    url=f"https://www.npmjs.com/package/{data.get('name', package_name)}",
                    platform="npm",
                    source_type="package_registry",
                    snippet=f"Version: {latest} | Weekly Downloads: {weekly_dl:,} | Desc: {data.get('description', '')[:200]}"
                )
                collector.add_source(
                    title=f"npm Registry API: {package_name}",
                    url=f"https://registry.npmjs.org/{requests.utils.quote(package_name)}",
                    platform="npm",
                    source_type="rest_api",
                    snippet=f"Maintainers: {len(data.get('maintainers', []))} | License: {data.get('license', 'None')}"
                )
                if repo_url:
                    collector.add_source(
                        title=f"Package Repository: {data.get('name', package_name)}",
                        url=repo_url,
                        platform="github",
                        source_type="git_repository"
                    )

                result = {
                    "name": data.get("name"),
                    "description": data.get("description"),
                    "version": latest,
                    "repository": repo_url,
                    "maintainers_count": len(data.get("maintainers", [])),
                    "weekly_downloads": weekly_dl,
                    "sources": collector.get_sources()
                }
            return result
        except Exception as e:
            logger.error(f"npm package fetch failed: {e}")
            return {"error": str(e)}

