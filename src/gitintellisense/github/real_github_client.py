"""
Real GitHub API Client for fetching actual user data.

This module provides functionality to fetch real GitHub data for a user,
including their actual pull requests, contributions, and repositories.
"""

import asyncio
import aiohttp
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..utils.logging import get_logger


@dataclass
class GitHubPR:
    """Represents a GitHub Pull Request."""
    number: int
    title: str
    state: str
    repository: str
    url: str
    created_at: str
    merged_at: Optional[str]
    author: str
    additions: int
    deletions: int
    files_changed: int
    labels: List[str]


class RealGitHubClient:
    """
    Real GitHub API client for fetching actual user data.
    
    This client fetches real data from GitHub API for the authenticated user.
    """
    
    def __init__(self, github_token: Optional[str] = None):
        """Initialize the GitHub client."""
        self.logger = get_logger("real_github_client")
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.base_url = "https://api.github.com"
        self.session = None
        
        if not self.github_token:
            self.logger.warning("No GitHub token provided. Some features may not work.")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'token {self.github_token}' if self.github_token else '',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'GitIntellisense/1.0'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def get_authenticated_user(self) -> Optional[Dict[str, Any]]:
        """Get the authenticated user's information."""
        if not self.github_token:
            return None
            
        try:
            async with self.session.get(f"{self.base_url}/user") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    self.logger.error(f"Failed to get user info: {response.status}")
                    return None
        except Exception as e:
            self.logger.error(f"Error getting user info: {e}")
            return None
    
    async def get_user_pull_requests(self, username: str, limit: int = 100) -> List[GitHubPR]:
        """
        Get all pull requests created by the user across all repositories.

        Args:
            username: GitHub username
            limit: Maximum number of PRs to fetch

        Returns:
            List of GitHubPR objects
        """
        if not self.github_token:
            self.logger.info("No GitHub token - fetching public data only")
        
        try:
            # Search for PRs created by the user
            query = f"type:pr author:{username}"
            
            async with self.session.get(
                f"{self.base_url}/search/issues",
                params={
                    'q': query,
                    'sort': 'created',
                    'order': 'desc',
                    'per_page': min(limit, 100)
                }
            ) as response:
                if response.status != 200:
                    self.logger.error(f"Failed to search PRs: {response.status}")
                    return []
                
                data = await response.json()
                prs = []
                
                for item in data.get('items', []):
                    # Extract repository info
                    repo_url = item.get('repository_url', '')
                    repo_parts = repo_url.split('/') if repo_url else []
                    repository = repo_parts[-2:] if len(repo_parts) >= 2 else ['unknown', 'repo']

                    # Determine state (check if merged)
                    state = item.get('state', 'unknown')
                    merged_at = None
                    if 'pull_request' in item and item['pull_request'].get('merged_at'):
                        state = 'merged'
                        merged_at = item['pull_request']['merged_at']

                    # Get detailed PR information if we have a token
                    additions = 0
                    deletions = 0
                    files_changed = 0

                    if self.github_token and 'pull_request' in item:
                        pr_data = await self._get_pr_details(item['pull_request']['url'])
                        if pr_data:
                            additions = pr_data.get('additions', 0)
                            deletions = pr_data.get('deletions', 0)
                            files_changed = pr_data.get('changed_files', 0)

                    pr = GitHubPR(
                        number=item['number'],
                        title=item['title'],
                        state=state,
                        repository=repository,
                        url=item['html_url'],
                        created_at=item['created_at'],
                        merged_at=merged_at,
                        author=username,
                        additions=additions,
                        deletions=deletions,
                        files_changed=files_changed,
                        labels=[label['name'] for label in item.get('labels', [])]
                    )
                    prs.append(pr)
                
                self.logger.info(f"Found {len(prs)} PRs for user {username}")
                return prs
                
        except Exception as e:
            self.logger.error(f"Error fetching user PRs: {e}")
            return []
    
    async def _get_pr_details(self, pr_url: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific PR."""
        try:
            async with self.session.get(pr_url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
        except Exception as e:
            self.logger.error(f"Error getting PR details: {e}")
            return None
    
    async def get_user_repositories(self, username: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get repositories owned by the user.

        Args:
            username: GitHub username
            limit: Maximum number of repositories to fetch

        Returns:
            List of repository data
        """
        # Public repositories can be fetched without authentication
        
        try:
            repos = []
            page = 1
            per_page = min(100, limit)
            
            while len(repos) < limit:
                async with self.session.get(
                    f"{self.base_url}/users/{username}/repos",
                    params={
                        'page': page,
                        'per_page': per_page,
                        'sort': 'updated',
                        'direction': 'desc'
                    }
                ) as response:
                    if response.status != 200:
                        break
                    
                    page_repos = await response.json()
                    if not page_repos:
                        break
                    
                    repos.extend(page_repos)
                    page += 1
                    
                    if len(page_repos) < per_page:
                        break
            
            return repos[:limit]
            
        except Exception as e:
            self.logger.error(f"Error fetching user repositories: {e}")
            return []
    
    async def get_user_contributions_stats(self, username: str) -> Dict[str, Any]:
        """
        Get contribution statistics for the user.
        
        Args:
            username: GitHub username
            
        Returns:
            Dictionary with contribution statistics
        """
        try:
            # Get user's public events (contributions)
            async with self.session.get(
                f"{self.base_url}/users/{username}/events/public",
                params={'per_page': 100}
            ) as response:
                if response.status != 200:
                    return {}
                
                events = await response.json()
                
                # Analyze contribution patterns
                stats = {
                    'total_events': len(events),
                    'push_events': 0,
                    'pr_events': 0,
                    'issue_events': 0,
                    'repositories_contributed': set(),
                    'recent_activity': []
                }
                
                for event in events:
                    event_type = event.get('type', '')
                    repo_name = event.get('repo', {}).get('name', '')
                    
                    if repo_name:
                        stats['repositories_contributed'].add(repo_name)
                    
                    if event_type == 'PushEvent':
                        stats['push_events'] += 1
                    elif event_type == 'PullRequestEvent':
                        stats['pr_events'] += 1
                    elif event_type in ['IssuesEvent', 'IssueCommentEvent']:
                        stats['issue_events'] += 1
                    
                    # Add to recent activity
                    if len(stats['recent_activity']) < 10:
                        stats['recent_activity'].append({
                            'type': event_type,
                            'repo': repo_name,
                            'created_at': event.get('created_at', ''),
                            'public': event.get('public', False)
                        })
                
                stats['repositories_contributed'] = len(stats['repositories_contributed'])
                return stats
                
        except Exception as e:
            self.logger.error(f"Error fetching contribution stats: {e}")
            return {}
    
    async def get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile information.
        
        Args:
            username: GitHub username
            
        Returns:
            User profile data
        """
        try:
            async with self.session.get(f"{self.base_url}/users/{username}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
        except Exception as e:
            self.logger.error(f"Error fetching user profile: {e}")
            return None
    
    async def search_user_issues(self, username: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for issues created by the user.

        Args:
            username: GitHub username
            limit: Maximum number of issues to fetch

        Returns:
            List of issues created by the user
        """
        # Public issues can be searched without authentication (with rate limits)
        
        try:
            query = f"type:issue author:{username}"
            
            async with self.session.get(
                f"{self.base_url}/search/issues",
                params={
                    'q': query,
                    'sort': 'created',
                    'order': 'desc',
                    'per_page': min(limit, 100)
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('items', [])
                else:
                    return []
                    
        except Exception as e:
            self.logger.error(f"Error searching user issues: {e}")
            return []
    
    async def get_comprehensive_user_data(self, username: str) -> Dict[str, Any]:
        """
        Get comprehensive data about a user including PRs, repos, and stats.
        
        Args:
            username: GitHub username
            
        Returns:
            Comprehensive user data
        """
        self.logger.info(f"Fetching comprehensive data for user: {username}")
        
        # Fetch all data concurrently
        tasks = [
            self.get_user_profile(username),
            self.get_user_pull_requests(username, 100),
            self.get_user_repositories(username, 50),
            self.get_user_contributions_stats(username),
            self.search_user_issues(username, 50)
        ]
        
        try:
            profile, prs, repos, stats, issues = await asyncio.gather(*tasks)
            
            # Calculate additional metrics
            merged_prs = [pr for pr in prs if pr.state == 'merged']
            open_prs = [pr for pr in prs if pr.state == 'open']
            
            # Calculate success rate
            total_prs = len(prs)
            success_rate = (len(merged_prs) / total_prs * 100) if total_prs > 0 else 0
            
            # Calculate quality score (based on various factors)
            quality_score = self._calculate_quality_score(prs, repos, stats)
            
            return {
                'profile': profile,
                'pull_requests': {
                    'total': total_prs,
                    'merged': len(merged_prs),
                    'open': len(open_prs),
                    'closed': total_prs - len(merged_prs) - len(open_prs),
                    'success_rate': success_rate,
                    'recent_prs': prs[:10]  # Most recent 10 PRs
                },
                'repositories': {
                    'total': len(repos),
                    'public_repos': len([r for r in repos if not r.get('private', False)]),
                    'recent_repos': repos[:10]
                },
                'issues': {
                    'total': len(issues),
                    'recent_issues': issues[:10]
                },
                'statistics': stats,
                'metrics': {
                    'success_rate': success_rate,
                    'quality_score': quality_score,
                    'activity_level': self._assess_activity_level(stats),
                    'contribution_diversity': self._assess_contribution_diversity(prs, issues)
                },
                'fetched_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching comprehensive user data: {e}")
            return {}
    
    def _calculate_quality_score(self, prs: List[GitHubPR], repos: List[Dict], stats: Dict) -> float:
        """Calculate a quality score based on various factors."""
        score = 0.0
        
        # PR quality factors
        if prs:
            merged_rate = len([pr for pr in prs if pr.state == 'merged']) / len(prs)
            score += merged_rate * 30  # Up to 30 points for merge rate
            
            # Average PR size (balanced is better)
            avg_changes = sum(pr.additions + pr.deletions for pr in prs) / len(prs)
            if 50 <= avg_changes <= 500:  # Sweet spot for PR size
                score += 20
            elif avg_changes < 50 or avg_changes > 1000:
                score += 5
            else:
                score += 15
        
        # Repository factors
        if repos:
            public_repos = len([r for r in repos if not r.get('private', False)])
            score += min(public_repos * 2, 20)  # Up to 20 points for public repos
            
            # Stars and forks
            total_stars = sum(r.get('stargazers_count', 0) for r in repos)
            score += min(total_stars / 10, 15)  # Up to 15 points for stars
        
        # Activity factors
        recent_activity = stats.get('total_events', 0)
        score += min(recent_activity / 5, 15)  # Up to 15 points for activity
        
        return min(score, 100.0)
    
    def _assess_activity_level(self, stats: Dict) -> str:
        """Assess user's activity level."""
        total_events = stats.get('total_events', 0)
        
        if total_events >= 50:
            return 'very_active'
        elif total_events >= 20:
            return 'active'
        elif total_events >= 5:
            return 'moderate'
        else:
            return 'low'
    
    def _assess_contribution_diversity(self, prs: List[GitHubPR], issues: List[Dict]) -> str:
        """Assess diversity of contributions."""
        unique_repos = set()
        
        for pr in prs:
            if isinstance(pr.repository, list) and len(pr.repository) >= 2:
                unique_repos.add(f"{pr.repository[-2]}/{pr.repository[-1]}")
        
        for issue in issues:
            repo_url = issue.get('repository_url', '')
            if repo_url:
                repo_parts = repo_url.split('/')
                if len(repo_parts) >= 2:
                    unique_repos.add(f"{repo_parts[-2]}/{repo_parts[-1]}")
        
        repo_count = len(unique_repos)
        
        if repo_count >= 10:
            return 'very_diverse'
        elif repo_count >= 5:
            return 'diverse'
        elif repo_count >= 2:
            return 'moderate'
        else:
            return 'focused'
