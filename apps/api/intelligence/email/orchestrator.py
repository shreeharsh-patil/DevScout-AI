"""
Email Intelligence Orchestrator.

Coordinates specialized agents through deterministic stages, isolating errors,
aggregating evidence, and generating production-quality intelligence reports.
"""

from __future__ import annotations

from typing import Callable, Optional
from loguru import logger
from sources import SourceCollector
from .agents import (
    AccountDiscoveryAgent,
    BreachExposureAgent,
    DeveloperFootprintAgent,
    UsernameCorrelationAgent,
    WebMentionAgent,
)
from .confidence import ConfidenceEngine
from .identity_resolver import IdentityResolverAgent
from .models import (
    ConfidenceAssessment,
    DeveloperFootprint,
    FindingStatus,
    IdentityFinding,
    IntelligenceReport,
)
from .reporter import EmailIntelligenceReporter
from .validator import EmailValidatorAgent


class EmailIntelligenceOrchestrator:
    """End-to-end orchestrator for autonomous Email Intelligence investigations."""

    def __init__(self, on_stage_change: Optional[Callable[[str], None]] = None):
        self.on_stage_change = on_stage_change
        self.validator = EmailValidatorAgent()
        self.account_discovery = AccountDiscoveryAgent()
        self.developer_footprint = DeveloperFootprintAgent()
        self.web_mentions = WebMentionAgent()
        self.breach_exposure = BreachExposureAgent()
        self.username_correlation = UsernameCorrelationAgent()
        self.identity_resolver = IdentityResolverAgent()
        self.reporter = EmailIntelligenceReporter()

    def _set_stage(self, stage: str):
        logger.info(f"[EmailIntelligence] Stage -> {stage}")
        if self.on_stage_change:
            try:
                self.on_stage_change(stage)
            except Exception as e:
                logger.debug(f"Error in on_stage_change callback: {e}")

    def execute(self, email_query: str) -> IntelligenceReport:
        source_collector = SourceCollector()

        # ── Stage 1: Validating Email ──
        self._set_stage("validating_email")
        target = self.validator.validate(email_query)

        if not target.is_valid:
            logger.warning(f"[EmailIntelligence] Email validation failed for '{email_query}': {target.validation_error}")
            empty_confidence = ConfidenceAssessment(
                level=FindingStatus.NO_EVIDENCE,
                score=0,
                reasons=[f"Validation Error: {target.validation_error}"]
            )
            report_md = (
                f"# \u274c Email Intelligence: Validation Failed\n\n"
                f"> **Query**: `{email_query}`  \n"
                f"> **Reason**: {target.validation_error}\n\n"
                f"Please provide a valid, well-formed email address (e.g. `developer@domain.com`)."
            )
            return IntelligenceReport(
                target=target,
                confidence=empty_confidence,
                report_markdown=report_md,
                status="failed",
                error=target.validation_error
            )

        email = target.normalized_email
        local_part = target.local_part
        domain = target.domain

        # ── Stage 2: Discovering Public Accounts ──
        self._set_stage("discovering_accounts")
        account_findings = []
        try:
            account_findings = self.account_discovery.discover_all(email, local_part, domain)
            for acc in account_findings:
                for ev in acc.evidence:
                    source_collector.add_source(
                        title=ev.title,
                        url=ev.url,
                        platform=ev.provider,
                        source_type=ev.source_type,
                        snippet=ev.snippet,
                        metadata=ev.raw_data
                    )
        except Exception as e:
            logger.warning(f"[EmailIntelligence] Account discovery error: {e}")

        # ── Stage 3: Searching Developer Sources ──
        self._set_stage("searching_developer_sources")
        footprint = None
        try:
            footprint = self.developer_footprint.build_footprint(email, local_part, domain, account_findings)
            for repo in footprint.repositories:
                source_collector.add_source(
                    title=f"GitHub Repository: {repo.full_name}",
                    url=repo.url,
                    platform="github",
                    source_type="code_repository",
                    snippet=repo.description or f"Stars: {repo.stars}, Language: {repo.language}"
                )
        except Exception as e:
            logger.warning(f"[EmailIntelligence] Developer footprint error: {e}")
            footprint = DeveloperFootprint()

        # ── Stage 4: Searching Public Web Mentions ──
        self._set_stage("searching_web")
        web_mentions_list = []
        try:
            web_mentions_list = self.web_mentions.discover_mentions(email, local_part)
            for m in web_mentions_list:
                source_collector.add_source(
                    title=m.title,
                    url=m.url,
                    platform="web",
                    source_type="search_index",
                    snippet=m.snippet
                )
        except Exception as e:
            logger.warning(f"[EmailIntelligence] Web mentions search error: {e}")

        # ── Stage 5: Checking Breach Disclosures ──
        self._set_stage("checking_breaches")
        breaches_list = []
        breach_status = "unavailable"
        try:
            breaches_list, breach_status = self.breach_exposure.check_exposure(email)
            if breaches_list:
                source_collector.add_source(
                    title="HaveIBeenPwned Security Disclosures",
                    url="https://haveibeenpwned.com",
                    platform="hibp",
                    source_type="security_audit",
                    snippet=f"Email verified in {len(breaches_list)} public breach disclosures."
                )
        except Exception as e:
            logger.warning(f"[EmailIntelligence] Breach audit error: {e}")

        # ── Stage 6: Correlating Identity Signals ──
        self._set_stage("correlating_identity")
        username_candidates = []
        identity_signals = None
        try:
            username_candidates = self.username_correlation.generate_candidates(local_part)
            identity_signals = self.identity_resolver.resolve(
                local_part, domain, account_findings, footprint, username_candidates
            )
        except Exception as e:
            logger.warning(f"[EmailIntelligence] Identity correlation error: {e}")
            identity_signals = IdentityFinding(
                provider="identity_resolver",
                finding_type="identity",
                status=FindingStatus.NO_EVIDENCE,
                confidence_level=FindingStatus.NO_EVIDENCE,
                confidence_score=0.0
            )

        # ── Stage 7: Confidence Assessment & Report Generation ──
        self._set_stage("generating_report")
        confidence = ConfidenceEngine.evaluate(
            account_findings=account_findings,
            web_mentions=web_mentions_list,
            breaches_count=len(breaches_list),
            has_domain_ownership=target.provider_type.value == "custom"
        )

        sources_normalized = source_collector.get_sources()

        report_markdown = self.reporter.generate_report(
            email=email,
            validation=target,
            confidence=confidence,
            accounts=account_findings,
            footprint=footprint,
            web_mentions=web_mentions_list,
            breaches=breaches_list,
            breach_status=breach_status,
            username_candidates=username_candidates,
            identity_signals=identity_signals,
            sources=sources_normalized
        )

        self._set_stage("completed")

        return IntelligenceReport(
            target=target,
            confidence=confidence,
            account_discovery=account_findings,
            developer_footprint=footprint,
            web_mentions=web_mentions_list,
            breaches=breaches_list,
            breach_status=breach_status,
            username_candidates=username_candidates,
            identity_signals=identity_signals,
            sources=sources_normalized,
            report_markdown=report_markdown,
            status="completed"
        )
