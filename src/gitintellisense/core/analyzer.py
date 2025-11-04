"""
Core repository analyzer that orchestrates comprehensive repository analysis.

This module provides the main analyzer class that coordinates all analysis components
to provide comprehensive repository intelligence and contribution opportunity identification.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..analysis.repository import RepositoryIntelligence
from ..analysis.patterns import PatternAnalyzer
from ..analysis.opportunities import OpportunityDetector
from ..core.github_client import GitHubClient
from ..utils.config import Config, get_config
from ..utils.logging import get_logger


class RepositoryAnalyzer:
    """
    Main repository analyzer that orchestrates comprehensive analysis.
    
    This class coordinates all analysis components to provide deep insights
    into repository structure, patterns, and contribution opportunities.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize repository analyzer."""
        self.config = config or get_config()
        self.logger = get_logger("repository_analyzer")
        
        # Initialize analysis components
        self.github_client = GitHubClient(config)
        self.repo_intelligence = RepositoryIntelligence(config)
        self.pattern_analyzer = PatternAnalyzer(config)
        self.opportunity_detector = OpportunityDetector(config)
        
        # Analysis cache
        self._analysis_cache: Dict[str, Dict[str, Any]] = {}
    
    async def analyze_repository_comprehensive(
        self, 
        repo_name: str, 
        include_patterns: bool = True,
        include_opportunities: bool = True,
        cache_results: bool = True
    ) -> Dict[str, Any]:
        """
        Perform comprehensive repository analysis.
        
        Args:
            repo_name: Repository name in format "owner/repo"
            include_patterns: Whether to include pattern analysis
            include_opportunities: Whether to include opportunity detection
            cache_results: Whether to cache analysis results
        
        Returns:
            Comprehensive analysis results
        """
        self.logger.info(
            f"Starting comprehensive analysis of {repo_name}",
            include_patterns=include_patterns,
            include_opportunities=include_opportunities
        )
        
        start_time = datetime.now()
        
        try:
            # Check cache first
            cache_key = f"{repo_name}_comprehensive_{include_patterns}_{include_opportunities}"
            if cache_results and cache_key in self._analysis_cache:
                cached_time = self._analysis_cache[cache_key].get("analysis_time")
                if cached_time and (datetime.now() - datetime.fromisoformat(cached_time)).seconds < self.config.analysis.cache_ttl:
                    self.logger.info(f"Using cached comprehensive analysis for {repo_name}")
                    return self._analysis_cache[cache_key]
            
            # Perform comprehensive analysis
            analysis_results = {
                "repository": repo_name,
                "analysis_time": datetime.now().isoformat(),
                "analysis_type": "comprehensive",
                "components_included": {
                    "basic_intelligence": True,
                    "patterns": include_patterns,
                    "opportunities": include_opportunities,
                },
            }
            
            # Basic repository intelligence (always included)
            self.logger.info(f"Performing repository intelligence analysis for {repo_name}")
            analysis_results["repository_intelligence"] = await self.repo_intelligence.analyze_repository(
                repo_name, 
                deep_analysis=True
            )
            
            # Pattern analysis (optional)
            if include_patterns:
                self.logger.info(f"Performing pattern analysis for {repo_name}")
                analysis_results["patterns"] = await self._perform_pattern_analysis(repo_name)
            
            # Opportunity detection (optional)
            if include_opportunities:
                self.logger.info(f"Performing opportunity detection for {repo_name}")
                analysis_results["opportunities"] = await self._perform_opportunity_detection(
                    repo_name, 
                    analysis_results.get("repository_intelligence", {}),
                    analysis_results.get("patterns", {})
                )
            
            # Generate comprehensive summary
            analysis_results["comprehensive_summary"] = self._generate_comprehensive_summary(analysis_results)
            
            # Cache results if requested
            if cache_results:
                self._analysis_cache[cache_key] = analysis_results
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"Comprehensive analysis completed for {repo_name}",
                duration_seconds=duration,
                components_analyzed=len([k for k, v in analysis_results["components_included"].items() if v])
            )
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Comprehensive analysis failed for {repo_name}", error=str(e))
            raise
    
    async def analyze_repository_quick(self, repo_name: str) -> Dict[str, Any]:
        """
        Perform quick repository analysis for initial assessment.
        
        Args:
            repo_name: Repository name in format "owner/repo"
        
        Returns:
            Quick analysis results
        """
        self.logger.info(f"Starting quick analysis of {repo_name}")
        
        start_time = datetime.now()
        
        try:
            # Quick analysis focuses on basic info and good first issues
            analysis_results = {
                "repository": repo_name,
                "analysis_time": datetime.now().isoformat(),
                "analysis_type": "quick",
            }
            
            # Basic repository information
            analysis_results["basic_info"] = await self.repo_intelligence._analyze_basic_info(repo_name)
            
            # Quick issue analysis for good first issues
            analysis_results["good_first_issues"] = await self.repo_intelligence._find_good_first_issues(repo_name)
            
            # Quick contribution assessment
            analysis_results["contribution_assessment"] = await self._quick_contribution_assessment(repo_name)
            
            # Generate quick summary
            analysis_results["quick_summary"] = self._generate_quick_summary(analysis_results)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Quick analysis completed for {repo_name}", duration_seconds=duration)
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Quick analysis failed for {repo_name}", error=str(e))
            raise
    
    async def _perform_pattern_analysis(self, repo_name: str) -> Dict[str, Any]:
        """Perform comprehensive pattern analysis."""
        patterns = {}
        
        # Commit patterns
        patterns["commit_patterns"] = await self.pattern_analyzer.analyze_commit_patterns(repo_name)
        
        # Maintainer patterns
        patterns["maintainer_patterns"] = await self.pattern_analyzer.analyze_maintainer_patterns(repo_name)
        
        return patterns
    
    async def _perform_opportunity_detection(
        self, 
        repo_name: str, 
        repo_intelligence: Dict[str, Any],
        patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform opportunity detection analysis."""
        # This will be implemented when we create the OpportunityDetector
        opportunities = {
            "placeholder": "Opportunity detection will be implemented in the next phase",
            "good_first_issues": repo_intelligence.get("issues_prs", {}).get("good_first_issues", []),
        }
        
        return opportunities
    
    async def _quick_contribution_assessment(self, repo_name: str) -> Dict[str, Any]:
        """Perform quick contribution assessment."""
        try:
            # Get basic repository info
            repo_info = await self.github_client.get_repository_info(repo_name)
            
            # Get contribution guidelines
            guidelines = await self.github_client.get_contribution_guidelines(repo_name)
            
            # Assess contribution difficulty
            difficulty_score = self._assess_contribution_difficulty_quick(repo_info, guidelines)
            
            return {
                "difficulty_score": difficulty_score,
                "has_guidelines": len(guidelines) > 0,
                "is_active": repo_info.get("updated_at", "").replace("Z", "+00:00") if repo_info.get("updated_at") else None,
                "community_size": {
                    "stars": repo_info.get("stars", 0),
                    "forks": repo_info.get("forks", 0),
                    "open_issues": repo_info.get("open_issues", 0),
                },
                "languages": repo_info.get("languages", {}),
            }
            
        except Exception as e:
            self.logger.warning(f"Quick contribution assessment failed: {e}")
            return {"error": str(e)}
    
    def _assess_contribution_difficulty_quick(
        self, 
        repo_info: Dict[str, Any], 
        guidelines: Dict[str, Any]
    ) -> str:
        """Quickly assess contribution difficulty."""
        score = 0
        
        # Repository maturity and activity
        if repo_info.get("updated_at"):
            try:
                last_update = datetime.fromisoformat(repo_info["updated_at"].replace("Z", "+00:00"))
                days_since_update = (datetime.now() - last_update).days
                
                if days_since_update < 30:
                    score += 2  # Active repository
                elif days_since_update < 90:
                    score += 1  # Moderately active
            except ValueError:
                pass
        
        # Community size indicators
        stars = repo_info.get("stars", 0)
        if stars > 1000:
            score += 1  # Popular repository
        if stars > 10000:
            score += 1  # Very popular repository
        
        # Documentation
        if guidelines:
            score += 2  # Has contribution guidelines
        
        if repo_info.get("has_wiki"):
            score += 1  # Has wiki
        
        # Issue management
        open_issues = repo_info.get("open_issues", 0)
        if 10 <= open_issues <= 100:
            score += 1  # Manageable number of issues
        elif open_issues > 500:
            score -= 1  # Too many issues might indicate maintenance problems
        
        # Determine difficulty level
        if score >= 6:
            return "beginner_friendly"
        elif score >= 4:
            return "moderate"
        elif score >= 2:
            return "intermediate"
        else:
            return "advanced"
    
    def _generate_comprehensive_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive analysis summary."""
        repo_intelligence = analysis_results.get("repository_intelligence", {})
        patterns = analysis_results.get("patterns", {})
        opportunities = analysis_results.get("opportunities", {})
        
        # Extract key metrics
        basic_info = repo_intelligence.get("basic_info", {})
        activity = repo_intelligence.get("activity", {})
        issues_prs = repo_intelligence.get("issues_prs", {})
        
        summary = {
            "overall_assessment": {
                "health_score": basic_info.get("health_score", 0),
                "activity_level": basic_info.get("activity_level", "unknown"),
                "maturity": basic_info.get("maturity", "unknown"),
                "contribution_difficulty": "moderate",  # Would be calculated from various factors
            },
            "key_metrics": {
                "stars": basic_info.get("stars", 0),
                "forks": basic_info.get("forks", 0),
                "open_issues": issues_prs.get("open_issues", {}).get("total", 0),
                "recent_commits": activity.get("total_commits", 0),
                "good_first_issues": len(opportunities.get("good_first_issues", [])),
            },
            "contribution_readiness": {
                "has_guidelines": len(repo_intelligence.get("guidelines", {}).get("guidelines", {})) > 0,
                "has_good_first_issues": len(opportunities.get("good_first_issues", [])) > 0,
                "maintainer_responsive": "unknown",  # Would be calculated from patterns
                "community_active": basic_info.get("activity_level") in ["active", "very_active"],
            },
            "recommendations": self._generate_recommendations(analysis_results),
        }
        
        return summary
    
    def _generate_quick_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate quick analysis summary."""
        basic_info = analysis_results.get("basic_info", {})
        good_first_issues = analysis_results.get("good_first_issues", [])
        contribution_assessment = analysis_results.get("contribution_assessment", {})
        
        summary = {
            "repository_health": basic_info.get("health_score", 0),
            "activity_level": basic_info.get("activity_level", "unknown"),
            "contribution_difficulty": contribution_assessment.get("difficulty_score", "unknown"),
            "good_first_issues_count": len(good_first_issues),
            "has_contribution_guidelines": contribution_assessment.get("has_guidelines", False),
            "community_size": contribution_assessment.get("community_size", {}),
            "recommendation": self._generate_quick_recommendation(analysis_results),
        }
        
        return summary
    
    def _generate_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on comprehensive analysis."""
        recommendations = []
        
        repo_intelligence = analysis_results.get("repository_intelligence", {})
        opportunities = analysis_results.get("opportunities", {})
        
        # Check for good first issues
        good_first_issues = opportunities.get("good_first_issues", [])
        if good_first_issues:
            recommendations.append(f"Found {len(good_first_issues)} good first issues - excellent for new contributors")
        
        # Check repository health
        basic_info = repo_intelligence.get("basic_info", {})
        health_score = basic_info.get("health_score", 0)
        
        if health_score > 80:
            recommendations.append("Repository is very healthy and well-maintained")
        elif health_score > 60:
            recommendations.append("Repository is in good condition for contributions")
        elif health_score > 40:
            recommendations.append("Repository shows some maintenance issues - proceed with caution")
        else:
            recommendations.append("Repository may have maintenance issues - consider other options")
        
        # Check activity level
        activity_level = basic_info.get("activity_level", "unknown")
        if activity_level in ["very_active", "active"]:
            recommendations.append("Repository is actively maintained - good for timely feedback")
        elif activity_level == "moderate":
            recommendations.append("Repository has moderate activity - expect slower response times")
        else:
            recommendations.append("Repository has low activity - contributions may not be reviewed quickly")
        
        return recommendations
    
    def _generate_quick_recommendation(self, analysis_results: Dict[str, Any]) -> str:
        """Generate quick recommendation."""
        contribution_assessment = analysis_results.get("contribution_assessment", {})
        difficulty = contribution_assessment.get("difficulty_score", "unknown")
        good_first_issues = analysis_results.get("good_first_issues", [])
        
        if difficulty == "beginner_friendly" and len(good_first_issues) > 0:
            return "Highly recommended for new contributors"
        elif difficulty in ["beginner_friendly", "moderate"] and len(good_first_issues) > 0:
            return "Good option for contributors"
        elif difficulty == "moderate":
            return "Suitable for contributors with some experience"
        elif difficulty in ["intermediate", "advanced"]:
            return "Recommended for experienced contributors only"
        else:
            return "Requires further analysis before contributing"
    
    async def close(self) -> None:
        """Close all analysis components."""
        await self.github_client.close()
        self.logger.info("Repository analyzer closed")
