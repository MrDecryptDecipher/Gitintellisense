"""
Core components for the GitHub Repository Scanner and Automated Contribution System.

This module contains the fundamental building blocks of the system:
- Repository analysis engine
- GitHub API client with advanced features
- AI-powered analysis and generation engine

These components work together to provide sophisticated repository intelligence
and automated contribution capabilities.
"""

from .analyzer import RepositoryAnalyzer
from .github_client import GitHubClient
from .ai_engine import AIEngine

__all__ = [
    "RepositoryAnalyzer",
    "GitHubClient", 
    "AIEngine",
]
