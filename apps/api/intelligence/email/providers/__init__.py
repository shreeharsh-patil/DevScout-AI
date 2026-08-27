"""
Email Intelligence Provider Plugins.

Exports all pluggable provider adapters and base interfaces.
"""

from .base import BaseEmailProvider, BaseProvider
from .breach import BreachEmailProvider, HIBPProvider
from .crates import CratesEmailProvider, CratesProvider
from .github import GitHubEmailProvider, GitHubProvider
from .gitlab import GitLabEmailProvider, GitLabProvider
from .gravatar import GravatarEmailProvider, GravatarProvider
from .npm import NpmEmailProvider, NpmProvider
from .pypi import PyPIEmailProvider, PyPIProvider
from .web_search import WebSearchEmailProvider, WebSearchProvider

__all__ = [
    "BaseEmailProvider",
    "BaseProvider",
    "GitHubEmailProvider",
    "GitHubProvider",
    "GravatarEmailProvider",
    "GravatarProvider",
    "NpmEmailProvider",
    "NpmProvider",
    "GitLabEmailProvider",
    "GitLabProvider",
    "PyPIEmailProvider",
    "PyPIProvider",
    "CratesEmailProvider",
    "CratesProvider",
    "WebSearchEmailProvider",
    "WebSearchProvider",
    "BreachEmailProvider",
    "HIBPProvider",
]
