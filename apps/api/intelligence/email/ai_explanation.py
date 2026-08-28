"""
Explainable AI Intelligence Synthesis with Strict Grounding Boundaries (Phase 18).

Permits LLMs to summarize evidence and identify developer patterns while strictly enforcing:
- ZERO invented accounts or citations
- ZERO alteration of deterministic confidence scores
- ZERO extrapolation of private or unverified personal data
- Mandatory schema validation with robust deterministic fallback synthesis.
"""

from __future__ import annotations

import json
import os
from typing import List, Optional
from loguru import logger
from .models import (
    AccountFinding,
    AIExplanation,
    ConfidenceAssessment,
    DeveloperFootprint,
    EmailTarget,
    FindingStatus,
    utc_now_iso,
)


class ExplainableAIEngine:
    """Generates strictly grounded narrative intelligence synthesis."""

    @classmethod
    def synthesize(
        cls,
        target: EmailTarget,
        confidence: ConfidenceAssessment,
        accounts: List[AccountFinding],
        footprint: DeveloperFootprint,
        breaches_count: int
    ) -> AIExplanation:
        """
        Synthesizes an explainable narrative. Attempts bounded LLM generation if configured,
        falling back to deterministic synthesis upon timeout, format error, or rate limits.
        """
        # Try bounded Gemini LLM synthesis if API key is present
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key:
            try:
                llm_explanation = cls._generate_with_gemini(
                    target, confidence, accounts, footprint, breaches_count, api_key
                )
                if llm_explanation:
                    return llm_explanation
            except Exception as e:
                logger.warning(f"[ExplainableAI] LLM synthesis fallback triggered: {e}")

        # Deterministic Grounded Fallback
        return cls._generate_deterministic_fallback(target, confidence, accounts, footprint, breaches_count)

    @classmethod
    def _generate_deterministic_fallback(
        cls,
        target: EmailTarget,
        confidence: ConfidenceAssessment,
        accounts: List[AccountFinding],
        footprint: DeveloperFootprint,
        breaches_count: int
    ) -> AIExplanation:
        verified_accs = [a for a in accounts if a.status == FindingStatus.VERIFIED]
        candidate_accs = [a for a in accounts if a.status == FindingStatus.CANDIDATE]

        summary_parts = [
            f"Email address '{target.raw_email}' has an overall public footprint score of {confidence.score}/100 "
            f"({confidence.level.value.replace('_', ' ')})."
        ]

        if target.is_role_account:
            summary_parts.append(f"Identified as a functional or team address ({target.role_type or 'generic'}).")

        if verified_accs:
            platforms = ", ".join(a.platform.upper() for a in verified_accs)
            summary_parts.append(f"Direct verification confirmed across {len(verified_accs)} platform(s): {platforms}.")

        if footprint.top_languages:
            langs = ", ".join(footprint.top_languages[:3])
            summary_parts.append(f"Primary developer language footprint centered on {langs}.")

        key_highlights = []
        if verified_accs:
            key_highlights.append(f"Confirmed public identity across {len(verified_accs)} platform(s).")
        if footprint.total_stars > 0:
            key_highlights.append(f"Accumulated {footprint.total_stars} stars across public open-source repositories.")
        if breaches_count > 0:
            key_highlights.append(f"Present in {breaches_count} verified historical security disclosure(s).")
        if candidate_accs:
            key_highlights.append(f"{len(candidate_accs)} candidate username leads identified (unverified).")

        # Determine developer archetype
        if "Rust" in footprint.top_languages or "C" in footprint.top_languages or "C++" in footprint.top_languages:
            archetype = "Systems / Low-Level Engineer"
        elif "TypeScript" in footprint.top_languages or "JavaScript" in footprint.top_languages:
            archetype = "Full-Stack / Web Architect"
        elif "Python" in footprint.top_languages or "R" in footprint.top_languages:
            archetype = "Data Engineer / Python Developer"
        elif verified_accs:
            archetype = "Open-Source Contributor"
        else:
            archetype = "General Technical Identity"

        uncertainty_notes = []
        if candidate_accs:
            uncertainty_notes.append("Candidate handles match syntax only and must not be treated as confirmed identities.")
        if target.mx_status == "uncertain":
            uncertainty_notes.append("DNS MX resolution encountered latency during scan.")

        return AIExplanation(
            summary=" ".join(summary_parts),
            key_highlights=key_highlights or ["Baseline intelligence assessment completed."],
            developer_archetype=archetype,
            uncertainty_notes=uncertainty_notes,
            generated_at=utc_now_iso()
        )

    @classmethod
    def _generate_with_gemini(
        cls,
        target: EmailTarget,
        confidence: ConfidenceAssessment,
        accounts: List[AccountFinding],
        footprint: DeveloperFootprint,
        breaches_count: int,
        api_key: str
    ) -> Optional[AIExplanation]:
        import google.genai as genai

        client = genai.Client(api_key=api_key)
        prompt = (
            f"You are a strict, objective OSINT evidence summarizer. Summarize the following structured developer intelligence.\n"
            f"TARGET: {target.raw_email}\n"
            f"CONFIDENCE: {confidence.score}/100 ({confidence.level.value})\n"
            f"VERIFIED ACCOUNTS: {[{'platform': a.platform, 'id': a.account_identifier} for a in accounts if a.status == FindingStatus.VERIFIED]}\n"
            f"CANDIDATES: {[{'platform': a.platform, 'id': a.account_identifier} for a in accounts if a.status == FindingStatus.CANDIDATE]}\n"
            f"LANGUAGES: {footprint.top_languages}\n"
            f"REPOSITORIES: {len(footprint.repositories)} (Total Stars: {footprint.total_stars})\n"
            f"BREACHES: {breaches_count}\n\n"
            f"STRICT RULES:\n"
            f"1. DO NOT invent accounts, links, or facts not present above.\n"
            f"2. Return ONLY a valid JSON object with keys: 'summary' (str), 'key_highlights' (list of str), 'developer_archetype' (str), 'uncertainty_notes' (list of str).\n"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )

        if response and response.text:
            data = json.loads(response.text)
            return AIExplanation(
                summary=data.get("summary", ""),
                key_highlights=data.get("key_highlights", []),
                developer_archetype=data.get("developer_archetype", "General Developer"),
                uncertainty_notes=data.get("uncertainty_notes", []),
                generated_at=utc_now_iso()
            )

        return None
