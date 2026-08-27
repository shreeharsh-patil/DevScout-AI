import hashlib
import os
import re
import time
import requests
import http_client
from loguru import logger
from dotenv import load_dotenv
from typing import Dict, List, Tuple

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

_gravatar_cache: dict = {}
_whois_cache: dict = {}
_hibp_cache: dict = {}
_web_cache: dict = {}

_CACHE_TTL = 600

# ---------------------------------------------------------------------------
# Confidence Category Constants
# ---------------------------------------------------------------------------
CONFIDENCE_VERIFIED = "verified"        # Direct cryptographic/API/profile confirmation
CONFIDENCE_PROBABLE = "probable"        # Strong multi-signal correlation (name + domain + bio)
CONFIDENCE_CANDIDATE = "candidate"      # Guessed handle or unverified mention (NO direct proof)
CONFIDENCE_NO_EVIDENCE = "no_evidence"  # Searched but no data found


def _cache_get(store: dict, key: str, ttl: int = _CACHE_TTL):
    entry = store.get(key)
    if entry:
        ts, data = entry
        if time.time() - ts < ttl:
            return data
        del store[key]
    return None


def _cache_set(store: dict, key: str, data):
    store[key] = (time.time(), data)


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validates email format strictly against RFC standard conventions.
    Returns (is_valid, error_reason).
    """
    if not email or not isinstance(email, str):
        return False, "Email address cannot be empty."

    email = email.strip()
    if len(email) > 254:
        return False, "Email address exceeds maximum length of 254 characters."

    pattern = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
    if not re.match(pattern, email):
        return False, f"Invalid email format: '{email}'."

    parts = email.split("@")
    if len(parts) != 2:
        return False, "Email must contain exactly one '@' character."

    local_part, domain = parts[0], parts[1]
    if len(local_part) > 64:
        return False, "Local part of email exceeds maximum length of 64 characters."

    if ".." in local_part or ".." in domain:
        return False, "Email cannot contain consecutive periods."

    domain_parts = domain.split(".")
    if len(domain_parts) < 2 or not all(domain_parts):
        return False, "Email domain must include a valid top-level domain."

    if len(domain_parts[-1]) < 2:
        return False, "Email top-level domain must be at least 2 characters long."

    return True, ""


class EmailOSINT:
    def __init__(self):
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            self.headers["Authorization"] = f"token {GITHUB_TOKEN}"

    def run_all(self, email: str) -> Dict:
        email = (email or "").strip()
        is_valid, val_err = validate_email(email)

        if not is_valid:
            logger.warning(f"Rejected invalid email in OSINT module: {email} ({val_err})")
            return {
                "email": email,
                "domain": "",
                "local_part": "",
                "status": "invalid_email",
                "validation_error": val_err,
                "confidence_category": CONFIDENCE_NO_EVIDENCE,
                "gravatar": {"has_profile": False, "confidence_category": CONFIDENCE_NO_EVIDENCE},
                "whois": {"has_data": False, "confidence_category": CONFIDENCE_NO_EVIDENCE},
                "breaches": [],
                "web_mentions": [],
                "social_profiles": [],
                "news_mentions": [],
                "pgp_keys": {"found": False, "confidence_category": CONFIDENCE_NO_EVIDENCE},
                "pastebin": [],
                "github": {
                    "accounts_found": 0,
                    "accounts": [],
                    "confirmed_accounts": [],
                    "candidate_accounts": [],
                    "confidence_category": CONFIDENCE_NO_EVIDENCE
                },
                "data_enrichment": {"possible_name": None, "possible_username": None},
                "sources_used": [],
                "profile_completeness": {
                    "score": 0,
                    "signals_found": 0,
                    "total_signals": 8,
                    "categorization": "none",
                    "confidence_category": CONFIDENCE_NO_EVIDENCE,
                    "verified_signals": [],
                    "candidate_signals": [],
                    "evidence_summary": f"Validation failed: {val_err}"
                }
            }

        domain = email.split("@")[-1]
        local = email.split("@")[0]

        results = {
            "email": email,
            "domain": domain,
            "local_part": local,
            "status": "valid",
            "validation_error": None,

            "gravatar": self._search_gravatar(email),
            "whois": self._search_whois(domain, email) if domain else {"has_data": False, "confidence_category": CONFIDENCE_NO_EVIDENCE},
            "breaches": self._search_breaches(email),
            "web_mentions": self._search_web_mentions(email),
            "social_profiles": self._search_social_platforms(email, local),
            "news_mentions": self._search_news(email),
            "pgp_keys": self._search_pgp(email),
            "pastebin": self._search_paste_sites(email),
            "github": self._search_github_osint(email, local, domain),
            "data_enrichment": self._enrich_from_public_data(email, local, domain),
            "sources_used": [
                "gravatar", "whois", "breaches", "web_mentions",
                "social_profiles", "news_mentions", "pgp_keys",
                "pastebin", "github", "data_enrichment"
            ]
        }

        results["profile_completeness"] = self._compute_completeness(results)
        results["confidence_category"] = results["profile_completeness"]["confidence_category"]

        # Collect normalized sources
        from sources import SourceCollector
        collector = SourceCollector()

        # 1. Gravatar
        if results.get("gravatar", {}).get("has_profile"):
            collector.add_source(
                title=f"Gravatar Profile: {results['gravatar'].get('display_name') or email}",
                url=results["gravatar"].get("profile_url") or f"https://gravatar.com/{hashlib.md5(email.strip().lower().encode()).hexdigest()}",
                platform="gravatar",
                source_type="avatar_registry",
                snippet=results["gravatar"].get("evidence", "Verified MD5 Gravatar profile match.")
            )

        # 2. WHOIS
        if results.get("whois", {}).get("has_data"):
            collector.add_source(
                title=f"RDAP WHOIS Domain Registry: {domain}",
                url=f"https://rdap.org/domain/{domain}",
                platform="whois",
                source_type="dns_whois",
                snippet=results["whois"].get("evidence", f"Domain registration record for {domain}.")
            )

        # 3. Breaches
        for b in results.get("breaches", []):
            collector.add_source(
                title=f"Breach Record: {b.get('name', 'Breach')}",
                url=f"https://haveibeenpwned.com/PwnedWebsites#{b.get('name', '')}",
                platform="hibp",
                source_type="breach_dump",
                snippet=b.get("evidence", f"Exposed in {b.get('name')} breach.")
            )

        # 4. GitHub confirmed & candidate accounts
        for acc in results.get("github", {}).get("confirmed_accounts", []):
            collector.add_source(
                title=f"GitHub Profile (Confirmed): {acc['login']}",
                url=acc.get("profile_url") or f"https://github.com/{acc['login']}",
                platform="github",
                source_type="user_profile",
                snippet=acc.get("evidence", "Confirmed GitHub account match.")
            )
        for acc in results.get("github", {}).get("candidate_accounts", []):
            collector.add_source(
                title=f"GitHub Candidate Lead (Unverified): {acc['login']}",
                url=acc.get("profile_url") or f"https://github.com/{acc['login']}",
                platform="github",
                source_type="candidate_lead",
                snippet=acc.get("evidence", "Inferred handle; unverified.")
            )

        # 5. PGP
        if results.get("pgp_keys", {}).get("found"):
            collector.add_source(
                title=f"OpenPGP Keyserver: {email}",
                url=f"https://keys.openpgp.org/search?q={requests.utils.quote(email)}",
                platform="openpgp",
                source_type="cryptographic_keyserver",
                snippet=results["pgp_keys"].get("evidence", "Public PGP key found.")
            )

        # 6. Web Mentions
        for wm in results.get("web_mentions", [])[:5]:
            if isinstance(wm, dict) and wm.get("url"):
                collector.add_source(
                    title=wm.get("title") or "Web Mention",
                    url=wm.get("url", ""),
                    platform="web",
                    source_type="search_result",
                    snippet=wm.get("snippet", "")
                )

        results["sources"] = collector.get_sources()
        return results


    def _compute_completeness(self, data: Dict) -> Dict:
        """
        Computes evidence-based confidence score and category.
        Candidate guesses DO NOT count towards verified confidence score.
        """
        verified_signals = []
        candidate_signals = []
        total_fields = 8

        # Gravatar
        if data.get("gravatar", {}).get("has_profile") and data.get("gravatar", {}).get("confidence_category") == CONFIDENCE_VERIFIED:
            verified_signals.append("gravatar_profile")

        # WHOIS
        whois_data = data.get("whois", {})
        if whois_data.get("has_data") and whois_data.get("confidence_category") in (CONFIDENCE_VERIFIED, CONFIDENCE_PROBABLE):
            verified_signals.append("domain_registration")

        # Breaches
        breaches = data.get("breaches", [])
        if any(b.get("confidence_category") == CONFIDENCE_VERIFIED for b in breaches):
            verified_signals.append("breach_records")

        # Web Mentions
        web_mentions = data.get("web_mentions", [])
        if any(w.get("confidence_category") == CONFIDENCE_PROBABLE for w in web_mentions):
            verified_signals.append("web_mentions")

        # Social Profiles
        social_profiles = data.get("social_profiles", [])
        for sp in social_profiles:
            if sp.get("confidence_category") in (CONFIDENCE_VERIFIED, CONFIDENCE_PROBABLE):
                if "social_media_presence" not in verified_signals:
                    verified_signals.append("social_media_presence")
            elif sp.get("confidence_category") == CONFIDENCE_CANDIDATE:
                if "candidate_social_media" not in candidate_signals:
                    candidate_signals.append("candidate_social_media")

        # News Mentions
        news = data.get("news_mentions", [])
        if any(n.get("confidence_category") == CONFIDENCE_PROBABLE for n in news):
            verified_signals.append("news_mentions")

        # GitHub Accounts (Strict separation)
        github_data = data.get("github", {})
        confirmed_gh = github_data.get("confirmed_accounts", [])
        candidate_gh = github_data.get("candidate_accounts", [])
        if confirmed_gh:
            verified_signals.append("github_presence")
        elif candidate_gh:
            candidate_signals.append("candidate_github_guess")

        # PGP Keys
        if data.get("pgp_keys", {}).get("found") and data.get("pgp_keys", {}).get("confidence_category") == CONFIDENCE_VERIFIED:
            verified_signals.append("pgp_key")

        # Pastebin
        if len(data.get("pastebin", [])) > 0:
            verified_signals.append("pastebin_mentions")

        verified_count = len(verified_signals)
        score = int((verified_count / total_fields) * 100)
        score = min(score, 100)

        if any(s in ("gravatar_profile", "github_presence", "pgp_key", "breach_records") for s in verified_signals):
            overall_category = CONFIDENCE_VERIFIED if verified_count >= 2 else CONFIDENCE_PROBABLE
        elif verified_count >= 1:
            overall_category = CONFIDENCE_PROBABLE
        elif candidate_signals:
            overall_category = CONFIDENCE_CANDIDATE
        else:
            overall_category = CONFIDENCE_NO_EVIDENCE

        categorization = (
            "high" if overall_category == CONFIDENCE_VERIFIED and score >= 40
            else "medium" if overall_category in (CONFIDENCE_VERIFIED, CONFIDENCE_PROBABLE) and score >= 20
            else "candidate" if overall_category == CONFIDENCE_CANDIDATE
            else "low" if verified_count > 0
            else "none"
        )

        return {
            "score": score,
            "signals_found": verified_count,
            "total_signals": total_fields,
            "categorization": categorization,
            "confidence_category": overall_category,
            "verified_signals": verified_signals,
            "candidate_signals": candidate_signals,
            "evidence_summary": f"Identified {verified_count} verified signal(s) and {len(candidate_signals)} candidate lead(s)."
        }


    def _search_gravatar(self, email: str) -> Dict:
        cached = _cache_get(_gravatar_cache, email)
        if cached is not None:
            return cached

        logger.info(f"Checking Gravatar for: {email}")
        result = {
            "has_profile": False,
            "avatar_url": None,
            "profile_url": None,
            "display_name": None,
            "confidence_category": CONFIDENCE_NO_EVIDENCE,
            "discovery_method": "gravatar_md5_hash",
            "evidence": "No Gravatar profile associated with email hash."
        }

        try:
            email_hash = hashlib.md5(email.strip().lower().encode()).hexdigest()
            result["hash"] = email_hash

            avatar_url = f"https://www.gravatar.com/avatar/{email_hash}?d=404&s=200"
            resp = http_client.get(avatar_url, timeout=8)
            if resp.status_code == 200:
                result["has_profile"] = True
                result["confidence_category"] = CONFIDENCE_VERIFIED
                result["avatar_url"] = f"https://www.gravatar.com/avatar/{email_hash}?s=400"
                result["profile_url"] = f"https://www.gravatar.com/{email_hash}"
                result["evidence"] = f"Cryptographic MD5 hash ({email_hash}) verified on Gravatar registry."

                profile_resp = http_client.get(
                    f"https://www.gravatar.com/{email_hash}.json",
                    timeout=8
                )
                if profile_resp.status_code == 200:
                    profile_data = profile_resp.json()
                    entry = profile_data.get("entry", [{}])[0]
                    result["display_name"] = entry.get("displayName") or entry.get("preferredUsername")
                    result["about_me"] = entry.get("aboutMe", "")
                    result["urls"] = [u.get("value") for u in entry.get("urls", []) if u.get("value")]
                    result["photos"] = [p.get("value") for p in entry.get("photos", []) if p.get("value")]

            _cache_set(_gravatar_cache, email, result)
        except Exception as e:
            logger.error(f"Gravatar search failed: {e}")

        return result

    def _search_whois(self, domain: str, target_email: str) -> Dict:
        cached = _cache_get(_whois_cache, domain)
        if cached is not None:
            return cached

        logger.info(f"Checking WHOIS for domain: {domain}")
        result = {
            "has_data": False,
            "confidence_category": CONFIDENCE_NO_EVIDENCE,
            "discovery_method": "rdap_whois",
            "evidence": "No WHOIS registration data accessible."
        }

        try:
            data = None
            whois_resp = http_client.get(
                f"https://rdap.verisign.com/com/v1/domain/{domain}",
                timeout=10
            )
            if whois_resp.status_code == 200:
                data = whois_resp.json()
            else:
                fallback = http_client.get(
                    f"https://www.rdap.net/domain/{domain}",
                    timeout=10
                )
                if fallback.status_code == 200:
                    data = fallback.json()

            if data:
                result["has_data"] = True
                result["confidence_category"] = CONFIDENCE_PROBABLE
                result["evidence"] = f"Public RDAP registration data for '{domain}' retrieved."

                entities = data.get("entities", [])
                for entity in entities:
                    vcard = entity.get("vcardArray", [])
                    if len(vcard) > 1:
                        for item in vcard[1]:
                            if len(item) >= 3:
                                field = item[0]
                                value = item[3]
                                if field == "fn":
                                    result["registrant_name"] = value
                                elif field == "org":
                                    result["registrant_org"] = value
                                elif field == "email":
                                    result["registrant_email"] = value
                                    if value.strip().lower() == target_email.strip().lower():
                                        result["confidence_category"] = CONFIDENCE_VERIFIED
                                        result["evidence"] = f"Registrant email '{value}' exactly matches target email."

                events = data.get("events", [])
                for event in events:
                    if event.get("eventAction") == "registration":
                        result["created_date"] = event.get("eventDate")
                    elif event.get("eventAction") == "expiration":
                        result["expiration_date"] = event.get("eventDate")

            _cache_set(_whois_cache, domain, result)
        except Exception as e:
            logger.error(f"WHOIS search failed: {e}")

        return result

    def _search_breaches(self, email: str) -> List[Dict]:
        cached = _cache_get(_hibp_cache, email)
        if cached is not None:
            return cached

        logger.info(f"Checking breaches for: {email}")
        results = []

        try:
            email_hash = hashlib.sha1(email.strip().lower().encode()).hexdigest().upper()
            prefix = email_hash[:5]
            suffix = email_hash[5:]

            hibp_resp = http_client.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                timeout=10,
                headers={"hibp-api-key": os.getenv("HIBP_API_KEY", "")}
            )
            if hibp_resp.status_code == 200:
                hashes = hibp_resp.text.splitlines()
                for line in hashes:
                    if line.startswith(suffix):
                        count = int(line.split(":")[1]) if ":" in line else 1
                        results.append({
                            "name": "Data Breach (Pwned Passwords match)",
                            "count": count,
                            "source": "haveibeenpwned",
                            "confidence_category": CONFIDENCE_VERIFIED,
                            "discovery_method": "k-anonymity_sha1_hash",
                            "evidence": f"K-Anonymity SHA-1 hash prefix {prefix} matched breach database ({count} occurrences)."
                        })

            breach_resp = http_client.get(
                f"https://haveibeenpwned.com/api/v3/breachedaccount/{requests.utils.quote(email)}?truncateResponse=true",
                timeout=10,
                headers={
                    "hibp-api-key": os.getenv("HIBP_API_KEY", ""),
                    "user-agent": "DevScoutAI/2.0"
                }
            )
            if breach_resp.status_code == 200:
                breaches = breach_resp.json()
                for b in breaches:
                    results.append({
                        "name": b.get("Name", "Unknown Breach"),
                        "domain": b.get("Domain", ""),
                        "breach_date": b.get("BreachDate", ""),
                        "data_classes": b.get("DataClasses", []),
                        "source": "haveibeenpwned",
                        "confidence_category": CONFIDENCE_VERIFIED,
                        "discovery_method": "hibp_account_lookup",
                        "evidence": f"Account '{email}' listed in '{b.get('Name')}' breach dataset."
                    })

            _cache_set(_hibp_cache, email, results)
        except Exception as e:
            logger.error(f"Breach search failed: {e}")

        return results

    def _search_web_mentions(self, email: str) -> List[Dict]:
        cached = _cache_get(_web_cache, f"web_{email}")
        if cached is not None:
            return cached

        logger.info(f"Searching web for: {email}")
        results = []

        try:
            search_url = f"https://s.jina.ai/{requests.utils.quote(email)}"
            resp = http_client.get(search_url, timeout=30)
            if resp.status_code == 200:
                raw = resp.text
                mentions = self._parse_search_results(raw, email)
                results.extend(mentions)

            encoded_email = requests.utils.quote(f'"{email}"')
            search_url2 = f"https://s.jina.ai/{encoded_email}"
            resp2 = http_client.get(search_url2, timeout=30)
            if resp2.status_code == 200 and resp2.text != raw:
                mentions2 = self._parse_search_results(resp2.text, email)
                existing_titles = {r.get("title") for r in results}
                for m in mentions2:
                    if m.get("title") not in existing_titles:
                        results.append(m)

            _cache_set(_web_cache, f"web_{email}", results)
        except Exception as e:
            logger.error(f"Web search failed: {e}")

        return results

    def _parse_search_results(self, text: str, email: str) -> List[Dict]:
        mentions = []
        lines = text.split("\n")
        current_title = None
        current_url = None
        current_snippet = None

        for line in lines:
            if line.startswith("Title:") or line.startswith("## "):
                if current_title and current_url:
                    mentions.append({
                        "title": current_title,
                        "url": current_url,
                        "snippet": (current_snippet or "")[:300],
                        "source": "web_search",
                        "confidence_category": CONFIDENCE_PROBABLE if email.lower() in (current_snippet or "").lower() else CONFIDENCE_CANDIDATE,
                        "discovery_method": "web_search_mention",
                        "evidence": f"Indexed web page mentions email query string '{email}'."
                    })
                current_title = line.replace("Title:", "").replace("##", "").strip()
                current_url = None
                current_snippet = None
            elif line.startswith("URL:") or line.startswith("http"):
                if line.startswith("URL:"):
                    current_url = line.replace("URL:", "").strip()
                elif current_url is None:
                    potential_url = line.strip()
                    if potential_url.startswith("http"):
                        current_url = potential_url
            elif email.lower() in line.lower() and len(line.strip()) > 10:
                snippet = line.strip()
                current_snippet = (current_snippet or "") + " " + snippet

        if current_title and current_url:
            mentions.append({
                "title": current_title,
                "url": current_url,
                "snippet": (current_snippet or "")[:300],
                "source": "web_search",
                "confidence_category": CONFIDENCE_PROBABLE if email.lower() in (current_snippet or "").lower() else CONFIDENCE_CANDIDATE,
                "discovery_method": "web_search_mention",
                "evidence": f"Indexed web page mentions email query string '{email}'."
            })

        return mentions[:15]

    def _search_social_platforms(self, email: str, local: str) -> List[Dict]:
        logger.info(f"Searching social platforms for: {email}")
        results = []

        platforms = [
            ("Twitter/X", f"https://s.jina.ai/site:twitter.com {email}"),
            ("LinkedIn", f"https://s.jina.ai/site:linkedin.com/in/ {email}"),
            ("Facebook", f"https://s.jina.ai/site:facebook.com {email}"),
            ("Reddit", f"https://s.jina.ai/site:reddit.com {email}"),
            ("Stack Overflow", f"https://s.jina.ai/site:stackoverflow.com/users {email}"),
            ("Medium", f"https://s.jina.ai/site:medium.com/@{local} {email}"),
            ("Keybase", f"https://s.jina.ai/site:keybase.io {email}"),
        ]

        for platform_name, search_url in platforms:
            try:
                resp = http_client.get(search_url, timeout=25)
                if resp.status_code == 200 and email.lower() in resp.text.lower():
                    lines = resp.text.split("\n")
                    title = ""
                    url = ""
                    for line in lines:
                        if line.startswith("Title:"):
                            title = line.replace("Title:", "").strip()
                        elif line.startswith("URL:"):
                            url = line.replace("URL:", "").strip()

                    results.append({
                        "platform": platform_name,
                        "title": title or platform_name,
                        "url": url or "",
                        "source": "social_search",
                        "confidence_category": CONFIDENCE_PROBABLE,
                        "is_confirmed": True,
                        "discovery_method": "targeted_social_search",
                        "evidence": f"Platform search for {platform_name} returned public content referencing '{email}'."
                    })
            except Exception as e:
                logger.error(f"Social search for {platform_name} failed: {e}")

        return results

    def _search_news(self, email: str) -> List[Dict]:
        logger.info(f"Searching news for: {email}")
        results = []

        try:
            search_query = f"site:news.ycombinator.com {email}"
            resp = http_client.get(
                f"https://s.jina.ai/{requests.utils.quote(search_query)}",
                timeout=25
            )
            if resp.status_code == 200:
                for mention in self._parse_search_results(resp.text, email):
                    mention["source"] = "news"
                    results.append(mention)

            search_query2 = f"site:techcrunch.com {email}"
            resp2 = http_client.get(
                f"https://s.jina.ai/{requests.utils.quote(search_query2)}",
                timeout=25
            )
            if resp2.status_code == 200:
                existing = {r.get("url") for r in results}
                for mention in self._parse_search_results(resp2.text, email):
                    if mention.get("url") not in existing:
                        mention["source"] = "news"
                        results.append(mention)

        except Exception as e:
            logger.error(f"News search failed: {e}")

        return results

    def _search_pgp(self, email: str) -> Dict:
        logger.info(f"Searching PGP keys for: {email}")
        result = {
            "found": False,
            "keys": [],
            "confidence_category": CONFIDENCE_NO_EVIDENCE,
            "discovery_method": "openpgp_keyserver",
            "evidence": "No public PGP key found."
        }

        try:
            pgp_resp = http_client.get(
                f"https://keyserver.ubuntu.com/pks/lookup?op=index&search={requests.utils.quote(email)}",
                timeout=15,
                headers={"user-agent": "DevScoutAI/2.0"}
            )
            if pgp_resp.status_code == 200 and email.lower() in pgp_resp.text.lower():
                result["found"] = True
                result["confidence_category"] = CONFIDENCE_VERIFIED
                result["evidence"] = f"OpenPGP key registered with UID matching '{email}' on Ubuntu keyserver."
                result["keys"].append({
                    "source": "keyserver.ubuntu.com",
                    "note": f"PGP key verified for {email}",
                    "confidence_category": CONFIDENCE_VERIFIED
                })

        except Exception as e:
            logger.error(f"PGP search failed: {e}")

        return result

    def _search_paste_sites(self, email: str) -> List[Dict]:
        logger.info(f"Searching paste sites for: {email}")
        results = []

        try:
            search_query = f"site:pastebin.com {email}"
            resp = http_client.get(
                f"https://s.jina.ai/{requests.utils.quote(search_query)}",
                timeout=25
            )
            if resp.status_code == 200:
                for mention in self._parse_search_results(resp.text, email):
                    mention["source"] = "pastebin"
                    results.append(mention)

        except Exception as e:
            logger.error(f"Paste site search failed: {e}")

        return results

    def _search_github_osint(self, email: str, local: str, domain: str) -> Dict:
        logger.info(f"Running GitHub OSINT for: {email}")
        found_logins: set = set()
        confirmed_accounts: list = []
        candidate_accounts: list = []

        # Strategy 1: Public Commit Search (VERIFIED - exact author email)
        try:
            commit_headers = {
                **self.headers,
                "Accept": "application/vnd.github.cloak-preview+json",
            }
            commit_resp = http_client.get(
                f"https://api.github.com/search/commits?q=author-email:{email}&per_page=10&sort=author-date",
                headers=commit_headers,
                timeout=15,
            )
            if commit_resp.status_code == 200:
                commits = commit_resp.json().get("items", [])
                account_map = {}
                for item in commits:
                    author = item.get("author")
                    committer = item.get("committer")
                    for actor in [author, committer]:
                        if actor and actor.get("login") and actor["login"] not in found_logins:
                            found_logins.add(actor["login"])
                            account_map[actor["login"]] = actor

                for a in account_map.values():
                    login = a["login"]
                    acc_obj = {
                        "login": login,
                        "avatar_url": a.get("avatar_url", ""),
                        "type": a.get("type", "User"),
                        "strategy": "commit_search",
                        "discovery_method": "commit_author_email",
                        "confidence_category": CONFIDENCE_VERIFIED,
                        "is_confirmed": True,
                        "confidence": "Verified (Public Commit History â€” exact author email match)",
                        "evidence": f"Commit author/committer email in GitHub repository history directly matches '{email}'.",
                        "profile_url": f"https://github.com/{login}"
                    }
                    confirmed_accounts.append(acc_obj)
        except Exception as e:
            logger.error(f"GitHub commit search failed: {e}")

        # Strategy 2: Profile Email Match (VERIFIED - public email on profile)
        try:
            profile_resp = http_client.get(
                f"https://api.github.com/search/users?q={requests.utils.quote(email)}+in:email&per_page=5",
                headers=self.headers,
                timeout=10,
            )
            if profile_resp.status_code == 200:
                for user in profile_resp.json().get("items", []):
                    login = user.get("login", "")
                    if login and login not in found_logins:
                        found_logins.add(login)
                        acc_obj = {
                            "login": login,
                            "avatar_url": user.get("avatar_url", ""),
                            "type": user.get("type", "User"),
                            "strategy": "email_match",
                            "discovery_method": "profile_email_search",
                            "confidence_category": CONFIDENCE_VERIFIED,
                            "is_confirmed": True,
                            "confidence": "Verified (Profile Email Match â€” public email on profile)",
                            "evidence": f"GitHub user profile explicitly lists matching email '{email}'.",
                            "profile_url": f"https://github.com/{login}"
                        }
                        confirmed_accounts.append(acc_obj)
        except Exception as e:
            logger.error(f"GitHub profile search failed: {e}")

        # Strategy 3: Username Prefix Guessing (CANDIDATE ONLY unless corroborating evidence exists)
        try:
            candidates = set()
            candidates.add(local)
            candidates.add(local.replace(".", ""))
            candidates.add(local.replace(".", "-"))
            candidates.add(local.replace("_", "-"))

            for candidate in candidates:
                if not candidate or candidate in found_logins:
                    continue
                try:
                    guess_resp = http_client.get(
                        f"https://api.github.com/users/{requests.utils.quote(candidate)}",
                        headers=self.headers,
                        timeout=8,
                    )
                    if guess_resp.status_code == 200:
                        user = guess_resp.json()
                        login = user.get("login", "")
                        if login and login not in found_logins:
                            found_logins.add(login)
                            user_email = (user.get("email") or "").strip().lower()
                            user_bio = (user.get("bio") or "").lower()
                            user_blog = (user.get("blog") or "").lower()
                            user_company = (user.get("company") or "").lower()

                            if user_email == email.lower():
                                acc_obj = {
                                    "login": login,
                                    "avatar_url": user.get("avatar_url", ""),
                                    "type": user.get("type", "User"),
                                    "strategy": "username_guess_verified",
                                    "discovery_method": "inferred_handle_with_matching_email",
                                    "confidence_category": CONFIDENCE_VERIFIED,
                                    "is_confirmed": True,
                                    "confidence": "Verified (Inferred Handle with matching profile email)",
                                    "evidence": f"GitHub profile for '{login}' matches email prefix and contains exact matching email '{email}'.",
                                    "profile_url": f"https://github.com/{login}"
                                }
                                confirmed_accounts.append(acc_obj)
                            elif domain and (domain.lower() in user_bio or domain.lower() in user_blog or domain.lower() in user_company):
                                acc_obj = {
                                    "login": login,
                                    "avatar_url": user.get("avatar_url", ""),
                                    "type": user.get("type", "User"),
                                    "strategy": "username_guess_correlated",
                                    "discovery_method": "inferred_handle_with_domain_correlation",
                                    "confidence_category": CONFIDENCE_PROBABLE,
                                    "is_confirmed": True,
                                    "confidence": "Probable (Inferred Handle with matching domain in bio/blog)",
                                    "evidence": f"GitHub handle '{login}' matches email prefix, and profile bio/blog references '{domain}'.",
                                    "profile_url": f"https://github.com/{login}"
                                }
                                confirmed_accounts.append(acc_obj)
                            else:
                                acc_obj = {
                                    "login": login,
                                    "avatar_url": user.get("avatar_url", ""),
                                    "type": user.get("type", "User"),
                                    "strategy": "username_guess_unverified",
                                    "discovery_method": "unverified_handle_prefix_guess",
                                    "confidence_category": CONFIDENCE_CANDIDATE,
                                    "is_confirmed": False,
                                    "confidence": "Candidate (Unverified Guess â€” handle matches email prefix only)",
                                    "evidence": f"GitHub handle '{login}' matches email prefix '{candidate}', but no cryptographic or email link was verified. Treat as an unconfirmed candidate lead only.",
                                    "profile_url": f"https://github.com/{login}"
                                }
                                candidate_accounts.append(acc_obj)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"GitHub username guessing failed: {e}")

        all_accounts = confirmed_accounts + candidate_accounts

        overall_gh_confidence = (
            CONFIDENCE_VERIFIED if any(a["confidence_category"] == CONFIDENCE_VERIFIED for a in confirmed_accounts)
            else CONFIDENCE_PROBABLE if confirmed_accounts
            else CONFIDENCE_CANDIDATE if candidate_accounts
            else CONFIDENCE_NO_EVIDENCE
        )

        return {
            "accounts_found": len(all_accounts),
            "confirmed_accounts_count": len(confirmed_accounts),
            "candidate_accounts_count": len(candidate_accounts),
            "confidence_category": overall_gh_confidence,
            "confirmed_accounts": confirmed_accounts,
            "candidate_accounts": candidate_accounts,
            "accounts": all_accounts
        }

    def _enrich_from_public_data(self, email: str, local: str, domain: str) -> Dict:
        logger.info(f"Enriching from public data for: {email}")
        result = {
            "possible_name": None,
            "possible_username": None,
            "possible_domain_owner": None,
            "associated_domains": [],
            "confidence_category": CONFIDENCE_PROBABLE if domain else CONFIDENCE_NO_EVIDENCE,
            "discovery_method": "heuristic_decomposition",
            "evidence": "Extracted name and domain hints from email syntax."
        }

        result["possible_username"] = local

        name_hints = re.split(r'[._\-\d+]', local)
        meaningful = [p for p in name_hints if len(p) > 2 and not p.isdigit()]
        if meaningful:
            result["possible_name"] = " ".join(meaningful).title()

        try:
            domain_authority = ".".join(domain.split(".")[-2:]) if "." in domain else domain
            company_resp = http_client.get(
                f"https://s.jina.ai/{requests.utils.quote(domain_authority + ' about company crunchbase')}",
                timeout=20
            )
            if company_resp.status_code == 200:
                text = company_resp.text[:2000]
                lines = text.split("\n")
                for line in lines:
                    lower = line.lower()
                    if "crunchbase" in lower or "linkedin.com/company" in lower:
                        result["associated_domains"].append({
                            "type": "company_profile_hint",
                            "url": line.replace("URL:", "").strip() if "URL:" in line else "",
                            "confidence_category": CONFIDENCE_PROBABLE
                        })
                        break
        except Exception as e:
            logger.error(f"Domain enrichment failed: {e}")

        return result

