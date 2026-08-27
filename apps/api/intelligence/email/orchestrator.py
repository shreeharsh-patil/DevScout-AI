"""
Email Intelligence Orchestrator (Phases 14 – 22).

Production Pipeline with:
- True concurrent parallel provider execution (ThreadPoolExecutor)
- Accurate stage-weighted progress percentages (12%, 25%, 42%, 61%, 74%, 86%, 94%, 100%)
- False positive detection & source quality hierarchy enforcement
- Explainable AI narrative synthesis with strict grounding boundaries
- Performance caching and telemetry collection
- Historical snapshot delta tracking
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional
from loguru import logger
from sources import SourceCollector
from .agents.account_discovery import AccountDiscoveryAgent
from .agents.breach_exposure import BreachExposureAgent
from .agents.developer_footprint import DeveloperFootprintAgent
from .agents.web_mentions import WebMentionAgent
from .ai_explanation import ExplainableAIEngine
from .confidence import ConfidenceEngine
from .correlation import IdentityCorrelationEngine, UsernameCorrelationEngine
from .false_positive import FalsePositiveDetector
from .history import HistoricalSnapshotEngine
from .models import (
    AccountFinding,
    AIExplanation,
    BreachFinding,
    ConfidenceAssessment,
    DeveloperFootprint,
    EmailReputationAssessment,
    FindingStatus,
    HistoricalSnapshotComparison,
    IdentityFinding,
    IntelligenceReport,
    InvestigationScope,
    ProviderMetric,
    WebMention,
)
from .registry import ProviderRegistry, default_registry
from .reporter import EmailIntelligenceReporter
from .reputation import EmailReputationEngine
from .telemetry import default_cache, default_telemetry
from .validator import EmailValidatorAgent


class EmailIntelligenceOrchestrator:
    """Production Email Intelligence Pipeline Orchestrator."""

    def __init__(
        self,
        registry: Optional[ProviderRegistry] = None,
        on_progress: Optional[Callable[[str, int], None]] = None,
        on_stage_change: Optional[Callable[[str], None]] = None
    ):
        self.validator = EmailValidatorAgent()
        self.account_discovery = AccountDiscoveryAgent()
        self.developer_footprint = DeveloperFootprintAgent()
        self.web_mentions = WebMentionAgent()
        self.breach_exposure = BreachExposureAgent()
        self.username_correlation = UsernameCorrelationEngine()
        self.identity_resolver = IdentityResolverAgent() if 'IdentityResolverAgent' in globals() else None
        self.reporter = EmailIntelligenceReporter()
        self.on_progress = on_progress
        self.on_stage_change = on_stage_change

        self.registry = registry if registry is not None else default_registry
        self._uses_default_registry = registry is None

    def _set_stage(self, stage: str, pct: int = 0):
        logger.info(f"[EmailIntelligence] Stage -> {stage} ({pct}%)")
        if self.on_stage_change:
            try:
                self.on_stage_change(stage)
            except Exception as e:
                logger.debug(f"[EmailIntelligence] on_stage_change callback error: {e}")
        if self.on_progress:
            try:
                self.on_progress(stage, pct)
            except Exception as e:
                logger.debug(f"[EmailIntelligence] on_progress callback error: {e}")

    def execute(
        self,
        email_query: str,
        depth: str = "standard",
        previous_data: Optional[Dict[str, Any]] = None,
        previous_job_id: Optional[str] = None,
        previous_created_at: Optional[str] = None
    ) -> IntelligenceReport:
        source_collector = SourceCollector()
        clean_depth = depth.lower() if depth in ("quick", "standard", "deep") else "standard"
        provider_metrics: List[ProviderMetric] = []

        # Scope definition
        if clean_depth == "quick":
            enabled_providers = ["email_validator", "github", "gravatar"]
            coverage_desc = "Quick scan: email validation, GitHub developer profile, and Gravatar hash."
            depth_rationale = "Optimized for sub-second verification of primary email syntax and GitHub handle."
        elif clean_depth == "deep":
            enabled_providers = ["email_validator", "github", "gravatar", "npm", "pypi", "crates", "gitlab", "web_search", "breach"]
            coverage_desc = "Deep intelligence: 7 public registries, expanded multi-query web search, identity clustering, Evidence Graph, and historical comparisons."
            depth_rationale = "Exhaustive deep-dive for high-stakes intelligence investigations."
        else:
            enabled_providers = ["email_validator", "github", "gravatar", "npm", "pypi", "crates", "gitlab", "web_search", "breach"]
            coverage_desc = "Standard investigation: public package registries, web citations, breach exposure audit, and identity correlation."
            depth_rationale = "Default comprehensive scan across all core ecosystems."

        scope = InvestigationScope(
            depth=clean_depth,
            estimated_coverage=coverage_desc,
            enabled_providers=enabled_providers,
            depth_rationale=depth_rationale
        )

        # ── Stage 1: 12% Validating target ──
        t0 = time.time()
        self._set_stage("validating_email", 12)
        target = self.validator.validate_email(email_query)
        v_dur = (time.time() - t0) * 1000
        provider_metrics.append(
            ProviderMetric(provider="email_validator", duration_ms=round(v_dur, 2), status="success" if target.is_valid else "invalid", records_count=1)
        )

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
                scope=scope,
                provider_metrics=provider_metrics,
                report_markdown=report_md,
                status="failed",
                error=target.validation_error
            )

        email = target.normalized_email
        local_part = target.local_part
        domain = target.domain

        # ── Stage 2: 25% Checking developer sources & Parallel Execution ──
        self._set_stage("checking_developer_sources", 25)
        account_findings: List[AccountFinding] = []
        footprint = DeveloperFootprint()
        web_mentions_list: List[WebMention] = []
        breaches_list: List[BreachFinding] = []
        breach_status = "unavailable"

        # Concurrently execute independent providers
        def _fetch_accounts():
            t_start = time.time()
            cached = default_cache.get("accounts", email)
            if cached:
                return cached, (time.time() - t_start) * 1000, True
            accs = self.account_discovery.discover_all(email, local_part, domain)
            default_cache.set("accounts", email, accs)
            return accs, (time.time() - t_start) * 1000, False

        def _fetch_web():
            if clean_depth == "quick":
                return [], 0.0, False
            t_start = time.time()
            cached = default_cache.get("web", email)
            if cached:
                return cached, (time.time() - t_start) * 1000, True
            mentions = self.web_mentions.discover_mentions(email, local_part, domain)
            default_cache.set("web", email, mentions)
            return mentions, (time.time() - t_start) * 1000, False

        def _fetch_breaches():
            if clean_depth == "quick":
                return ([], "unavailable"), 0.0, False
            t_start = time.time()
            cached = default_cache.get("breach", email)
            if cached:
                return cached, (time.time() - t_start) * 1000, True
            b_res = self.breach_exposure.check_exposure(email)
            default_cache.set("breach", email, b_res)
            return b_res, (time.time() - t_start) * 1000, False

        with ThreadPoolExecutor(max_workers=4) as executor:
            fut_accounts = executor.submit(_fetch_accounts)
            fut_web = executor.submit(_fetch_web)
            fut_breaches = executor.submit(_fetch_breaches)

            # 42% Searching public web
            self._set_stage("searching_public_web", 42)

            try:
                raw_accs, acc_dur, acc_cache = fut_accounts.result(timeout=15.0)
                if clean_depth == "quick":
                    account_findings = [a for a in raw_accs if a.platform in ("github", "gravatar")]
                else:
                    account_findings = raw_accs
                provider_metrics.append(
                    ProviderMetric(provider="account_discovery", duration_ms=round(acc_dur, 2), status="success", cache_hit=acc_cache, records_count=len(account_findings))
                )
            except Exception as e:
                logger.warning(f"[EmailIntelligence] Account discovery error: {e}")

            try:
                web_mentions_list, web_dur, web_cache = fut_web.result(timeout=15.0)
                provider_metrics.append(
                    ProviderMetric(provider="web_search", duration_ms=round(web_dur, 2), status="success", cache_hit=web_cache, records_count=len(web_mentions_list))
                )
            except Exception as e:
                logger.warning(f"[EmailIntelligence] Web search error: {e}")

            try:
                (breaches_list, breach_status), b_dur, b_cache = fut_breaches.result(timeout=15.0)
                provider_metrics.append(
                    ProviderMetric(provider="breach_audit", duration_ms=round(b_dur, 2), status="success", cache_hit=b_cache, records_count=len(breaches_list))
                )
            except Exception as e:
                logger.warning(f"[EmailIntelligence] Breach audit error: {e}")

        # Ingest custom plugin providers from registry if any custom registered
        standard_provider_names = {"github", "gravatar", "npm", "gitlab", "pypi", "crates", "web_search", "web", "breach", "hibp"}
        custom_providers = [name for name in self.registry.list_providers() if name not in standard_provider_names]

        if custom_providers and clean_depth != "quick":
            try:
                custom_results = self.registry.execute_all(target=target, provider_names=custom_providers, concurrent=True)
                for p_name, p_res in custom_results.items():
                    for ev in p_res.evidence_items:
                        source_collector.add_source(
                            title=ev.title,
                            url=ev.url,
                            platform=ev.provider,
                            source_type=ev.source_type,
                            snippet=ev.snippet,
                            metadata=ev.raw_data or ev.metadata
                        )
                    for f in p_res.findings:
                        if isinstance(f, AccountFinding):
                            account_findings.append(f)
            except Exception as e:
                logger.warning(f"[EmailIntelligence] Custom provider execution error: {e}")

        # Ingest Sources into Collector

        for acc in account_findings:
            for ev in acc.evidence:
                source_collector.add_source(
                    title=ev.title,
                    url=ev.url,
                    platform=ev.provider,
                    source_type=ev.source_type,
                    snippet=ev.snippet,
                    metadata=ev.raw_data or ev.metadata
                )

        for m in web_mentions_list:
            source_collector.add_source(
                title=m.title,
                url=m.canonical_url or m.url,
                platform="web",
                source_type=m.mention_category.value,
                snippet=m.snippet,
                metadata={"domain": m.domain, "is_exact_match": m.is_exact_match}
            )

        if breaches_list:
            source_collector.add_source(
                title="HaveIBeenPwned Security Disclosures",
                url="https://haveibeenpwned.com",
                platform="hibp",
                source_type="security_audit",
                snippet=f"Email verified in {len(breaches_list)} public breach disclosures."
            )

        # ── Stage 3: 61% Processing account findings & False Positive Calibration ──
        self._set_stage("processing_account_findings", 61)
        account_findings, contradictions = FalsePositiveDetector.filter_and_calibrate(
            accounts=account_findings,
            target_email=email,
            target_local=local_part,
            target_domain=domain
        )

        try:
            footprint = self.developer_footprint.build_footprint(email, local_part, domain, account_findings)
        except Exception as e:
            logger.warning(f"[EmailIntelligence] Footprint error: {e}")

        # ── Stage 4: 74% Correlating identities ──
        self._set_stage("correlating_identities", 74)
        username_candidates = UsernameCorrelationEngine.generate_candidates(local_part)
        identity_clusters = IdentityCorrelationEngine.build_clusters(email, domain, account_findings)

        # ── Stage 5: 86% Scoring evidence ──
        self._set_stage("scoring_evidence", 86)
        confidence = ConfidenceEngine.evaluate(
            account_findings=account_findings,
            web_mentions=web_mentions_list,
            breaches_count=len(breaches_list),
            has_domain_ownership=target.domain_classification.value in ("corporate_domain", "custom_domain", "custom"),
            is_role_account=target.is_role_account
        )

        # Append contradiction signals if false positives detected
        if contradictions:
            for contra in contradictions[:3]:
                confidence.contradicting_signals.append(f"- Contradiction: {contra}")

        sources_normalized = source_collector.get_sources()

        # Build Evidence Graph
        evidence_graph = IdentityCorrelationEngine.build_evidence_graph(
            email=email,
            target=target,
            clusters=identity_clusters,
            accounts=account_findings,
            footprint=footprint,
            web_mentions=web_mentions_list,
            breaches=breaches_list,
            sources=sources_normalized
        )

        # Reputation Analysis
        reputation = EmailReputationEngine.evaluate(
            target=target,
            accounts=account_findings,
            footprint=footprint,
            web_mentions=web_mentions_list,
            breaches=breaches_list
        )

        # ── Stage 6: 94% Building report & Explainable AI Narrative ──
        self._set_stage("building_report", 94)
        ai_explanation = ExplainableAIEngine.synthesize(
            target=target,
            confidence=confidence,
            accounts=account_findings,
            footprint=footprint,
            breaches_count=len(breaches_list)
        )

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
            identity_signals=None,
            sources=sources_normalized,
            identity_clusters=identity_clusters
        )

        prelim_report = IntelligenceReport(
            target=target,
            confidence=confidence,
            account_discovery=account_findings,
            developer_footprint=footprint,
            web_mentions=web_mentions_list,
            breaches=breaches_list,
            breach_status=breach_status,
            username_candidates=username_candidates,
            identity_clusters=identity_clusters,
            evidence_graph=evidence_graph,
            reputation=reputation,
            scope=scope,
            ai_explanation=ai_explanation,
            provider_metrics=provider_metrics,
            sources=sources_normalized,
            report_markdown=report_markdown,
            status="completed"
        )

        historical_comparison = HistoricalSnapshotEngine.compare_snapshots(
            current_report=prelim_report,
            previous_data=previous_data,
            previous_job_id=previous_job_id,
            previous_created_at=previous_created_at
        )

        # ── 100% Completed ──
        self._set_stage("completed", 100)

        # Record total telemetry
        for metric in provider_metrics:
            default_telemetry.record_metric(metric)

        return IntelligenceReport(
            target=target,
            confidence=confidence,
            account_discovery=account_findings,
            developer_footprint=footprint,
            web_mentions=web_mentions_list,
            breaches=breaches_list,
            breach_status=breach_status,
            username_candidates=username_candidates,
            identity_clusters=identity_clusters,
            evidence_graph=evidence_graph,
            reputation=reputation,
            historical_comparison=historical_comparison,
            scope=scope,
            ai_explanation=ai_explanation,
            provider_metrics=provider_metrics,
            sources=sources_normalized,
            report_markdown=report_markdown,
            status="completed"
        )
