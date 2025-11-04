"""
Advanced metrics system for repository health analysis and trend prediction.

This module provides sophisticated analytics capabilities including:
- Repository health scoring with multiple dimensions
- Trend analysis and forecasting
- Predictive analytics for contribution success
- Community health metrics
- Performance benchmarking
"""

import json
import math
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

from ..core.github_client import GitHubClient
from ..utils.config import Config, get_config
from ..utils.logging import get_logger
from ..utils.database import DatabaseManager


class AdvancedMetricsEngine:
    """
    Advanced metrics engine for comprehensive repository analysis.
    
    Provides multi-dimensional health scoring, trend analysis,
    and predictive analytics for repository and contribution metrics.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize advanced metrics engine."""
        self.config = config or get_config()
        self.logger = get_logger("advanced_metrics")
        
        # Initialize components
        self.github_client = GitHubClient(config)
        self.db = DatabaseManager(config)
        
        # Metrics configuration
        self.health_weights = {
            "activity": 0.25,
            "community": 0.20,
            "code_quality": 0.20,
            "documentation": 0.15,
            "maintenance": 0.10,
            "accessibility": 0.10,
        }
    
    async def calculate_comprehensive_health_score(
        self, 
        repository: str,
        include_trends: bool = True
    ) -> Dict[str, Any]:
        """Calculate comprehensive repository health score."""
        self.logger.info(f"Calculating comprehensive health score for {repository}")
        
        try:
            # Get repository data
            repo_info = await self.github_client.get_repository_info(repository)
            
            # Calculate individual dimension scores
            activity_score = await self._calculate_activity_score(repository, repo_info)
            community_score = await self._calculate_community_score(repository, repo_info)
            code_quality_score = await self._calculate_code_quality_score(repository, repo_info)
            documentation_score = await self._calculate_documentation_score(repository, repo_info)
            maintenance_score = await self._calculate_maintenance_score(repository, repo_info)
            accessibility_score = await self._calculate_accessibility_score(repository, repo_info)
            
            # Calculate weighted overall score
            dimension_scores = {
                "activity": activity_score,
                "community": community_score,
                "code_quality": code_quality_score,
                "documentation": documentation_score,
                "maintenance": maintenance_score,
                "accessibility": accessibility_score,
            }
            
            overall_score = sum(
                score * self.health_weights[dimension]
                for dimension, score in dimension_scores.items()
            )
            
            # Calculate trends if requested
            trends = {}
            if include_trends:
                trends = await self._calculate_health_trends(repository)
            
            # Generate recommendations
            recommendations = self._generate_health_recommendations(dimension_scores)
            
            return {
                "repository": repository,
                "overall_score": round(overall_score, 1),
                "dimension_scores": dimension_scores,
                "trends": trends,
                "recommendations": recommendations,
                "calculated_at": datetime.now().isoformat(),
                "methodology_version": "2.0",
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate health score for {repository}: {e}")
            return {"error": str(e)}
    
    async def analyze_contribution_trends(
        self, 
        repository: str,
        time_period_days: int = 365
    ) -> Dict[str, Any]:
        """Analyze contribution trends and patterns."""
        self.logger.info(f"Analyzing contribution trends for {repository}")
        
        try:
            # Get historical contribution data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period_days)
            
            # Get commits, PRs, and issues data
            commits_data = await self._get_commits_timeline(repository, start_date, end_date)
            prs_data = await self._get_prs_timeline(repository, start_date, end_date)
            issues_data = await self._get_issues_timeline(repository, start_date, end_date)
            
            # Analyze trends
            commit_trends = self._analyze_timeline_trends(commits_data, "commits")
            pr_trends = self._analyze_timeline_trends(prs_data, "pull_requests")
            issue_trends = self._analyze_timeline_trends(issues_data, "issues")
            
            # Calculate contributor diversity
            contributor_diversity = await self._calculate_contributor_diversity(repository)
            
            # Predict future activity
            activity_forecast = self._forecast_activity(commits_data, prs_data, issues_data)
            
            return {
                "repository": repository,
                "analysis_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": time_period_days,
                },
                "trends": {
                    "commits": commit_trends,
                    "pull_requests": pr_trends,
                    "issues": issue_trends,
                },
                "contributor_diversity": contributor_diversity,
                "activity_forecast": activity_forecast,
                "analyzed_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze trends for {repository}: {e}")
            return {"error": str(e)}
    
    async def benchmark_repository(
        self, 
        repository: str,
        comparison_repositories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Benchmark repository against similar repositories."""
        self.logger.info(f"Benchmarking repository {repository}")
        
        try:
            # Get target repository metrics
            target_metrics = await self._get_repository_metrics(repository)
            
            # Get comparison repositories if not provided
            if not comparison_repositories:
                comparison_repositories = await self._find_similar_repositories(repository)
            
            # Get metrics for comparison repositories
            comparison_metrics = []
            for comp_repo in comparison_repositories:
                try:
                    metrics = await self._get_repository_metrics(comp_repo)
                    comparison_metrics.append({"repository": comp_repo, "metrics": metrics})
                except Exception as e:
                    self.logger.warning(f"Failed to get metrics for {comp_repo}: {e}")
            
            # Calculate percentiles and rankings
            benchmarks = self._calculate_benchmarks(target_metrics, comparison_metrics)
            
            # Generate insights
            insights = self._generate_benchmark_insights(benchmarks)
            
            return {
                "target_repository": repository,
                "comparison_repositories": [c["repository"] for c in comparison_metrics],
                "target_metrics": target_metrics,
                "benchmarks": benchmarks,
                "insights": insights,
                "benchmarked_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to benchmark repository {repository}: {e}")
            return {"error": str(e)}
    
    async def predict_contribution_success_rate(
        self, 
        repository: str,
        contributor_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Predict contribution success rate for a repository."""
        self.logger.info(f"Predicting contribution success rate for {repository}")
        
        try:
            # Get historical contribution data
            historical_data = await self._get_historical_contribution_data(repository)
            
            # Calculate base success rate
            base_success_rate = self._calculate_base_success_rate(historical_data)
            
            # Analyze success factors
            success_factors = self._analyze_success_factors(historical_data)
            
            # Predict success rate for contributor profile
            predicted_rate = base_success_rate
            confidence = "medium"
            
            if contributor_profile:
                predicted_rate, confidence = self._predict_individual_success_rate(
                    historical_data, 
                    contributor_profile,
                    base_success_rate
                )
            
            # Generate recommendations
            recommendations = self._generate_success_recommendations(success_factors)
            
            return {
                "repository": repository,
                "base_success_rate": base_success_rate,
                "predicted_success_rate": predicted_rate,
                "confidence": confidence,
                "success_factors": success_factors,
                "recommendations": recommendations,
                "contributor_profile": contributor_profile,
                "predicted_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to predict success rate for {repository}: {e}")
            return {"error": str(e)}
    
    async def generate_repository_report(
        self, 
        repository: str,
        include_all_metrics: bool = True
    ) -> Dict[str, Any]:
        """Generate comprehensive repository analysis report."""
        self.logger.info(f"Generating comprehensive report for {repository}")
        
        try:
            report = {
                "repository": repository,
                "generated_at": datetime.now().isoformat(),
                "report_version": "2.0",
            }
            
            # Health score analysis
            health_analysis = await self.calculate_comprehensive_health_score(repository)
            report["health_analysis"] = health_analysis
            
            if include_all_metrics:
                # Contribution trends
                trends_analysis = await self.analyze_contribution_trends(repository)
                report["trends_analysis"] = trends_analysis
                
                # Benchmarking
                benchmark_analysis = await self.benchmark_repository(repository)
                report["benchmark_analysis"] = benchmark_analysis
                
                # Success prediction
                success_prediction = await self.predict_contribution_success_rate(repository)
                report["success_prediction"] = success_prediction
            
            # Executive summary
            report["executive_summary"] = self._generate_executive_summary(report)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate report for {repository}: {e}")
            return {"error": str(e)}
    
    async def _calculate_activity_score(self, repository: str, repo_info: Dict[str, Any]) -> float:
        """Calculate activity dimension score."""
        try:
            # Get recent activity data
            recent_commits = await self._get_recent_activity_count(repository, "commits", 30)
            recent_prs = await self._get_recent_activity_count(repository, "pulls", 30)
            recent_issues = await self._get_recent_activity_count(repository, "issues", 30)
            
            # Calculate activity score based on recent activity
            activity_score = min(100, (recent_commits * 2 + recent_prs * 3 + recent_issues * 1) / 2)
            
            # Adjust based on repository age
            created_at = datetime.fromisoformat(repo_info.get("created_at", "").replace("Z", "+00:00"))
            age_days = (datetime.now() - created_at).days
            
            if age_days < 30:
                activity_score *= 0.8  # Newer repos get slight penalty
            elif age_days > 365:
                activity_score *= 1.1  # Mature repos get slight bonus
            
            return min(100, max(0, activity_score))
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate activity score: {e}")
            return 50.0  # Default score
    
    async def _calculate_community_score(self, repository: str, repo_info: Dict[str, Any]) -> float:
        """Calculate community dimension score."""
        try:
            # Base metrics
            stars = repo_info.get("stargazers_count", 0)
            forks = repo_info.get("forks_count", 0)
            watchers = repo_info.get("watchers_count", 0)
            
            # Calculate community engagement score
            engagement_score = min(100, math.log10(max(1, stars)) * 20 + math.log10(max(1, forks)) * 15)
            
            # Check for community health indicators
            has_contributing = await self._check_file_exists(repository, "CONTRIBUTING.md")
            has_code_of_conduct = await self._check_file_exists(repository, "CODE_OF_CONDUCT.md")
            has_issue_templates = await self._check_directory_exists(repository, ".github/ISSUE_TEMPLATE")
            
            community_health_bonus = 0
            if has_contributing:
                community_health_bonus += 10
            if has_code_of_conduct:
                community_health_bonus += 10
            if has_issue_templates:
                community_health_bonus += 5
            
            total_score = min(100, engagement_score + community_health_bonus)
            return max(0, total_score)
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate community score: {e}")
            return 50.0
    
    async def _calculate_code_quality_score(self, repository: str, repo_info: Dict[str, Any]) -> float:
        """Calculate code quality dimension score."""
        try:
            # Check for quality indicators
            has_tests = await self._check_tests_exist(repository)
            has_ci = await self._check_ci_exists(repository)
            has_linting = await self._check_linting_config(repository)
            
            quality_score = 40  # Base score
            
            if has_tests:
                quality_score += 30
            if has_ci:
                quality_score += 20
            if has_linting:
                quality_score += 10
            
            return min(100, max(0, quality_score))
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate code quality score: {e}")
            return 50.0

    async def _calculate_documentation_score(self, repository: str, repo_info: Dict[str, Any]) -> float:
        """Calculate documentation dimension score."""
        try:
            # Check for documentation files
            has_readme = await self._check_file_exists(repository, "README.md")
            has_docs_dir = await self._check_directory_exists(repository, "docs")
            has_wiki = repo_info.get("has_wiki", False)

            doc_score = 20  # Base score

            if has_readme:
                doc_score += 40
            if has_docs_dir:
                doc_score += 30
            if has_wiki:
                doc_score += 10

            return min(100, max(0, doc_score))

        except Exception as e:
            self.logger.warning(f"Failed to calculate documentation score: {e}")
            return 50.0

    async def _calculate_maintenance_score(self, repository: str, repo_info: Dict[str, Any]) -> float:
        """Calculate maintenance dimension score."""
        try:
            # Check last update
            updated_at = datetime.fromisoformat(repo_info.get("updated_at", "").replace("Z", "+00:00"))
            days_since_update = (datetime.now() - updated_at).days

            # Calculate freshness score
            if days_since_update <= 7:
                freshness_score = 100
            elif days_since_update <= 30:
                freshness_score = 80
            elif days_since_update <= 90:
                freshness_score = 60
            elif days_since_update <= 180:
                freshness_score = 40
            else:
                freshness_score = 20

            # Check for maintenance indicators
            has_releases = await self._check_has_releases(repository)
            has_security_policy = await self._check_file_exists(repository, "SECURITY.md")

            maintenance_bonus = 0
            if has_releases:
                maintenance_bonus += 10
            if has_security_policy:
                maintenance_bonus += 5

            total_score = min(100, freshness_score + maintenance_bonus)
            return max(0, total_score)

        except Exception as e:
            self.logger.warning(f"Failed to calculate maintenance score: {e}")
            return 50.0

    async def _calculate_accessibility_score(self, repository: str, repo_info: Dict[str, Any]) -> float:
        """Calculate accessibility dimension score."""
        try:
            # Check accessibility indicators
            has_license = repo_info.get("license") is not None
            has_good_description = len(repo_info.get("description", "")) > 20
            has_topics = len(repo_info.get("topics", [])) > 0
            open_issues = repo_info.get("open_issues_count", 0)

            accessibility_score = 30  # Base score

            if has_license:
                accessibility_score += 25
            if has_good_description:
                accessibility_score += 20
            if has_topics:
                accessibility_score += 15
            if open_issues < 50:  # Manageable number of issues
                accessibility_score += 10

            return min(100, max(0, accessibility_score))

        except Exception as e:
            self.logger.warning(f"Failed to calculate accessibility score: {e}")
            return 50.0

    async def _get_recent_activity_count(self, repository: str, activity_type: str, days: int) -> int:
        """Get count of recent activity."""
        try:
            since_date = datetime.now() - timedelta(days=days)

            if activity_type == "commits":
                commits = await self.github_client.get_commits(repository, since=since_date.isoformat())
                return len(commits)
            elif activity_type == "pulls":
                prs = await self.github_client.get_pull_requests(repository, state="all")
                recent_prs = [pr for pr in prs if datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00")) > since_date]
                return len(recent_prs)
            elif activity_type == "issues":
                issues = await self.github_client.get_issues(repository, state="all")
                recent_issues = [issue for issue in issues if datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00")) > since_date]
                return len(recent_issues)

            return 0

        except Exception as e:
            self.logger.warning(f"Failed to get {activity_type} count: {e}")
            return 0

    async def _check_file_exists(self, repository: str, filename: str) -> bool:
        """Check if a file exists in the repository."""
        try:
            content = await self.github_client.get_file_content(repository, filename)
            return content is not None
        except:
            return False

    async def _check_directory_exists(self, repository: str, dirname: str) -> bool:
        """Check if a directory exists in the repository."""
        try:
            contents = await self.github_client.get_repository_contents(repository, dirname)
            return len(contents) > 0
        except:
            return False

    async def _check_tests_exist(self, repository: str) -> bool:
        """Check if tests exist in the repository."""
        test_indicators = ["test", "tests", "spec", "__tests__", "test_"]

        try:
            contents = await self.github_client.get_repository_contents(repository, "")

            for item in contents:
                if any(indicator in item["name"].lower() for indicator in test_indicators):
                    return True

            return False
        except:
            return False

    async def _check_ci_exists(self, repository: str) -> bool:
        """Check if CI configuration exists."""
        ci_files = [
            ".github/workflows",
            ".travis.yml",
            "circle.yml",
            ".circleci/config.yml",
            "Jenkinsfile",
            ".gitlab-ci.yml"
        ]

        for ci_file in ci_files:
            if await self._check_file_exists(repository, ci_file) or await self._check_directory_exists(repository, ci_file):
                return True

        return False

    async def _check_linting_config(self, repository: str) -> bool:
        """Check if linting configuration exists."""
        linting_files = [
            ".eslintrc",
            ".pylintrc",
            "tslint.json",
            ".flake8",
            "pyproject.toml",
            ".pre-commit-config.yaml"
        ]

        for lint_file in linting_files:
            if await self._check_file_exists(repository, lint_file):
                return True

        return False

    async def _check_has_releases(self, repository: str) -> bool:
        """Check if repository has releases."""
        try:
            releases = await self.github_client.get_releases(repository)
            return len(releases) > 0
        except:
            return False
