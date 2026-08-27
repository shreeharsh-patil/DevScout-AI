"""
Backward-compatible wrapper for BreachEmailProvider.
"""

from .breach import BreachEmailProvider, HIBPProvider

__all__ = ["BreachEmailProvider", "HIBPProvider"]
