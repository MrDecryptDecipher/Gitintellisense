"""
GitHub API client with advanced features for repository analysis.

This module provides a sophisticated GitHub API client with rate limiting,
error handling, and specialized methods for repository intelligence gathering.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import aiohttp
from github import Github, GithubException, RateLimitExceededException
from github.Repository import Repository
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.Commit import Commit

from ..utils.config import Config, get_config
from ..utils.logging import get_logger


class GitHubRateLimiter:
    """Rate limiter for GitHub API calls."""
    
    def __init__(self, requests_per_hour: int = 5000):
        """Initialize rate limiter."""
        self.requests_per_hour = requests_per_hour
        self.requests_per_second = requests_per_hour / 3600
        self.last_request_time = 0.0
        self.request_count = 0
        self.window_start = time.time()
    
    async def acquire(self) -> None:
        """Acquire permission to make a request."""
        current_time = time.time()
        
        # Reset window if needed
        if current_time - self.window_start >= 3600:
            self.request_count = 0
            self.window_start = current_time
        
        # Check if we've exceeded the hourly limit
        if self.request_count >= self.requests_per_hour:
            sleep_time = 3600 - (current_time - self.window_start)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                self.request_count = 0
                self.window_start = time.time()
        
        # Ensure we don't exceed per-second rate
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.requests_per_second
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1


class GitHubClient:
    """
    Advanced GitHub API client with rate limiting, error handling,
    and specialized methods for repository analysis.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize GitHub client."""
        self.config = config or get_config()
        self.logger = get_logger("github_client")
        
        # Initialize GitHub client
        self.github = Github(
            self.config.github.token,
            timeout=self.config.github.request_timeout,
            retry=self.config.github.max_retries,
        )
        
        # Initialize rate limiter
        self.rate_limiter = GitHubRateLimiter(
            self.config.github.rate_limit_per_hour
        )
        
        # Cache for repositories
        self._repo_cache: Dict[str, Repository] = {}
    
    async def _make_request(self, func, *args, **kwargs) -> Any:
        """Make a rate-limited GitHub API request with error handling."""
        await self.rate_limiter.acquire()
        
        max_retries = self.config.github.max_retries
        backoff_factor = self.config.github.retry_backoff_factor
        
        for attempt in range(max_retries + 1):
            try:
                # Log the API call
                self.logger.github_api_call(
                    endpoint=func.__name__,
                    attempt=attempt + 1,
                    max_attempts=max_retries + 1
                )
                
                result = func(*args, **kwargs)
                
                # Log rate limit status
                try:
                    rate_limit = self.github.get_rate_limit()
                    # Handle different PyGithub versions
                    if hasattr(rate_limit, 'core'):
                        remaining = rate_limit.core.remaining
                        reset_time = rate_limit.core.reset
                    else:
                        # Fallback for newer versions
                        remaining = getattr(rate_limit, 'remaining', 'unknown')
                        reset_time = getattr(rate_limit, 'reset', 'unknown')

                    # Convert reset_time to string if it's a datetime object
                    reset_time_str = reset_time
                    if hasattr(reset_time, 'isoformat'):
                        reset_time_str = reset_time.isoformat()
                    elif isinstance(reset_time, (int, float)):
                        reset_time_str = str(reset_time)

                    self.logger.github_rate_limit(
                        remaining=remaining,
                        reset_time=reset_time_str
                    )
                except Exception as e:
                    self.logger.warning(f"Could not get rate limit info: {e}")
                
                return result
                
            except RateLimitExceededException as e:
                reset_time = e.headers.get('X-RateLimit-Reset')
                if reset_time:
                    reset_datetime = datetime.fromtimestamp(int(reset_time))
                    sleep_time = (reset_datetime - datetime.now()).total_seconds()
                    
                    self.logger.warning(
                        f"Rate limit exceeded, sleeping for {sleep_time} seconds",
                        reset_time=reset_datetime.isoformat()
                    )
                    
                    await asyncio.sleep(max(sleep_time, 0))
                    continue
                else:
                    # Default sleep time if reset time not available
                    await asyncio.sleep(60)
                    continue
                    
            except GithubException as e:
                if attempt == max_retries:
                    self.logger.error(
                        f"GitHub API error after {max_retries + 1} attempts",
                        error=str(e),
                        status_code=e.status
                    )
                    raise
                
                # Exponential backoff
                sleep_time = backoff_factor ** attempt
                self.logger.warning(
                    f"GitHub API error, retrying in {sleep_time} seconds",
                    error=str(e),
                    attempt=attempt + 1,
                    sleep_time=sleep_time
                )
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(
                    f"Unexpected error in GitHub API call",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
        
        raise Exception(f"Failed to complete GitHub API request after {max_retries + 1} attempts")
    
    async def get_repository(self, repo_name: str) -> Repository:
        """Get repository with caching."""
        if repo_name not in self._repo_cache:
            repo = await self._make_request(self.github.get_repo, repo_name)
            self._repo_cache[repo_name] = repo
        
        return self._repo_cache[repo_name]
    
    async def get_repository_info(self, repo_name: str) -> Dict[str, Any]:
        """Get comprehensive repository information."""
        repo = await self.get_repository(repo_name)

        try:
            # Safely extract license information
            license_info = None
            if repo.license:
                try:
                    license_info = {
                        "name": repo.license.name,
                        "key": getattr(repo.license, 'key', ''),
                        "spdx_id": getattr(repo.license, 'spdx_id', ''),
                    }
                except Exception:
                    license_info = {"name": "Unknown"}

            # Safely get topics
            topics = []
            try:
                topics = list(repo.get_topics())
            except Exception:
                topics = []

            # Safely get languages
            languages = {}
            try:
                languages = await self._make_request(repo.get_languages)
            except Exception:
                languages = {}

            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description or "",
                "language": repo.language,
                "languages": languages,
                "stargazers_count": repo.stargazers_count,
                "watchers_count": repo.watchers_count,
                "forks_count": repo.forks_count,
                "open_issues_count": repo.open_issues_count,
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None,
                "size": repo.size,
                "default_branch": repo.default_branch,
                "topics": topics,
                "license": license_info,
                "has_issues": repo.has_issues,
                "has_projects": repo.has_projects,
                "has_wiki": repo.has_wiki,
                "archived": repo.archived,
                "disabled": repo.disabled,
                "private": repo.private,
                "html_url": repo.html_url,
                "clone_url": repo.clone_url,
                "ssh_url": repo.ssh_url,
            }
        except Exception as e:
            self.logger.error(f"Error getting repository info: {e}")
            # Return basic info if detailed extraction fails
            return {
                "name": getattr(repo, 'name', ''),
                "full_name": getattr(repo, 'full_name', ''),
                "description": getattr(repo, 'description', ''),
                "language": getattr(repo, 'language', ''),
                "stargazers_count": getattr(repo, 'stargazers_count', 0),
                "forks_count": getattr(repo, 'forks_count', 0),
                "open_issues_count": getattr(repo, 'open_issues_count', 0),
                "updated_at": None,
            }
    
    async def get_recent_commits(self, repo_name: str, since: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent commits from repository."""
        repo = await self.get_repository(repo_name)
        
        # Default to last 6 months if no since date provided
        if since is None:
            since = datetime.now() - timedelta(days=180)
        
        commits = await self._make_request(
            repo.get_commits,
            since=since
        )
        
        commit_data = []
        count = 0
        
        for commit in commits:
            if count >= limit:
                break
                
            commit_info = {
                "sha": commit.sha,
                "message": commit.commit.message,
                "author": {
                    "name": commit.commit.author.name,
                    "email": commit.commit.author.email,
                    "date": commit.commit.author.date.isoformat(),
                },
                "committer": {
                    "name": commit.commit.committer.name,
                    "email": commit.commit.committer.email,
                    "date": commit.commit.committer.date.isoformat(),
                },
                "url": commit.html_url,
                "stats": {
                    "additions": commit.stats.additions if commit.stats else 0,
                    "deletions": commit.stats.deletions if commit.stats else 0,
                    "total": commit.stats.total if commit.stats else 0,
                },
                "files_changed": commit.files.totalCount if hasattr(commit.files, 'totalCount') else (len(list(commit.files)) if commit.files else 0),
            }
            
            commit_data.append(commit_info)
            count += 1
        
        return commit_data
    
    async def get_open_issues(self, repo_name: str, labels: Optional[List[str]] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get open issues from repository."""
        repo = await self.get_repository(repo_name)
        
        # Get issues with optional label filtering
        if labels:
            issues = await self._make_request(
                repo.get_issues,
                state="open",
                labels=labels
            )
        else:
            issues = await self._make_request(
                repo.get_issues,
                state="open"
            )
        
        issue_data = []
        count = 0
        
        for issue in issues:
            if count >= limit:
                break
            
            # Skip pull requests (they appear in issues API)
            if issue.pull_request:
                continue
            
            try:
                # Safely extract issue data
                labels = []
                try:
                    labels = [label.name for label in issue.labels]
                except Exception:
                    labels = []

                assignees = []
                try:
                    assignees = [assignee.login for assignee in issue.assignees]
                except Exception:
                    assignees = []

                reactions = {}
                try:
                    reactions = {
                        "total": issue.reactions.get("total_count", 0),
                        "+1": issue.reactions.get("+1", 0),
                        "-1": issue.reactions.get("-1", 0),
                        "laugh": issue.reactions.get("laugh", 0),
                        "hooray": issue.reactions.get("hooray", 0),
                        "confused": issue.reactions.get("confused", 0),
                        "heart": issue.reactions.get("heart", 0),
                        "rocket": issue.reactions.get("rocket", 0),
                        "eyes": issue.reactions.get("eyes", 0),
                    }
                except Exception:
                    reactions = {"total": 0}

                issue_info = {
                    "number": issue.number,
                    "title": issue.title or "",
                    "body": issue.body or "",
                    "state": issue.state,
                    "labels": labels,
                    "assignees": assignees,
                    "author": issue.user.login if issue.user else "unknown",
                    "created_at": issue.created_at.isoformat() if issue.created_at else None,
                    "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
                    "comments": getattr(issue, 'comments', 0),
                    "url": issue.html_url,
                    "reactions": reactions,
                }
            except Exception as e:
                self.logger.warning(f"Error processing issue {getattr(issue, 'number', 'unknown')}: {e}")
                continue
            
            issue_data.append(issue_info)
            count += 1
        
        return issue_data

    async def get_issues(self, repo_name: str, state: str = "open", limit: int = 100) -> List[Dict[str, Any]]:
        """Get issues from repository (wrapper for get_open_issues)."""
        if state == "open":
            return await self.get_open_issues(repo_name, limit=limit)
        else:
            # For non-open states, we'll use the same logic but with different state
            repo = await self.get_repository(repo_name)
            issues = await self._make_request(repo.get_issues, state=state)

            issue_data = []
            count = 0

            for issue in issues:
                if count >= limit:
                    break

                # Skip pull requests
                if issue.pull_request:
                    continue

                try:
                    issue_info = {
                        "number": issue.number,
                        "title": issue.title or "",
                        "body": issue.body or "",
                        "state": issue.state,
                        "labels": [label.name for label in issue.labels] if issue.labels else [],
                        "author": issue.user.login if issue.user else "unknown",
                        "created_at": issue.created_at.isoformat() if issue.created_at else None,
                        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
                        "url": issue.html_url,
                    }
                    issue_data.append(issue_info)
                    count += 1
                except Exception as e:
                    self.logger.warning(f"Error processing issue {getattr(issue, 'number', 'unknown')}: {e}")
                    continue

            return issue_data

    async def get_pull_requests(self, repo_name: str, state: str = "open", limit: int = 100) -> List[Dict[str, Any]]:
        """Get pull requests from repository."""
        repo = await self.get_repository(repo_name)
        
        pulls = await self._make_request(
            repo.get_pulls,
            state=state
        )
        
        pr_data = []
        count = 0
        
        for pr in pulls:
            if count >= limit:
                break
            
            pr_info = {
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "author": pr.user.login,
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat(),
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                "closed_at": pr.closed_at.isoformat() if pr.closed_at else None,
                "merge_commit_sha": pr.merge_commit_sha,
                "head": {
                    "ref": pr.head.ref,
                    "sha": pr.head.sha,
                },
                "base": {
                    "ref": pr.base.ref,
                    "sha": pr.base.sha,
                },
                "mergeable": pr.mergeable,
                "merged": pr.merged,
                "comments": pr.comments,
                "review_comments": pr.review_comments,
                "commits": pr.commits,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files,
                "url": pr.html_url,
            }
            
            pr_data.append(pr_info)
            count += 1
        
        return pr_data
    
    async def get_contributors(self, repo_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get repository contributors."""
        repo = await self.get_repository(repo_name)
        
        contributors = await self._make_request(repo.get_contributors)
        
        contributor_data = []
        count = 0
        
        for contributor in contributors:
            if count >= limit:
                break
            
            contributor_info = {
                "login": contributor.login,
                "contributions": contributor.contributions,
                "type": contributor.type,
                "url": contributor.html_url,
            }
            
            contributor_data.append(contributor_info)
            count += 1
        
        return contributor_data
    
    async def search_code(self, query: str, repo_name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Search code in repository or globally."""
        if repo_name:
            search_query = f"{query} repo:{repo_name}"
        else:
            search_query = query
        
        results = await self._make_request(
            self.github.search_code,
            search_query
        )
        
        code_data = []
        count = 0
        
        for result in results:
            if count >= limit:
                break
            
            code_info = {
                "name": result.name,
                "path": result.path,
                "sha": result.sha,
                "url": result.html_url,
                "repository": result.repository.full_name,
                "score": result.score,
            }
            
            code_data.append(code_info)
            count += 1
        
        return code_data
    
    async def get_maintainer_patterns(self, repo_name: str) -> Dict[str, Any]:
        """Analyze maintainer patterns and preferences."""
        repo = await self.get_repository(repo_name)

        # Get recent PRs to analyze maintainer behavior
        recent_prs = await self.get_pull_requests(repo_name, state="closed", limit=200)

        # Analyze patterns
        maintainer_stats = {}
        response_times = []
        acceptance_patterns = {
            "total_prs": len(recent_prs),
            "merged_prs": 0,
            "closed_without_merge": 0,
            "common_rejection_reasons": [],
        }

        for pr in recent_prs:
            if pr["merged"]:
                acceptance_patterns["merged_prs"] += 1

                # Calculate response time if available
                if pr["created_at"] and pr["merged_at"]:
                    created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
                    merged = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
                    response_time = (merged - created).total_seconds() / 3600  # hours
                    response_times.append(response_time)
            else:
                acceptance_patterns["closed_without_merge"] += 1

        # Calculate acceptance rate
        if acceptance_patterns["total_prs"] > 0:
            acceptance_patterns["acceptance_rate"] = (
                acceptance_patterns["merged_prs"] / acceptance_patterns["total_prs"]
            )
        else:
            acceptance_patterns["acceptance_rate"] = 0.0

        # Calculate average response time
        if response_times:
            acceptance_patterns["avg_response_time_hours"] = sum(response_times) / len(response_times)
            acceptance_patterns["median_response_time_hours"] = sorted(response_times)[len(response_times) // 2]

        return {
            "maintainer_stats": maintainer_stats,
            "acceptance_patterns": acceptance_patterns,
            "response_times": response_times[:50],  # Sample of response times
        }

    async def get_contribution_guidelines(self, repo_name: str) -> Dict[str, Any]:
        """Get contribution guidelines and coding standards."""
        repo = await self.get_repository(repo_name)

        guidelines = {}

        # Try to get common guideline files
        guideline_files = [
            "CONTRIBUTING.md",
            "CONTRIBUTING",
            ".github/CONTRIBUTING.md",
            "docs/CONTRIBUTING.md",
            "CODING_STANDARDS.md",
            "CODE_OF_CONDUCT.md",
            "STYLE_GUIDE.md",
        ]

        for filename in guideline_files:
            try:
                content = await self._make_request(repo.get_contents, filename)
                if hasattr(content, 'decoded_content'):
                    guidelines[filename] = {
                        "content": content.decoded_content.decode('utf-8'),
                        "size": content.size,
                        "last_modified": content.last_modified,
                    }
            except GithubException:
                # File doesn't exist, continue
                continue

        return guidelines

    async def analyze_code_patterns(self, repo_name: str, file_extensions: List[str] = None) -> Dict[str, Any]:
        """Analyze code patterns and structure in repository."""
        if file_extensions is None:
            file_extensions = [".cpp", ".h", ".py", ".js", ".ts"]

        patterns = {
            "file_structure": {},
            "language_distribution": {},
            "common_patterns": [],
            "complexity_indicators": {},
        }

        # Get repository contents
        repo = await self.get_repository(repo_name)

        try:
            # Get language statistics
            languages = await self._make_request(repo.get_languages)
            total_bytes = sum(languages.values())

            for language, bytes_count in languages.items():
                patterns["language_distribution"][language] = {
                    "bytes": bytes_count,
                    "percentage": (bytes_count / total_bytes) * 100 if total_bytes > 0 else 0
                }

            # Analyze file structure (limited to avoid rate limits)
            contents = await self._make_request(repo.get_contents, "")
            patterns["file_structure"] = await self._analyze_directory_structure(contents, repo, max_depth=2)

        except GithubException as e:
            self.logger.warning(f"Could not analyze code patterns: {e}")

        return patterns

    async def _analyze_directory_structure(self, contents, repo, current_depth=0, max_depth=2) -> Dict[str, Any]:
        """Recursively analyze directory structure."""
        if current_depth >= max_depth:
            return {}

        structure = {}

        for content in contents:
            if content.type == "dir":
                try:
                    subcontents = await self._make_request(repo.get_contents, content.path)
                    structure[content.name] = {
                        "type": "directory",
                        "contents": await self._analyze_directory_structure(
                            subcontents, repo, current_depth + 1, max_depth
                        )
                    }
                except GithubException:
                    structure[content.name] = {"type": "directory", "contents": {}}
            else:
                structure[content.name] = {
                    "type": "file",
                    "size": content.size,
                    "extension": content.name.split(".")[-1] if "." in content.name else None
                }

        return structure

    async def get_issue_templates(self, repo_name: str) -> Dict[str, Any]:
        """Get issue and PR templates."""
        repo = await self.get_repository(repo_name)

        templates = {}
        template_paths = [
            ".github/ISSUE_TEMPLATE",
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/issue_template.md",
            ".github/pull_request_template.md",
            "ISSUE_TEMPLATE.md",
            "PULL_REQUEST_TEMPLATE.md",
        ]

        for path in template_paths:
            try:
                content = await self._make_request(repo.get_contents, path)
                if hasattr(content, 'decoded_content'):
                    templates[path] = {
                        "content": content.decoded_content.decode('utf-8'),
                        "size": content.size,
                    }
                elif isinstance(content, list):
                    # Directory with multiple templates
                    templates[path] = {}
                    for template_file in content:
                        if template_file.type == "file":
                            file_content = await self._make_request(repo.get_contents, template_file.path)
                            templates[path][template_file.name] = {
                                "content": file_content.decoded_content.decode('utf-8'),
                                "size": file_content.size,
                            }
            except GithubException:
                continue

        return templates

    async def close(self) -> None:
        """Close the GitHub client."""
        # PyGithub doesn't require explicit closing, but we can clear caches
        self._repo_cache.clear()
        self.logger.info("GitHub client closed")
