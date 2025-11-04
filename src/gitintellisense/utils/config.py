"""
Configuration management for the GitHub Repository Scanner and Automated Contribution System.

This module provides secure configuration management with environment variable support,
validation, and integration with existing infrastructure patterns.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
load_dotenv()


class GitHubConfig(BaseSettings):
    """GitHub API configuration."""
    
    token: str = Field(..., description="GitHub Personal Access Token")
    username: str = Field(..., description="GitHub username")
    rate_limit_per_hour: int = Field(4500, description="GitHub API rate limit per hour")
    request_timeout: int = Field(30, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")
    retry_backoff_factor: float = Field(2.0, description="Exponential backoff factor")
    
    model_config = SettingsConfigDict(env_prefix="GITHUB_")


class OpenRouterConfig(BaseSettings):
    """OpenRouter AI configuration."""
    
    api_key: str = Field(..., description="OpenRouter API key")
    base_url: str = Field("https://openrouter.ai/api/v1", description="OpenRouter base URL")
    model: str = Field("google/gemini-2.0-flash-exp:free", description="AI model to use")
    temperature: float = Field(0.3, description="AI temperature setting")
    max_tokens: int = Field(4000, description="Maximum tokens per request")
    top_p: float = Field(0.9, description="Top-p sampling parameter")
    frequency_penalty: float = Field(0.1, description="Frequency penalty")
    presence_penalty: float = Field(0.1, description="Presence penalty")
    rate_limit_per_minute: int = Field(60, description="Rate limit per minute")
    
    model_config = SettingsConfigDict(env_prefix="OPENROUTER_")


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    
    url: str = Field("sqlite:///gitintellisense.db", description="Database URL")
    pool_size: int = Field(10, description="Connection pool size")
    max_overflow: int = Field(20, description="Maximum overflow connections")
    echo: bool = Field(False, description="Enable SQL query logging")
    
    model_config = SettingsConfigDict(env_prefix="DATABASE_")


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    level: str = Field("INFO", description="Logging level")
    format: str = Field("json", description="Log format (json or text)")
    file: str = Field("logs/gitintellisense.log", description="Log file path")
    max_size: str = Field("10MB", description="Maximum log file size")
    backup_count: int = Field(5, description="Number of backup log files")
    
    model_config = SettingsConfigDict(env_prefix="LOG_")


class AnalysisConfig(BaseSettings):
    """Repository analysis configuration."""
    
    max_repositories_per_scan: int = Field(10, description="Maximum repositories per scan")
    max_commits_to_analyze: int = Field(1000, description="Maximum commits to analyze")
    max_issues_to_analyze: int = Field(500, description="Maximum issues to analyze")
    cache_ttl: int = Field(3600, description="Cache TTL in seconds")
    
    model_config = SettingsConfigDict(env_prefix="ANALYSIS_")


class ContributionConfig(BaseSettings):
    """Contribution generation configuration."""
    
    min_score: float = Field(0.7, description="Minimum contribution score")
    max_per_day: int = Field(3, description="Maximum contributions per day")
    validation_enabled: bool = Field(True, description="Enable contribution validation")
    dry_run_mode: bool = Field(True, description="Enable dry run mode")
    
    model_config = SettingsConfigDict(env_prefix="CONTRIBUTION_")


class SecurityConfig(BaseSettings):
    """Security configuration."""
    
    encrypt_sensitive_data: bool = Field(True, description="Encrypt sensitive data")
    encryption_key: Optional[str] = Field(None, description="Encryption key")
    session_timeout: int = Field(3600, description="Session timeout in seconds")
    api_key_rotation_days: int = Field(90, description="API key rotation period")
    
    model_config = SettingsConfigDict(env_prefix="SECURITY_")


class PerformanceConfig(BaseSettings):
    """Performance configuration."""
    
    async_worker_count: int = Field(10, description="Number of async workers")
    cache_size: int = Field(1000, description="Cache size")
    memory_limit_mb: int = Field(2048, description="Memory limit in MB")
    cpu_limit_percent: int = Field(80, description="CPU limit percentage")
    
    model_config = SettingsConfigDict(env_prefix="PERFORMANCE_")


class MonitoringConfig(BaseSettings):
    """Monitoring configuration."""
    
    enabled: bool = Field(True, description="Enable monitoring")
    port: int = Field(8080, description="Metrics port")
    health_check_interval: int = Field(60, description="Health check interval")
    alert_webhook_url: Optional[str] = Field(None, description="Alert webhook URL")
    
    model_config = SettingsConfigDict(env_prefix="MONITORING_")


class DevelopmentConfig(BaseSettings):
    """Development configuration."""
    
    debug: bool = Field(False, description="Enable debug mode")
    development_mode: bool = Field(False, description="Enable development mode")
    profiling_enabled: bool = Field(False, description="Enable profiling")
    verbose_logging: bool = Field(False, description="Enable verbose logging")
    
    model_config = SettingsConfigDict(env_prefix="DEVELOPMENT_")


class TargetRepositoryConfig(BaseSettings):
    """Target repository configuration."""
    
    default_repo: str = Field("bitcoin/bitcoin", description="Default target repository")
    branches: List[str] = Field(["master", "main", "develop"], description="Target branches")
    exclude_paths: List[str] = Field([".git", ".github", "node_modules", "__pycache__"], description="Paths to exclude")
    include_extensions: List[str] = Field([".py", ".cpp", ".h", ".js", ".ts", ".md"], description="File extensions to include")
    
    model_config = SettingsConfigDict(env_prefix="TARGET_")
    
    @field_validator("branches", mode="before")
    @classmethod
    def parse_branches(cls, v):
        if isinstance(v, str):
            return [branch.strip() for branch in v.split(",")]
        return v

    @field_validator("exclude_paths", mode="before")
    @classmethod
    def parse_exclude_paths(cls, v):
        if isinstance(v, str):
            return [path.strip() for path in v.split(",")]
        return v

    @field_validator("include_extensions", mode="before")
    @classmethod
    def parse_include_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v


class FeatureFlagsConfig(BaseSettings):
    """Feature flags configuration."""
    
    ai_analysis: bool = Field(True, description="Enable AI analysis")
    static_analysis: bool = Field(True, description="Enable static analysis")
    pattern_recognition: bool = Field(True, description="Enable pattern recognition")
    contribution_generation: bool = Field(True, description="Enable contribution generation")
    automated_testing: bool = Field(True, description="Enable automated testing")
    performance_monitoring: bool = Field(True, description="Enable performance monitoring")
    
    model_config = SettingsConfigDict(env_prefix="ENABLE_")


class Config(BaseSettings):
    """Main configuration class that aggregates all configuration sections."""
    
    # Configuration sections
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    openrouter: OpenRouterConfig = Field(default_factory=OpenRouterConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    contribution: ContributionConfig = Field(default_factory=ContributionConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    development: DevelopmentConfig = Field(default_factory=DevelopmentConfig)
    target: TargetRepositoryConfig = Field(default_factory=TargetRepositoryConfig)
    features: FeatureFlagsConfig = Field(default_factory=FeatureFlagsConfig)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def __init__(self, **kwargs):
        """Initialize configuration with proper environment loading."""
        super().__init__(**kwargs)
        
        # Initialize sub-configurations
        self.github = GitHubConfig()
        self.openrouter = OpenRouterConfig()
        self.database = DatabaseConfig()
        self.logging = LoggingConfig()
        self.analysis = AnalysisConfig()
        self.contribution = ContributionConfig()
        self.security = SecurityConfig()
        self.performance = PerformanceConfig()
        self.monitoring = MonitoringConfig()
        self.development = DevelopmentConfig()
        self.target = TargetRepositoryConfig()
        self.features = FeatureFlagsConfig()
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.development.development_mode or self.development.debug
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.is_development
    
    def get_log_level(self) -> str:
        """Get the appropriate log level."""
        if self.development.verbose_logging:
            return "DEBUG"
        return self.logging.level
    
    def validate_required_credentials(self) -> bool:
        """Validate that all required credentials are present."""
        required_fields = [
            (self.github.token, "GitHub token"),
            (self.github.username, "GitHub username"),
            (self.openrouter.api_key, "OpenRouter API key"),
        ]
        
        missing_fields = []
        for value, name in required_fields:
            if not value or value == "your_token_here" or value == "your_key_here":
                missing_fields.append(name)
        
        if missing_fields:
            raise ValueError(f"Missing required credentials: {', '.join(missing_fields)}")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "github": self.github.model_dump(),
            "openrouter": self.openrouter.model_dump(),
            "database": self.database.model_dump(),
            "logging": self.logging.model_dump(),
            "analysis": self.analysis.model_dump(),
            "contribution": self.contribution.model_dump(),
            "security": self.security.model_dump(),
            "performance": self.performance.model_dump(),
            "monitoring": self.monitoring.model_dump(),
            "development": self.development.model_dump(),
            "target": self.target.model_dump(),
            "features": self.features.model_dump(),
        }


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
        _config.validate_required_credentials()
    return _config


def reload_config() -> Config:
    """Reload the configuration from environment variables."""
    global _config
    _config = None
    return get_config()


def set_config(config: Config) -> None:
    """Set the global configuration instance (for testing)."""
    global _config
    _config = config
