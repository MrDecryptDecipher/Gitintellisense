"""
Logging system for the GitHub Repository Scanner and Automated Contribution System.

This module provides structured logging with multiple transports and specialized methods
for GitHub analysis activities, integrating with existing infrastructure patterns.
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import structlog
from rich.console import Console
from rich.logging import RichHandler

from .config import Config, get_config


class GitIntellisenseLogger:
    """
    Custom logger class that provides structured logging with multiple transports
    and specialized methods for GitHub analysis activities.
    """
    
    def __init__(self, name: str, config: Optional[Config] = None):
        """Initialize the logger with configuration."""
        self.name = name
        self.config = config or get_config()
        self.console = Console()
        
        # Initialize structured logger
        self._setup_structlog()
        self.logger = structlog.get_logger(name)
    
    def _setup_structlog(self) -> None:
        """Set up structured logging configuration."""
        # Configure processors
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
        
        # Add JSON processor for structured output
        if self.config.logging.format.lower() == "json":
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())
        
        # Configure structlog
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    def _get_log_level(self) -> int:
        """Get the numeric log level."""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        return level_map.get(self.config.get_log_level().upper(), logging.INFO)
    
    def _setup_file_handler(self) -> logging.Handler:
        """Set up file handler with rotation."""
        log_file = Path(self.config.logging.file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Parse max size
        max_size = self.config.logging.max_size
        if max_size.endswith("MB"):
            max_bytes = int(max_size[:-2]) * 1024 * 1024
        elif max_size.endswith("KB"):
            max_bytes = int(max_size[:-2]) * 1024
        else:
            max_bytes = int(max_size)
        
        handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=self.config.logging.backup_count,
            encoding="utf-8"
        )
        
        # Set formatter
        if self.config.logging.format.lower() == "json":
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        
        handler.setFormatter(formatter)
        handler.setLevel(self._get_log_level())
        
        return handler
    
    def _setup_console_handler(self) -> logging.Handler:
        """Set up console handler with rich formatting."""
        if self.config.development.debug:
            handler = RichHandler(
                console=self.console,
                show_time=True,
                show_level=True,
                show_path=True,
                rich_tracebacks=True,
            )
        else:
            handler = logging.StreamHandler(sys.stdout)
        
        handler.setLevel(self._get_log_level())
        return handler
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback."""
        self.logger.exception(message, **kwargs)
    
    # Specialized logging methods for GitHub analysis activities
    
    def github_api_call(self, endpoint: str, method: str = "GET", **kwargs) -> None:
        """Log GitHub API call."""
        self.info(
            "GitHub API call",
            endpoint=endpoint,
            method=method,
            activity_type="github_api",
            **kwargs
        )
    
    def github_rate_limit(self, remaining: int, reset_time: datetime, **kwargs) -> None:
        """Log GitHub rate limit status."""
        self.info(
            "GitHub rate limit status",
            remaining=remaining,
            reset_time=reset_time.isoformat(),
            activity_type="rate_limit",
            **kwargs
        )
    
    def repository_analysis_start(self, repo: str, **kwargs) -> None:
        """Log start of repository analysis."""
        self.info(
            "Starting repository analysis",
            repository=repo,
            activity_type="analysis_start",
            **kwargs
        )
    
    def repository_analysis_complete(self, repo: str, duration: float, **kwargs) -> None:
        """Log completion of repository analysis."""
        self.info(
            "Repository analysis complete",
            repository=repo,
            duration_seconds=duration,
            activity_type="analysis_complete",
            **kwargs
        )
    
    def opportunity_detected(self, repo: str, opportunity_type: str, score: float, **kwargs) -> None:
        """Log detected contribution opportunity."""
        self.info(
            "Contribution opportunity detected",
            repository=repo,
            opportunity_type=opportunity_type,
            score=score,
            activity_type="opportunity_detected",
            **kwargs
        )
    
    def ai_analysis_start(self, model: str, prompt_length: int, **kwargs) -> None:
        """Log start of AI analysis."""
        self.info(
            "Starting AI analysis",
            model=model,
            prompt_length=prompt_length,
            activity_type="ai_analysis_start",
            **kwargs
        )
    
    def ai_analysis_complete(self, model: str, tokens_used: int, duration: float, **kwargs) -> None:
        """Log completion of AI analysis."""
        self.info(
            "AI analysis complete",
            model=model,
            tokens_used=tokens_used,
            duration_seconds=duration,
            activity_type="ai_analysis_complete",
            **kwargs
        )
    
    def contribution_generated(self, repo: str, contribution_type: str, **kwargs) -> None:
        """Log generated contribution."""
        self.info(
            "Contribution generated",
            repository=repo,
            contribution_type=contribution_type,
            activity_type="contribution_generated",
            **kwargs
        )
    
    def pr_created(self, repo: str, pr_number: int, pr_url: str, **kwargs) -> None:
        """Log created pull request."""
        self.info(
            "Pull request created",
            repository=repo,
            pr_number=pr_number,
            pr_url=pr_url,
            activity_type="pr_created",
            **kwargs
        )
    
    def validation_result(self, validation_type: str, passed: bool, details: Dict[str, Any], **kwargs) -> None:
        """Log validation result."""
        level = "info" if passed else "warning"
        getattr(self, level)(
            f"Validation {validation_type} {'passed' if passed else 'failed'}",
            validation_type=validation_type,
            passed=passed,
            details=details,
            activity_type="validation_result",
            **kwargs
        )
    
    def performance_metric(self, metric_name: str, value: Union[int, float], unit: str = "", **kwargs) -> None:
        """Log performance metric."""
        self.info(
            f"Performance metric: {metric_name}",
            metric_name=metric_name,
            value=value,
            unit=unit,
            activity_type="performance_metric",
            **kwargs
        )
    
    def security_event(self, event_type: str, severity: str, details: Dict[str, Any], **kwargs) -> None:
        """Log security event."""
        level_map = {
            "low": "info",
            "medium": "warning",
            "high": "error",
            "critical": "critical"
        }
        level = level_map.get(severity.lower(), "warning")
        
        getattr(self, level)(
            f"Security event: {event_type}",
            event_type=event_type,
            severity=severity,
            details=details,
            activity_type="security_event",
            **kwargs
        )


# Global logger registry
_loggers: Dict[str, GitIntellisenseLogger] = {}


def setup_logging(config: Optional[Config] = None) -> None:
    """Set up global logging configuration."""
    config = config or get_config()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create main logger
    main_logger = GitIntellisenseLogger("gitintellisense", config)
    
    # Add handlers to root logger
    if config.logging.file:
        root_logger.addHandler(main_logger._setup_file_handler())
    
    root_logger.addHandler(main_logger._setup_console_handler())
    
    # Store in registry
    _loggers["gitintellisense"] = main_logger


def get_logger(name: str = "gitintellisense") -> GitIntellisenseLogger:
    """Get a logger instance."""
    if name not in _loggers:
        config = get_config()
        _loggers[name] = GitIntellisenseLogger(name, config)
    
    return _loggers[name]


def log_system_info() -> None:
    """Log system information at startup."""
    logger = get_logger()
    config = get_config()
    
    logger.info(
        "GitHub Repository Scanner and Automated Contribution System starting",
        version="1.0.0",
        python_version=sys.version,
        development_mode=config.is_development,
        activity_type="system_startup"
    )
    
    # Log configuration summary (without sensitive data)
    config_summary = {
        "github_username": config.github.username,
        "target_repo": config.target.default_repo,
        "ai_model": config.openrouter.model,
        "dry_run_mode": config.contribution.dry_run_mode,
        "features_enabled": {
            "ai_analysis": config.features.ai_analysis,
            "static_analysis": config.features.static_analysis,
            "pattern_recognition": config.features.pattern_recognition,
            "contribution_generation": config.features.contribution_generation,
        }
    }
    
    logger.info(
        "System configuration loaded",
        config=config_summary,
        activity_type="config_loaded"
    )
