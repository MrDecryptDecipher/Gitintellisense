"""
Opportunity detection module for identifying contribution opportunities.

This module provides sophisticated opportunity detection capabilities using
AI-powered analysis, pattern recognition, and static code analysis to identify
meaningful contribution opportunities in repositories.
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict, Counter

from ..core.github_client import GitHubClient
from ..core.ai_engine import AIEngine
from ..utils.config import Config, get_config
from ..utils.logging import get_logger


class OpportunityDetector:
    """
    Advanced opportunity detection engine that identifies meaningful
    contribution opportunities using AI and pattern analysis.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize opportunity detector."""
        self.config = config or get_config()
        self.logger = get_logger("opportunity_detector")
        self.github_client = GitHubClient(config)
        self.ai_engine = AIEngine(config)
        
        # Opportunity scoring weights
        self.scoring_weights = {
            "technical_impact": 0.3,
            "learning_value": 0.2,
            "acceptance_likelihood": 0.25,
            "maintainer_alignment": 0.15,
            "community_benefit": 0.1,
        }
    
    async def detect_opportunities(
        self, 
        repo_name: str,
        repo_analysis: Dict[str, Any],
        contributor_skills: Optional[List[str]] = None,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect contribution opportunities in a repository.
        
        Args:
            repo_name: Repository name in format "owner/repo"
            repo_analysis: Comprehensive repository analysis data
            contributor_skills: List of contributor skills/technologies
            focus_areas: Specific areas to focus on
        
        Returns:
            Comprehensive opportunity analysis
        """
        self.logger.opportunity_detected(
            repo_name, 
            "detection_started", 
            0.0,
            contributor_skills=contributor_skills,
            focus_areas=focus_areas
        )
        
        opportunities = {
            "repository": repo_name,
            "detection_time": datetime.now().isoformat(),
            "contributor_skills": contributor_skills or [],
            "focus_areas": focus_areas or [],
            "opportunities": [],
        }
        
        try:
            # Detect different types of opportunities
            issue_opportunities = await self._detect_issue_opportunities(repo_name, repo_analysis)
            code_opportunities = await self._detect_code_opportunities(repo_name, repo_analysis)
            documentation_opportunities = await self._detect_documentation_opportunities(repo_name, repo_analysis)
            testing_opportunities = await self._detect_testing_opportunities(repo_name, repo_analysis)
            
            # Combine all opportunities
            all_opportunities = (
                issue_opportunities + 
                code_opportunities + 
                documentation_opportunities + 
                testing_opportunities
            )
            
            # Score and rank opportunities
            scored_opportunities = await self._score_opportunities(
                all_opportunities, 
                repo_analysis,
                contributor_skills,
                focus_areas
            )
            
            # Filter and prioritize
            filtered_opportunities = self._filter_opportunities(
                scored_opportunities,
                contributor_skills,
                focus_areas
            )
            
            # Use AI for advanced analysis
            if self.config.features.ai_analysis and filtered_opportunities:
                ai_analysis = await self._ai_enhance_opportunities(
                    filtered_opportunities,
                    repo_analysis,
                    contributor_skills
                )
                opportunities["ai_analysis"] = ai_analysis
            
            opportunities["opportunities"] = filtered_opportunities[:20]  # Top 20
            opportunities["summary"] = self._generate_opportunity_summary(filtered_opportunities)
            
            self.logger.info(
                f"Detected {len(filtered_opportunities)} opportunities for {repo_name}",
                total_opportunities=len(all_opportunities),
                filtered_opportunities=len(filtered_opportunities)
            )
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Opportunity detection failed for {repo_name}", error=str(e))
            return {"error": str(e)}
    
    async def _detect_issue_opportunities(
        self, 
        repo_name: str, 
        repo_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect opportunities from issues."""
        opportunities = []
        
        # Get good first issues
        issues_data = repo_analysis.get("repository_intelligence", {}).get("issues_prs", {})
        good_first_issues = issues_data.get("good_first_issues", [])
        
        for issue in good_first_issues:
            opportunity = {
                "type": "issue",
                "subtype": "good_first_issue",
                "title": f"Resolve issue: {issue.get('title', 'Unknown')}",
                "description": issue.get("body", "")[:500],  # Truncate description
                "issue_number": issue.get("number"),
                "labels": issue.get("labels", []),
                "url": issue.get("url", ""),
                "complexity": self._assess_issue_complexity(issue),
                "estimated_effort": self._estimate_issue_effort(issue),
                "skills_required": self._extract_skills_from_issue(issue),
                "base_score": issue.get("suitability_score", 0),
            }
            opportunities.append(opportunity)
        
        # Look for other issue patterns
        open_issues = issues_data.get("open_issues", {}).get("analysis", {})
        if open_issues:
            # Find documentation issues
            doc_opportunities = await self._find_documentation_issues(repo_name)
            opportunities.extend(doc_opportunities)
            
            # Find testing issues
            test_opportunities = await self._find_testing_issues(repo_name)
            opportunities.extend(test_opportunities)
        
        return opportunities
    
    async def _detect_code_opportunities(
        self, 
        repo_name: str, 
        repo_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect code improvement opportunities."""
        opportunities = []
        
        # Analyze code structure for improvement opportunities
        code_structure = repo_analysis.get("repository_intelligence", {}).get("code_structure", {})
        
        if code_structure:
            # Look for refactoring opportunities
            refactor_opportunities = self._identify_refactoring_opportunities(code_structure)
            opportunities.extend(refactor_opportunities)
            
            # Look for performance opportunities
            performance_opportunities = self._identify_performance_opportunities(code_structure)
            opportunities.extend(performance_opportunities)
            
            # Look for security opportunities
            security_opportunities = self._identify_security_opportunities(code_structure)
            opportunities.extend(security_opportunities)
        
        return opportunities
    
    async def _detect_documentation_opportunities(
        self, 
        repo_name: str, 
        repo_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect documentation improvement opportunities."""
        opportunities = []
        
        guidelines = repo_analysis.get("repository_intelligence", {}).get("guidelines", {})
        
        # Check for missing documentation
        if not guidelines.get("guidelines"):
            opportunities.append({
                "type": "documentation",
                "subtype": "missing_guidelines",
                "title": "Create contribution guidelines",
                "description": "Repository lacks contribution guidelines which would help new contributors",
                "complexity": "medium",
                "estimated_effort": "4-8 hours",
                "skills_required": ["technical_writing", "project_management"],
                "base_score": 8.0,
            })
        
        # Check for README improvements
        basic_info = repo_analysis.get("repository_intelligence", {}).get("basic_info", {})
        if not basic_info.get("description") or len(basic_info.get("description", "")) < 50:
            opportunities.append({
                "type": "documentation",
                "subtype": "readme_improvement",
                "title": "Improve README documentation",
                "description": "Repository README could be enhanced with better description and usage examples",
                "complexity": "low",
                "estimated_effort": "2-4 hours",
                "skills_required": ["technical_writing"],
                "base_score": 6.0,
            })
        
        return opportunities
    
    async def _detect_testing_opportunities(
        self, 
        repo_name: str, 
        repo_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect testing improvement opportunities."""
        opportunities = []
        
        # This would require more sophisticated analysis of the codebase
        # For now, we'll provide general testing opportunities
        
        code_structure = repo_analysis.get("repository_intelligence", {}).get("code_structure", {})
        file_structure = code_structure.get("file_structure", {})
        
        # Check if test directory exists
        has_tests = any(
            "test" in name.lower() for name in file_structure.keys()
        )
        
        if not has_tests:
            opportunities.append({
                "type": "testing",
                "subtype": "missing_tests",
                "title": "Add test infrastructure",
                "description": "Repository lacks comprehensive testing infrastructure",
                "complexity": "high",
                "estimated_effort": "16-32 hours",
                "skills_required": ["testing", "test_automation"],
                "base_score": 9.0,
            })
        else:
            # Look for specific testing improvements
            opportunities.append({
                "type": "testing",
                "subtype": "test_coverage",
                "title": "Improve test coverage",
                "description": "Enhance test coverage for critical components",
                "complexity": "medium",
                "estimated_effort": "8-16 hours",
                "skills_required": ["testing", "code_analysis"],
                "base_score": 7.0,
            })
        
        return opportunities
    
    async def _score_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        repo_analysis: Dict[str, Any],
        contributor_skills: Optional[List[str]],
        focus_areas: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Score opportunities based on multiple factors."""
        scored_opportunities = []
        
        for opp in opportunities:
            score_components = {
                "technical_impact": self._score_technical_impact(opp, repo_analysis),
                "learning_value": self._score_learning_value(opp, contributor_skills),
                "acceptance_likelihood": self._score_acceptance_likelihood(opp, repo_analysis),
                "maintainer_alignment": self._score_maintainer_alignment(opp, repo_analysis),
                "community_benefit": self._score_community_benefit(opp, repo_analysis),
            }
            
            # Calculate weighted score
            total_score = sum(
                score_components[component] * self.scoring_weights[component]
                for component in score_components
            )
            
            # Apply focus area bonus
            if focus_areas and opp.get("type") in focus_areas:
                total_score *= 1.2
            
            # Apply skill match bonus
            if contributor_skills:
                required_skills = opp.get("skills_required", [])
                skill_match = len(set(contributor_skills) & set(required_skills)) / max(len(required_skills), 1)
                total_score *= (1 + skill_match * 0.3)
            
            opp["score"] = round(total_score, 2)
            opp["score_components"] = score_components
            scored_opportunities.append(opp)
        
        # Sort by score
        return sorted(scored_opportunities, key=lambda x: x["score"], reverse=True)
    
    def _score_technical_impact(self, opportunity: Dict[str, Any], repo_analysis: Dict[str, Any]) -> float:
        """Score technical impact of opportunity."""
        opp_type = opportunity.get("type", "")
        complexity = opportunity.get("complexity", "medium")
        
        base_scores = {
            "issue": 6.0,
            "code": 8.0,
            "documentation": 5.0,
            "testing": 7.0,
        }
        
        complexity_multipliers = {
            "low": 0.8,
            "medium": 1.0,
            "high": 1.3,
        }
        
        base_score = base_scores.get(opp_type, 5.0)
        multiplier = complexity_multipliers.get(complexity, 1.0)
        
        return min(base_score * multiplier, 10.0)
    
    def _score_learning_value(self, opportunity: Dict[str, Any], contributor_skills: Optional[List[str]]) -> float:
        """Score learning value for contributor."""
        required_skills = opportunity.get("skills_required", [])
        
        if not contributor_skills:
            return 7.0  # Default score when skills unknown
        
        # Higher score for opportunities that teach new skills
        new_skills = set(required_skills) - set(contributor_skills)
        skill_overlap = set(required_skills) & set(contributor_skills)
        
        if len(new_skills) > 0 and len(skill_overlap) > 0:
            return 9.0  # Perfect learning opportunity
        elif len(new_skills) > 0:
            return 8.0  # Challenging but learnable
        elif len(skill_overlap) > 0:
            return 6.0  # Uses existing skills
        else:
            return 4.0  # No clear skill match
    
    def _score_acceptance_likelihood(self, opportunity: Dict[str, Any], repo_analysis: Dict[str, Any]) -> float:
        """Score likelihood of acceptance."""
        opp_type = opportunity.get("type", "")
        
        # Base acceptance rates by type
        base_rates = {
            "issue": 8.0,  # Issues are usually welcome
            "documentation": 9.0,  # Documentation is almost always welcome
            "testing": 8.5,  # Testing improvements are valued
            "code": 6.0,  # Code changes need more scrutiny
        }
        
        base_score = base_rates.get(opp_type, 6.0)
        
        # Adjust based on repository characteristics
        basic_info = repo_analysis.get("repository_intelligence", {}).get("basic_info", {})
        activity_level = basic_info.get("activity_level", "unknown")
        
        if activity_level in ["very_active", "active"]:
            base_score *= 1.1  # Active repos more likely to accept contributions
        elif activity_level in ["low", "inactive"]:
            base_score *= 0.8  # Inactive repos less likely to respond
        
        return min(base_score, 10.0)
    
    def _score_maintainer_alignment(self, opportunity: Dict[str, Any], repo_analysis: Dict[str, Any]) -> float:
        """Score alignment with maintainer preferences."""
        # This would be based on maintainer pattern analysis
        # For now, provide a reasonable default
        return 7.0
    
    def _score_community_benefit(self, opportunity: Dict[str, Any], repo_analysis: Dict[str, Any]) -> float:
        """Score benefit to the community."""
        opp_type = opportunity.get("type", "")
        
        community_scores = {
            "documentation": 9.0,  # High community benefit
            "testing": 8.0,  # Good community benefit
            "issue": 7.0,  # Moderate community benefit
            "code": 6.0,  # Depends on the specific change
        }
        
        return community_scores.get(opp_type, 6.0)
    
    def _filter_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        contributor_skills: Optional[List[str]],
        focus_areas: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Filter opportunities based on criteria."""
        filtered = []
        
        for opp in opportunities:
            # Minimum score threshold
            if opp.get("score", 0) < self.config.contribution.min_score:
                continue
            
            # Focus area filter
            if focus_areas and opp.get("type") not in focus_areas:
                continue
            
            # Complexity filter based on skills
            if contributor_skills:
                complexity = opp.get("complexity", "medium")
                required_skills = opp.get("skills_required", [])
                
                # Skip high complexity if no matching skills
                if complexity == "high" and not set(contributor_skills) & set(required_skills):
                    continue
            
            filtered.append(opp)
        
        return filtered
    
    async def _ai_enhance_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        repo_analysis: Dict[str, Any],
        contributor_skills: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Use AI to enhance opportunity analysis."""
        try:
            # Prepare contributor profile
            contributor_profile = {
                "skills": contributor_skills or [],
                "experience_level": "intermediate",  # Could be determined from skills
                "preferences": [],
            }
            
            # Get AI analysis
            ai_result = await self.ai_engine.analyze_repository_for_opportunities(
                repo_analysis,
                focus_areas=[opp["type"] for opp in opportunities[:5]]
            )
            
            return ai_result
            
        except Exception as e:
            self.logger.warning(f"AI enhancement failed: {e}")
            return {"error": str(e)}
    
    def _generate_opportunity_summary(self, opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary of detected opportunities."""
        if not opportunities:
            return {"total": 0}
        
        by_type = Counter(opp["type"] for opp in opportunities)
        by_complexity = Counter(opp.get("complexity", "unknown") for opp in opportunities)
        
        avg_score = sum(opp.get("score", 0) for opp in opportunities) / len(opportunities)
        
        return {
            "total_opportunities": len(opportunities),
            "by_type": dict(by_type),
            "by_complexity": dict(by_complexity),
            "average_score": round(avg_score, 2),
            "top_opportunity": opportunities[0] if opportunities else None,
            "recommended_next_steps": self._generate_next_steps(opportunities[:3]),
        }
    
    def _generate_next_steps(self, top_opportunities: List[Dict[str, Any]]) -> List[str]:
        """Generate recommended next steps."""
        if not top_opportunities:
            return ["No opportunities identified"]
        
        steps = []
        
        for i, opp in enumerate(top_opportunities[:3], 1):
            step = f"{i}. {opp.get('title', 'Unknown opportunity')} (Score: {opp.get('score', 0)})"
            steps.append(step)
        
        return steps
    
    # Helper methods for opportunity detection
    def _assess_issue_complexity(self, issue: Dict[str, Any]) -> str:
        """Assess complexity of an issue."""
        labels = [label.lower() for label in issue.get("labels", [])]
        
        if any(label in labels for label in ["easy", "beginner", "good first issue"]):
            return "low"
        elif any(label in labels for label in ["hard", "complex", "advanced"]):
            return "high"
        else:
            return "medium"
    
    def _estimate_issue_effort(self, issue: Dict[str, Any]) -> str:
        """Estimate effort required for an issue."""
        complexity = self._assess_issue_complexity(issue)
        
        effort_map = {
            "low": "2-4 hours",
            "medium": "4-8 hours", 
            "high": "8-16 hours",
        }
        
        return effort_map.get(complexity, "4-8 hours")
    
    def _extract_skills_from_issue(self, issue: Dict[str, Any]) -> List[str]:
        """Extract required skills from issue."""
        labels = [label.lower() for label in issue.get("labels", [])]
        title = issue.get("title", "").lower()
        body = issue.get("body", "").lower()
        
        skills = []
        
        # Language skills
        if any(term in title + body for term in ["c++", "cpp"]):
            skills.append("cpp")
        if any(term in title + body for term in ["python", "py"]):
            skills.append("python")
        if any(term in title + body for term in ["javascript", "js"]):
            skills.append("javascript")
        
        # Domain skills
        if any(term in labels for term in ["documentation", "docs"]):
            skills.append("technical_writing")
        if any(term in labels for term in ["test", "testing"]):
            skills.append("testing")
        if any(term in labels for term in ["ui", "frontend"]):
            skills.append("frontend")
        if any(term in labels for term in ["backend", "api"]):
            skills.append("backend")
        
        return skills or ["general"]
    
    async def _find_documentation_issues(self, repo_name: str) -> List[Dict[str, Any]]:
        """Find documentation-related issues."""
        try:
            doc_issues = await self.github_client.get_open_issues(
                repo_name, 
                labels=["documentation", "docs"], 
                limit=10
            )
            
            opportunities = []
            for issue in doc_issues:
                opportunities.append({
                    "type": "issue",
                    "subtype": "documentation_issue",
                    "title": f"Documentation: {issue.get('title', 'Unknown')}",
                    "description": issue.get("body", "")[:500],
                    "issue_number": issue.get("number"),
                    "labels": issue.get("labels", []),
                    "url": issue.get("url", ""),
                    "complexity": "low",
                    "estimated_effort": "2-4 hours",
                    "skills_required": ["technical_writing"],
                    "base_score": 7.0,
                })
            
            return opportunities
            
        except Exception as e:
            self.logger.warning(f"Could not find documentation issues: {e}")
            return []
    
    async def _find_testing_issues(self, repo_name: str) -> List[Dict[str, Any]]:
        """Find testing-related issues."""
        try:
            test_issues = await self.github_client.get_open_issues(
                repo_name, 
                labels=["test", "testing"], 
                limit=10
            )
            
            opportunities = []
            for issue in test_issues:
                opportunities.append({
                    "type": "issue",
                    "subtype": "testing_issue",
                    "title": f"Testing: {issue.get('title', 'Unknown')}",
                    "description": issue.get("body", "")[:500],
                    "issue_number": issue.get("number"),
                    "labels": issue.get("labels", []),
                    "url": issue.get("url", ""),
                    "complexity": "medium",
                    "estimated_effort": "4-8 hours",
                    "skills_required": ["testing"],
                    "base_score": 8.0,
                })
            
            return opportunities
            
        except Exception as e:
            self.logger.warning(f"Could not find testing issues: {e}")
            return []
    
    def _identify_refactoring_opportunities(self, code_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify code refactoring opportunities."""
        # This would require more sophisticated static analysis
        # For now, return placeholder opportunities
        return []
    
    def _identify_performance_opportunities(self, code_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify performance improvement opportunities."""
        # This would require performance profiling and analysis
        # For now, return placeholder opportunities
        return []
    
    def _identify_security_opportunities(self, code_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify security improvement opportunities."""
        # This would require security analysis tools
        # For now, return placeholder opportunities
        return []
