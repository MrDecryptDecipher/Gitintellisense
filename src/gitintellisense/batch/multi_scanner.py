"""
Multi-repository scanner for batch processing.

This module provides capabilities for scanning and analyzing
multiple repositories simultaneously with advanced scheduling
and resource management.
"""

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..core.analyzer import RepositoryAnalyzer
from ..analysis.opportunities import OpportunityDetector
from ..core.github_client import GitHubClient
from ..utils.config import Config, get_config
from ..utils.logging import get_logger
from ..utils.database import DatabaseManager


class MultiRepositoryScanner:
    """
    Advanced multi-repository scanner with batch processing capabilities.
    
    Features:
    - Concurrent repository analysis
    - Intelligent scheduling and rate limiting
    - Progress tracking and reporting
    - Error handling and retry logic
    - Resource optimization
    - Priority-based processing
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize multi-repository scanner."""
        self.config = config or get_config()
        self.logger = get_logger("multi_scanner")
        
        # Initialize components
        self.analyzer = RepositoryAnalyzer(config)
        self.opportunity_detector = OpportunityDetector(config)
        self.github_client = GitHubClient(config)
        self.db = DatabaseManager(config)
        
        # Scanning configuration
        self.max_concurrent = self.config.scanning.get("max_concurrent", 5)
        self.rate_limit_delay = self.config.scanning.get("rate_limit_delay", 1.0)
        self.retry_attempts = self.config.scanning.get("retry_attempts", 3)
        self.timeout_seconds = self.config.scanning.get("timeout_seconds", 300)
        
        # State tracking
        self.active_scans: Set[str] = set()
        self.scan_results: Dict[str, Dict[str, Any]] = {}
        self.scan_errors: Dict[str, List[str]] = {}
        
    async def scan_repositories(
        self, 
        repositories: List[str],
        priority_order: bool = True,
        include_opportunities: bool = True,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Scan multiple repositories with advanced batch processing.
        
        Args:
            repositories: List of repository names to scan
            priority_order: Whether to prioritize repositories by importance
            include_opportunities: Whether to detect opportunities
            force_refresh: Whether to force refresh of existing analyses
        
        Returns:
            Comprehensive scan results with statistics
        """
        self.logger.info(f"Starting multi-repository scan of {len(repositories)} repositories")
        
        start_time = time.time()
        
        try:
            # Prepare repositories for scanning
            scan_queue = await self._prepare_scan_queue(
                repositories, 
                priority_order, 
                force_refresh
            )
            
            # Execute batch scanning
            results = await self._execute_batch_scan(
                scan_queue, 
                include_opportunities
            )
            
            # Generate comprehensive report
            scan_report = self._generate_scan_report(results, start_time)
            
            # Store batch results
            await self._store_batch_results(scan_report)
            
            return scan_report
            
        except Exception as e:
            self.logger.error(f"Multi-repository scan failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "scanned_repositories": 0,
                "total_repositories": len(repositories),
                "duration_seconds": time.time() - start_time,
            }
    
    async def scan_github_trending(
        self, 
        language: Optional[str] = None,
        time_range: str = "daily",
        limit: int = 25
    ) -> Dict[str, Any]:
        """
        Scan trending repositories from GitHub.
        
        Args:
            language: Programming language filter
            time_range: Trending time range (daily, weekly, monthly)
            limit: Maximum number of repositories to scan
        
        Returns:
            Scan results for trending repositories
        """
        self.logger.info(f"Scanning GitHub trending repositories ({time_range}, {language or 'all languages'})")
        
        try:
            # Get trending repositories
            trending_repos = await self._get_trending_repositories(language, time_range, limit)
            
            # Scan trending repositories
            return await self.scan_repositories(
                trending_repos,
                priority_order=True,
                include_opportunities=True,
                force_refresh=False
            )
            
        except Exception as e:
            self.logger.error(f"Failed to scan trending repositories: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def scan_organization_repositories(
        self, 
        organization: str,
        include_forks: bool = False,
        min_stars: int = 0,
        max_repositories: int = 50
    ) -> Dict[str, Any]:
        """
        Scan all repositories from a GitHub organization.
        
        Args:
            organization: GitHub organization name
            include_forks: Whether to include forked repositories
            min_stars: Minimum star count filter
            max_repositories: Maximum number of repositories to scan
        
        Returns:
            Scan results for organization repositories
        """
        self.logger.info(f"Scanning repositories from organization: {organization}")
        
        try:
            # Get organization repositories
            org_repos = await self._get_organization_repositories(
                organization, 
                include_forks, 
                min_stars, 
                max_repositories
            )
            
            # Scan organization repositories
            return await self.scan_repositories(
                org_repos,
                priority_order=True,
                include_opportunities=True,
                force_refresh=False
            )
            
        except Exception as e:
            self.logger.error(f"Failed to scan organization repositories: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def continuous_scanning(
        self, 
        repositories: List[str],
        scan_interval_hours: int = 24,
        max_iterations: Optional[int] = None
    ) -> None:
        """
        Continuously scan repositories at regular intervals.
        
        Args:
            repositories: List of repositories to scan continuously
            scan_interval_hours: Hours between scans
            max_iterations: Maximum number of scan iterations (None for infinite)
        """
        self.logger.info(f"Starting continuous scanning of {len(repositories)} repositories")
        
        iteration = 0
        
        while max_iterations is None or iteration < max_iterations:
            try:
                self.logger.info(f"Starting scan iteration {iteration + 1}")
                
                # Perform scan
                results = await self.scan_repositories(
                    repositories,
                    priority_order=True,
                    include_opportunities=True,
                    force_refresh=True
                )
                
                self.logger.info(f"Scan iteration {iteration + 1} completed: {results.get('status')}")
                
                iteration += 1
                
                # Wait for next iteration
                if max_iterations is None or iteration < max_iterations:
                    await asyncio.sleep(scan_interval_hours * 3600)
                    
            except KeyboardInterrupt:
                self.logger.info("Continuous scanning stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Scan iteration {iteration + 1} failed: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    async def _prepare_scan_queue(
        self, 
        repositories: List[str],
        priority_order: bool,
        force_refresh: bool
    ) -> List[Tuple[str, int]]:
        """Prepare and prioritize repositories for scanning."""
        scan_queue = []
        
        for repo in repositories:
            # Calculate priority score
            priority = await self._calculate_repository_priority(repo)
            
            # Check if scan is needed
            if force_refresh or await self._needs_scanning(repo):
                scan_queue.append((repo, priority))
        
        # Sort by priority if requested
        if priority_order:
            scan_queue.sort(key=lambda x: x[1], reverse=True)
        
        return scan_queue
    
    async def _execute_batch_scan(
        self, 
        scan_queue: List[Tuple[str, int]],
        include_opportunities: bool
    ) -> Dict[str, Dict[str, Any]]:
        """Execute batch scanning with concurrency control."""
        results = {}
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def scan_single_repository(repo_info: Tuple[str, int]) -> Tuple[str, Dict[str, Any]]:
            repo, priority = repo_info
            
            async with semaphore:
                try:
                    # Add rate limiting
                    await asyncio.sleep(self.rate_limit_delay)
                    
                    # Perform repository analysis
                    analysis_result = await self._scan_repository_with_retry(repo)
                    
                    # Detect opportunities if requested
                    opportunities = []
                    if include_opportunities and analysis_result.get("status") == "success":
                        opportunities = await self._detect_opportunities_with_retry(repo, analysis_result)
                    
                    return repo, {
                        "status": "success",
                        "priority": priority,
                        "analysis": analysis_result,
                        "opportunities": opportunities,
                        "scanned_at": datetime.now().isoformat(),
                    }
                    
                except Exception as e:
                    self.logger.error(f"Failed to scan repository {repo}: {e}")
                    return repo, {
                        "status": "failed",
                        "priority": priority,
                        "error": str(e),
                        "scanned_at": datetime.now().isoformat(),
                    }
        
        # Execute concurrent scanning
        tasks = [scan_single_repository(repo_info) for repo_info in scan_queue]
        
        for completed_task in asyncio.as_completed(tasks):
            repo, result = await completed_task
            results[repo] = result
            
            # Log progress
            completed = len(results)
            total = len(scan_queue)
            self.logger.info(f"Scan progress: {completed}/{total} repositories completed")
        
        return results
    
    async def _scan_repository_with_retry(self, repository: str) -> Dict[str, Any]:
        """Scan repository with retry logic."""
        for attempt in range(self.retry_attempts):
            try:
                result = await asyncio.wait_for(
                    self.analyzer.analyze_repository(repository),
                    timeout=self.timeout_seconds
                )
                return result
                
            except asyncio.TimeoutError:
                self.logger.warning(f"Repository scan timeout for {repository} (attempt {attempt + 1})")
                if attempt == self.retry_attempts - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                self.logger.warning(f"Repository scan failed for {repository} (attempt {attempt + 1}): {e}")
                if attempt == self.retry_attempts - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
    
    async def _detect_opportunities_with_retry(
        self, 
        repository: str, 
        analysis_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect opportunities with retry logic."""
        for attempt in range(self.retry_attempts):
            try:
                opportunities = await asyncio.wait_for(
                    self.opportunity_detector.detect_opportunities(repository, analysis_result),
                    timeout=self.timeout_seconds
                )
                return opportunities.get("opportunities", [])
                
            except asyncio.TimeoutError:
                self.logger.warning(f"Opportunity detection timeout for {repository} (attempt {attempt + 1})")
                if attempt == self.retry_attempts - 1:
                    return []
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                self.logger.warning(f"Opportunity detection failed for {repository} (attempt {attempt + 1}): {e}")
                if attempt == self.retry_attempts - 1:
                    return []
                await asyncio.sleep(2 ** attempt)
    
    async def _calculate_repository_priority(self, repository: str) -> int:
        """Calculate priority score for repository."""
        try:
            # Get basic repository info
            repo_info = await self.github_client.get_repository_info(repository)
            
            # Calculate priority based on various factors
            priority = 0
            
            # Star count (0-50 points)
            stars = repo_info.get("stargazers_count", 0)
            priority += min(50, stars // 100)
            
            # Activity level (0-30 points)
            updated_at = repo_info.get("updated_at", "")
            if updated_at:
                days_since_update = (datetime.now() - datetime.fromisoformat(updated_at.replace("Z", "+00:00"))).days
                if days_since_update < 7:
                    priority += 30
                elif days_since_update < 30:
                    priority += 20
                elif days_since_update < 90:
                    priority += 10
            
            # Language popularity (0-20 points)
            language = repo_info.get("language", "").lower()
            popular_languages = ["python", "javascript", "typescript", "java", "go", "rust", "c++"]
            if language in popular_languages:
                priority += 20
            
            return priority
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate priority for {repository}: {e}")
            return 0
    
    async def _needs_scanning(self, repository: str) -> bool:
        """Check if repository needs scanning."""
        try:
            # Check if repository was analyzed recently
            analyses = self.db.get_repository_analyses(repository=repository, limit=1)
            
            if not analyses:
                return True
            
            last_analysis = analyses[0]
            last_scan_time = datetime.fromisoformat(last_analysis["analysis_date"])
            
            # Scan if last analysis is older than 24 hours
            return (datetime.now() - last_scan_time) > timedelta(hours=24)
            
        except Exception as e:
            self.logger.warning(f"Failed to check scan status for {repository}: {e}")
            return True

    async def _get_trending_repositories(
        self,
        language: Optional[str],
        time_range: str,
        limit: int
    ) -> List[str]:
        """Get trending repositories from GitHub."""
        try:
            # Use GitHub search API to find trending repositories
            query = "stars:>100"

            if language:
                query += f" language:{language}"

            # Add time filter
            if time_range == "daily":
                date_filter = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                query += f" created:>{date_filter}"
            elif time_range == "weekly":
                date_filter = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                query += f" created:>{date_filter}"
            elif time_range == "monthly":
                date_filter = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                query += f" created:>{date_filter}"

            # Search repositories
            search_results = await self.github_client.search_repositories(query, limit)

            return [repo["full_name"] for repo in search_results.get("items", [])]

        except Exception as e:
            self.logger.error(f"Failed to get trending repositories: {e}")
            return []

    async def _get_organization_repositories(
        self,
        organization: str,
        include_forks: bool,
        min_stars: int,
        max_repositories: int
    ) -> List[str]:
        """Get repositories from a GitHub organization."""
        try:
            # Get organization repositories
            org_repos = await self.github_client.get_organization_repositories(
                organization,
                max_repositories
            )

            filtered_repos = []

            for repo in org_repos:
                # Filter forks
                if not include_forks and repo.get("fork", False):
                    continue

                # Filter by stars
                if repo.get("stargazers_count", 0) < min_stars:
                    continue

                filtered_repos.append(repo["full_name"])

            return filtered_repos[:max_repositories]

        except Exception as e:
            self.logger.error(f"Failed to get organization repositories: {e}")
            return []

    def _generate_scan_report(
        self,
        results: Dict[str, Dict[str, Any]],
        start_time: float
    ) -> Dict[str, Any]:
        """Generate comprehensive scan report."""
        total_repositories = len(results)
        successful_scans = len([r for r in results.values() if r["status"] == "success"])
        failed_scans = total_repositories - successful_scans

        # Calculate statistics
        total_opportunities = sum(
            len(r.get("opportunities", []))
            for r in results.values()
            if r["status"] == "success"
        )

        # Calculate average health score
        health_scores = [
            r["analysis"].get("health_score", 0)
            for r in results.values()
            if r["status"] == "success" and "analysis" in r
        ]
        avg_health_score = sum(health_scores) / len(health_scores) if health_scores else 0

        # Group by priority
        high_priority = len([r for r in results.values() if r.get("priority", 0) >= 70])
        medium_priority = len([r for r in results.values() if 30 <= r.get("priority", 0) < 70])
        low_priority = len([r for r in results.values() if r.get("priority", 0) < 30])

        return {
            "status": "completed",
            "summary": {
                "total_repositories": total_repositories,
                "successful_scans": successful_scans,
                "failed_scans": failed_scans,
                "success_rate": (successful_scans / total_repositories * 100) if total_repositories > 0 else 0,
                "total_opportunities": total_opportunities,
                "avg_health_score": round(avg_health_score, 1),
                "duration_seconds": round(time.time() - start_time, 2),
            },
            "priority_distribution": {
                "high_priority": high_priority,
                "medium_priority": medium_priority,
                "low_priority": low_priority,
            },
            "detailed_results": results,
            "generated_at": datetime.now().isoformat(),
        }

    async def _store_batch_results(self, scan_report: Dict[str, Any]) -> None:
        """Store batch scan results in database."""
        try:
            # Store individual repository results
            for repo, result in scan_report["detailed_results"].items():
                if result["status"] == "success" and "analysis" in result:
                    # Store analysis result
                    analysis = result["analysis"]
                    self.db.store_analysis(
                        repo,
                        analysis.get("health_score", 0),
                        analysis.get("activity_level", "unknown"),
                        analysis.get("contribution_difficulty", "unknown"),
                        analysis.get("good_first_issues", 0),
                        analysis.get("has_guidelines", False),
                        analysis.get("recommendation", "")
                    )

                    # Store opportunities
                    for opportunity in result.get("opportunities", []):
                        self.db.store_opportunity(
                            repo,
                            opportunity.get("type", "unknown"),
                            opportunity.get("title", ""),
                            opportunity.get("description", ""),
                            opportunity.get("complexity", "unknown"),
                            opportunity.get("skills_required", []),
                            opportunity.get("score", 0),
                            opportunity.get("issue_number")
                        )

            self.logger.info("Batch scan results stored successfully")

        except Exception as e:
            self.logger.error(f"Failed to store batch results: {e}")

    def get_scan_statistics(self) -> Dict[str, Any]:
        """Get scanning statistics."""
        try:
            # Get recent analyses
            recent_analyses = self.db.get_repository_analyses(limit=1000)

            # Calculate statistics
            total_analyses = len(recent_analyses)

            # Group by date
            daily_stats = {}
            for analysis in recent_analyses:
                date = analysis["analysis_date"][:10]  # Get date part
                if date not in daily_stats:
                    daily_stats[date] = 0
                daily_stats[date] += 1

            # Get top repositories by health score
            top_repos = sorted(
                recent_analyses,
                key=lambda x: x["health_score"],
                reverse=True
            )[:10]

            return {
                "total_analyses": total_analyses,
                "daily_statistics": daily_stats,
                "top_repositories": top_repos,
                "active_scans": len(self.active_scans),
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get scan statistics: {e}")
            return {"error": str(e)}
