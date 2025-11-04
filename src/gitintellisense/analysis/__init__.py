"""
Analysis components for repository intelligence and opportunity detection.

This module provides sophisticated analysis capabilities including:
- Deep repository structure and pattern analysis
- Historical commit and maintainer behavior analysis
- AI-powered opportunity detection and scoring
- Contribution feasibility assessment

These components enable the system to understand repository dynamics
and identify meaningful contribution opportunities.
"""

from .repository import RepositoryIntelligence
from .patterns import PatternAnalyzer
from .opportunities import OpportunityDetector

__all__ = [
    "RepositoryIntelligence",
    "PatternAnalyzer",
    "OpportunityDetector",
]
