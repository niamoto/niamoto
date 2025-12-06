"""
Auto-discovery matching system for transformers and widgets.

This module implements the SmartMatcher system that automatically discovers
compatible widgets for transformers based on their output/input contracts.
"""

from .matcher import SmartMatcher, WidgetSuggestion

__all__ = ["SmartMatcher", "WidgetSuggestion"]
