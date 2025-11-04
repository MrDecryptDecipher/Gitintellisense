"""
GitHub Repository Scanner and Automated Contribution System

A sophisticated AI-enhanced system that autonomously identifies, analyzes, and contributes
meaningful improvements to blockchain repositories, starting with Bitcoin Core.

This system demonstrates elite-level software engineering capabilities through:
- Meticulous planning and empirical rigor
- Surgical precision in implementation
- Professional-grade technical communication
- Comprehensive quality assurance and validation

Author: The Augster
Version: 1.0.0
License: MIT
"""

__version__ = "1.0.0"
__author__ = "The Augster"
__email__ = "augster@example.com"
__license__ = "MIT"

# Core imports for public API
from .core.analyzer import RepositoryAnalyzer
from .core.github_client import GitHubClient
from .core.ai_engine import AIEngine

# Analysis components
from .analysis.repository import RepositoryIntelligence
from .analysis.patterns import PatternAnalyzer
from .analysis.opportunities import OpportunityDetector

# Generation components
from .generation.pr_generator import PRGenerator
from .generation.templates import TemplateEngine
from .generation.validation import ValidationPipeline

# Utility components
from .utils.config import Config
from .utils.logging import setup_logging
from .utils.database import DatabaseManager

# Public API
__all__ = [
    # Core
    "RepositoryAnalyzer",
    "GitHubClient", 
    "AIEngine",
    
    # Analysis
    "RepositoryIntelligence",
    "PatternAnalyzer",
    "OpportunityDetector",
    
    # Generation
    "PRGenerator",
    "TemplateEngine",
    "ValidationPipeline",
    
    # Utils
    "Config",
    "setup_logging",
    "DatabaseManager",
    
    # Metadata
    "__version__",
    "__author__",
    "__email__",
    "__license__",
]

# Package-level configuration
import logging
import warnings

# Configure default logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Filter out deprecation warnings from dependencies
warnings.filterwarnings("ignore", category=DeprecationWarning, module="github")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="openai")

# Package initialization
def initialize_package():
    """Initialize the package with default configuration."""
    try:
        from .utils.config import Config
        from .utils.logging import setup_logging
        
        # Load configuration
        config = Config()
        
        # Setup logging
        setup_logging(config)
        
        return True
    except Exception as e:
        logging.getLogger(__name__).warning(f"Package initialization failed: {e}")
        return False

# Auto-initialize if possible
_initialized = initialize_package()

if not _initialized:
    logging.getLogger(__name__).info(
        "Package auto-initialization failed. Manual initialization may be required."
    )
