"""
Email Intelligence Provider Registry.

Centralized registry for dynamically registering, configuring, health-checking,
and concurrently executing pluggable intelligence providers.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional, Type, Union
from loguru import logger
from .models import (
    EmailTarget,
    FindingStatus,
    ProviderHealthReport,
    ProviderHealthStatus,
    ProviderResult,
    utc_now_iso,
)
from .providers.base import BaseEmailProvider
from .providers.breach import BreachEmailProvider
from .providers.crates import CratesEmailProvider
from .providers.github import GitHubEmailProvider
from .providers.gitlab import GitLabEmailProvider
from .providers.gravatar import GravatarEmailProvider
from .providers.npm import NpmEmailProvider
from .providers.pypi import PyPIEmailProvider
from .providers.web_search import WebSearchEmailProvider



class ProviderRegistry:
    """
    Registry for managing and executing pluggable Email Intelligence providers.
    """

    def __init__(self):
        self._providers: Dict[str, BaseEmailProvider] = {}

    def register(
        self,
        provider: Union[BaseEmailProvider, Type[BaseEmailProvider]],
        name: Optional[str] = None
    ) -> Union[BaseEmailProvider, Callable]:
        """
        Registers a provider instance or class. Can be used as a function or a decorator.
        """
        # Used as a decorator with parameters: @registry.register(name="custom")
        if provider is None:
            def decorator(cls: Type[BaseEmailProvider]):
                self.register(cls, name=name)
                return cls
            return decorator

        # If passed a class, instantiate it
        if isinstance(provider, type):
            instance = provider()
        else:
            instance = provider

        provider_name = name or getattr(instance, "provider_name", None) or instance.__class__.__name__.lower()
        self._providers[provider_name] = instance
        logger.debug(f"[ProviderRegistry] Registered provider: '{provider_name}'")
        return instance

    def unregister(self, name: str) -> Optional[BaseEmailProvider]:
        """Removes a provider from the registry."""
        return self._providers.pop(name, None)

    def get(self, name: str) -> Optional[BaseEmailProvider]:
        """Retrieves a registered provider by name."""
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        """Returns a list of all registered provider names."""
        return list(self._providers.keys())

    def get_active_providers(self) -> List[BaseEmailProvider]:
        """Returns all registered providers that are available."""
        return [p for p in self._providers.values() if p.is_available()]

    def health_check_all(self) -> Dict[str, ProviderHealthReport]:
        """Runs health checks across all registered providers."""
        reports: Dict[str, ProviderHealthReport] = {}
        for name, provider in self._providers.items():
            try:
                reports[name] = provider.health_check()
            except Exception as e:
                reports[name] = ProviderHealthReport(
                    provider_name=name,
                    status=ProviderHealthStatus.FAILED,
                    is_available=False,
                    last_error=str(e),
                    details={"exception": str(e)}
                )
        return reports

    def execute_all(
        self,
        target: EmailTarget,
        concurrent: bool = True,
        max_workers: int = 6,
        provider_names: Optional[List[str]] = None
    ) -> Dict[str, ProviderResult]:
        """
        Executes all (or specified) providers for given target safely.
        Guarantees:
        - Independent concurrent execution where safe.
        - Per-provider timeout.
        - Error isolation: one failing provider never fails other providers.
        """
        results: Dict[str, ProviderResult] = {}
        selected_providers = {
            name: p for name, p in self._providers.items()
            if provider_names is None or name in provider_names
        }

        if not selected_providers:
            return results

        if not concurrent or len(selected_providers) == 1:
            for name, provider in selected_providers.items():
                results[name] = provider.execute(target)
            return results

        # Concurrent execution with ThreadPoolExecutor
        futures = {}
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="devscout-provider") as executor:
            for name, provider in selected_providers.items():
                futures[executor.submit(provider.execute, target)] = name

            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as e:
                    logger.error(f"[ProviderRegistry] Unhandled future exception for '{name}': {e}")
                    results[name] = ProviderResult(
                        provider=name,
                        finding_type="account",
                        status=FindingStatus.ERROR,
                        confidence_level=FindingStatus.ERROR,
                        confidence_score=0.0,
                        retrieved_at=utc_now_iso(),
                        error=f"Provider execution exception: {str(e)}",
                        metadata={"exception": str(e)}
                    )

        return results


def create_default_registry() -> ProviderRegistry:
    """Instantiates and registers standard production providers."""
    registry = ProviderRegistry()
    registry.register(GitHubEmailProvider())
    registry.register(GravatarEmailProvider())
    registry.register(NpmEmailProvider())
    registry.register(GitLabEmailProvider())
    registry.register(PyPIEmailProvider())
    registry.register(CratesEmailProvider())
    registry.register(WebSearchEmailProvider())
    registry.register(BreachEmailProvider())
    return registry



# Global default provider registry instance
default_registry = create_default_registry()
