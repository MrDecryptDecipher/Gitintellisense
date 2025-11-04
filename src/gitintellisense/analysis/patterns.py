"""
Pattern analysis module for GitHub repository intelligence.

This module provides sophisticated pattern recognition capabilities for analyzing
repository development patterns, maintainer behavior, and contribution trends.
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import defaultdict, Counter
import statistics

import pandas as pd
import numpy as np

from ..core.github_client import GitHubClient
from ..utils.config import Config, get_config
from ..utils.logging import get_logger


class PatternAnalyzer:
    """
    Advanced pattern analysis engine for repository intelligence.
    
    Analyzes historical patterns in commits, issues, PRs, and maintainer behavior
    to identify trends and predict optimal contribution strategies.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize pattern analyzer."""
        self.config = config or get_config()
        self.logger = get_logger("pattern_analyzer")
        self.github_client = GitHubClient(config)
    
    async def analyze_commit_patterns(self, repo_name: str, months_back: int = 12) -> Dict[str, Any]:
        """
        Analyze commit patterns over time to identify development rhythms.
        
        Args:
            repo_name: Repository name in format "owner/repo"
            months_back: Number of months to analyze
        
        Returns:
            Comprehensive commit pattern analysis
        """
        self.logger.info(f"Analyzing commit patterns for {repo_name}")
        
        # Get commits for the specified period
        since_date = datetime.now() - timedelta(days=months_back * 30)
        commits = await self.github_client.get_recent_commits(
            repo_name, 
            since=since_date, 
            limit=self.config.analysis.max_commits_to_analyze
        )
        
        if not commits:
            return {"error": "No commits found for analysis"}
        
        # Convert to DataFrame for easier analysis
        commit_data = []
        for commit in commits:
            try:
                commit_time = datetime.fromisoformat(commit["author"]["date"].replace("Z", "+00:00"))
                commit_data.append({
                    "sha": commit["sha"],
                    "message": commit["message"],
                    "author": commit["author"]["name"],
                    "author_email": commit["author"]["email"],
                    "date": commit_time,
                    "additions": commit["stats"]["additions"],
                    "deletions": commit["stats"]["deletions"],
                    "files_changed": commit["files_changed"],
                })
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Skipping commit due to parsing error: {e}")
                continue
        
        if not commit_data:
            return {"error": "No valid commits found for analysis"}
        
        df = pd.DataFrame(commit_data)
        
        # Perform various pattern analyses
        patterns = {
            "temporal_patterns": self._analyze_temporal_commit_patterns(df),
            "author_patterns": self._analyze_author_commit_patterns(df),
            "message_patterns": self._analyze_commit_message_patterns(df),
            "size_patterns": self._analyze_commit_size_patterns(df),
            "frequency_patterns": self._analyze_commit_frequency_patterns(df),
            "collaboration_patterns": self._analyze_collaboration_patterns(df),
        }
        
        return patterns
    
    def _analyze_temporal_commit_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze temporal patterns in commits."""
        df["hour"] = df["date"].dt.hour
        df["day_of_week"] = df["date"].dt.dayofweek  # 0=Monday, 6=Sunday
        df["month"] = df["date"].dt.month
        df["week"] = df["date"].dt.isocalendar().week
        
        # Hour patterns
        hourly_commits = df.groupby("hour").size()
        peak_hours = hourly_commits.nlargest(3).index.tolist()
        
        # Day of week patterns
        daily_commits = df.groupby("day_of_week").size()
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        daily_pattern = {weekday_names[i]: daily_commits.get(i, 0) for i in range(7)}
        
        # Weekly patterns
        weekly_commits = df.groupby("week").size()
        
        # Monthly patterns
        monthly_commits = df.groupby("month").size()
        
        return {
            "peak_hours": peak_hours,
            "hourly_distribution": hourly_commits.to_dict(),
            "daily_pattern": daily_pattern,
            "weekend_vs_weekday": {
                "weekday_commits": daily_commits[0:5].sum(),
                "weekend_commits": daily_commits[5:7].sum(),
                "weekend_percentage": (daily_commits[5:7].sum() / len(df)) * 100,
            },
            "weekly_trend": {
                "avg_commits_per_week": weekly_commits.mean(),
                "most_active_weeks": weekly_commits.nlargest(5).to_dict(),
                "least_active_weeks": weekly_commits.nsmallest(5).to_dict(),
            },
            "monthly_trend": monthly_commits.to_dict(),
        }
    
    def _analyze_author_commit_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze author-specific commit patterns."""
        author_stats = df.groupby("author").agg({
            "sha": "count",
            "additions": ["sum", "mean"],
            "deletions": ["sum", "mean"],
            "files_changed": ["sum", "mean"],
            "date": ["min", "max"],
        }).round(2)
        
        # Flatten column names
        author_stats.columns = ["_".join(col).strip() for col in author_stats.columns]
        
        # Calculate author activity patterns
        author_patterns = {}
        for author in df["author"].unique():
            author_commits = df[df["author"] == author]
            
            # Time patterns for this author
            author_hours = author_commits["hour"].value_counts()
            author_days = author_commits["day_of_week"].value_counts()
            
            # Commit size patterns
            avg_additions = author_commits["additions"].mean()
            avg_deletions = author_commits["deletions"].mean()
            avg_files = author_commits["files_changed"].mean()
            
            # Activity span
            first_commit = author_commits["date"].min()
            last_commit = author_commits["date"].max()
            activity_span = (last_commit - first_commit).days
            
            author_patterns[author] = {
                "total_commits": len(author_commits),
                "avg_additions": round(avg_additions, 2),
                "avg_deletions": round(avg_deletions, 2),
                "avg_files_changed": round(avg_files, 2),
                "preferred_hours": author_hours.head(3).to_dict(),
                "preferred_days": author_days.head(3).to_dict(),
                "activity_span_days": activity_span,
                "commits_per_day": round(len(author_commits) / max(1, activity_span), 3),
                "first_commit": first_commit.isoformat(),
                "last_commit": last_commit.isoformat(),
            }
        
        # Top contributors
        top_contributors = df["author"].value_counts().head(10).to_dict()
        
        # Contribution distribution analysis
        commit_counts = df["author"].value_counts().values
        gini_coefficient = self._calculate_gini_coefficient(commit_counts)
        
        return {
            "total_unique_authors": len(df["author"].unique()),
            "top_contributors": top_contributors,
            "author_details": author_patterns,
            "contribution_distribution": {
                "gini_coefficient": gini_coefficient,
                "top_10_percentage": sum(list(top_contributors.values())) / len(df) * 100,
            },
        }
    
    def _analyze_commit_message_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze commit message patterns and conventions."""
        messages = df["message"].tolist()
        
        # Message length analysis
        message_lengths = [len(msg) for msg in messages]
        
        # Common prefixes (conventional commits)
        prefixes = []
        conventional_pattern = re.compile(r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build)(\(.+\))?:")
        
        for msg in messages:
            match = conventional_pattern.match(msg.lower())
            if match:
                prefixes.append(match.group(1))
            else:
                # Look for other common patterns
                first_word = msg.split()[0] if msg.split() else ""
                if first_word.endswith(":"):
                    prefixes.append(first_word[:-1].lower())
        
        # Analyze message structure
        multiline_messages = sum(1 for msg in messages if "\n" in msg)
        
        # Common keywords
        all_words = " ".join(messages).lower().split()
        word_freq = Counter(all_words)
        common_words = word_freq.most_common(20)
        
        # Issue/PR references
        issue_refs = sum(1 for msg in messages if re.search(r"#\d+", msg))
        
        return {
            "message_length": {
                "avg_length": statistics.mean(message_lengths),
                "median_length": statistics.median(message_lengths),
                "min_length": min(message_lengths),
                "max_length": max(message_lengths),
            },
            "conventional_commits": {
                "total_conventional": len(prefixes),
                "percentage_conventional": (len(prefixes) / len(messages)) * 100,
                "common_types": Counter(prefixes).most_common(10),
            },
            "structure_analysis": {
                "multiline_percentage": (multiline_messages / len(messages)) * 100,
                "avg_lines": sum(msg.count("\n") + 1 for msg in messages) / len(messages),
            },
            "content_analysis": {
                "common_words": common_words,
                "issue_references": issue_refs,
                "issue_ref_percentage": (issue_refs / len(messages)) * 100,
            },
        }
    
    def _analyze_commit_size_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze commit size patterns."""
        # Calculate total changes per commit
        df["total_changes"] = df["additions"] + df["deletions"]
        
        # Size categories
        def categorize_size(changes):
            if changes < 10:
                return "tiny"
            elif changes < 50:
                return "small"
            elif changes < 200:
                return "medium"
            elif changes < 1000:
                return "large"
            else:
                return "huge"
        
        df["size_category"] = df["total_changes"].apply(categorize_size)
        size_distribution = df["size_category"].value_counts().to_dict()
        
        # Statistical analysis
        additions_stats = df["additions"].describe().to_dict()
        deletions_stats = df["deletions"].describe().to_dict()
        files_stats = df["files_changed"].describe().to_dict()
        
        return {
            "size_distribution": size_distribution,
            "additions_statistics": additions_stats,
            "deletions_statistics": deletions_stats,
            "files_changed_statistics": files_stats,
            "large_commits": {
                "count": len(df[df["total_changes"] > 1000]),
                "percentage": (len(df[df["total_changes"] > 1000]) / len(df)) * 100,
            },
        }
    
    def _analyze_commit_frequency_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze commit frequency patterns over time."""
        # Daily commit counts
        df["date_only"] = df["date"].dt.date
        daily_commits = df.groupby("date_only").size()
        
        # Weekly patterns
        df["week_start"] = df["date"].dt.to_period("W").dt.start_time
        weekly_commits = df.groupby("week_start").size()
        
        # Monthly patterns
        df["month_start"] = df["date"].dt.to_period("M").dt.start_time
        monthly_commits = df.groupby("month_start").size()
        
        # Identify trends
        if len(weekly_commits) > 4:
            # Simple trend analysis using linear regression
            x = np.arange(len(weekly_commits))
            y = weekly_commits.values
            trend_slope = np.polyfit(x, y, 1)[0]
            
            if trend_slope > 0.1:
                trend = "increasing"
            elif trend_slope < -0.1:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "daily_frequency": {
                "avg_commits_per_day": daily_commits.mean(),
                "max_commits_per_day": daily_commits.max(),
                "days_with_commits": len(daily_commits),
                "days_without_commits": len(pd.date_range(df["date"].min(), df["date"].max())) - len(daily_commits),
            },
            "weekly_frequency": {
                "avg_commits_per_week": weekly_commits.mean(),
                "trend": trend,
                "most_active_week": weekly_commits.idxmax().strftime("%Y-%m-%d") if len(weekly_commits) > 0 else None,
            },
            "monthly_frequency": {
                "avg_commits_per_month": monthly_commits.mean(),
                "most_active_month": monthly_commits.idxmax().strftime("%Y-%m") if len(monthly_commits) > 0 else None,
            },
        }
    
    def _analyze_collaboration_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze collaboration patterns between authors."""
        # Co-authorship analysis (simplified)
        # In a real implementation, this would analyze co-authored commits
        
        # Time-based collaboration
        df["date_only"] = df["date"].dt.date
        daily_authors = df.groupby("date_only")["author"].nunique()
        
        # Author overlap analysis
        author_pairs = {}
        dates_with_multiple_authors = daily_authors[daily_authors > 1].index
        
        for date in dates_with_multiple_authors:
            day_commits = df[df["date_only"] == date]
            authors = day_commits["author"].unique()
            
            for i, author1 in enumerate(authors):
                for author2 in authors[i+1:]:
                    pair = tuple(sorted([author1, author2]))
                    author_pairs[pair] = author_pairs.get(pair, 0) + 1
        
        return {
            "collaboration_frequency": {
                "days_with_multiple_authors": len(dates_with_multiple_authors),
                "avg_authors_per_active_day": daily_authors.mean(),
                "max_authors_per_day": daily_authors.max(),
            },
            "author_pairs": dict(sorted(author_pairs.items(), key=lambda x: x[1], reverse=True)[:10]),
            "collaboration_score": len(dates_with_multiple_authors) / len(daily_authors) * 100,
        }
    
    def _calculate_gini_coefficient(self, values: List[int]) -> float:
        """Calculate Gini coefficient for distribution analysis."""
        if not values or len(values) < 2:
            return 0.0
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        cumsum = sum((i + 1) * val for i, val in enumerate(sorted_values))
        return (2 * cumsum) / (n * sum(sorted_values)) - (n + 1) / n

    async def analyze_maintainer_patterns(self, repo_name: str) -> Dict[str, Any]:
        """
        Analyze maintainer behavior patterns and preferences.

        Args:
            repo_name: Repository name in format "owner/repo"

        Returns:
            Comprehensive maintainer pattern analysis
        """
        self.logger.info(f"Analyzing maintainer patterns for {repo_name}")

        # Get recent PRs for analysis
        recent_prs = await self.github_client.get_pull_requests(
            repo_name,
            state="all",
            limit=500
        )

        if not recent_prs:
            return {"error": "No pull requests found for analysis"}

        # Analyze PR patterns
        pr_patterns = self._analyze_pr_review_patterns(recent_prs)

        # Analyze response patterns
        response_patterns = self._analyze_maintainer_response_patterns(recent_prs)

        # Analyze acceptance patterns
        acceptance_patterns = self._analyze_pr_acceptance_patterns(recent_prs)

        # Analyze communication patterns
        communication_patterns = await self._analyze_communication_patterns(repo_name, recent_prs)

        return {
            "pr_review_patterns": pr_patterns,
            "response_patterns": response_patterns,
            "acceptance_patterns": acceptance_patterns,
            "communication_patterns": communication_patterns,
            "maintainer_preferences": self._infer_maintainer_preferences(recent_prs),
        }

    def _analyze_pr_review_patterns(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze PR review patterns."""
        if not prs:
            return {}

        # Convert to DataFrame
        pr_data = []
        for pr in prs:
            try:
                created_time = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
                merged_time = None
                closed_time = None

                if pr.get("merged_at"):
                    merged_time = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
                if pr.get("closed_at"):
                    closed_time = datetime.fromisoformat(pr["closed_at"].replace("Z", "+00:00"))

                pr_data.append({
                    "number": pr["number"],
                    "state": pr["state"],
                    "merged": pr.get("merged", False),
                    "created_at": created_time,
                    "merged_at": merged_time,
                    "closed_at": closed_time,
                    "additions": pr.get("additions", 0),
                    "deletions": pr.get("deletions", 0),
                    "changed_files": pr.get("changed_files", 0),
                    "comments": pr.get("comments", 0),
                    "review_comments": pr.get("review_comments", 0),
                    "commits": pr.get("commits", 0),
                    "author": pr.get("author", "unknown"),
                })
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Skipping PR due to parsing error: {e}")
                continue

        if not pr_data:
            return {"error": "No valid PRs found for analysis"}

        df = pd.DataFrame(pr_data)

        # Analyze review time patterns
        merged_prs = df[df["merged"] == True].copy()
        if len(merged_prs) > 0:
            merged_prs["review_time_hours"] = (
                merged_prs["merged_at"] - merged_prs["created_at"]
            ).dt.total_seconds() / 3600

            review_time_stats = merged_prs["review_time_hours"].describe().to_dict()
        else:
            review_time_stats = {}

        # Analyze PR size preferences
        size_acceptance = {}
        for size_category in ["small", "medium", "large"]:
            if size_category == "small":
                size_prs = df[df["changed_files"] <= 5]
            elif size_category == "medium":
                size_prs = df[(df["changed_files"] > 5) & (df["changed_files"] <= 20)]
            else:
                size_prs = df[df["changed_files"] > 20]

            if len(size_prs) > 0:
                acceptance_rate = len(size_prs[size_prs["merged"] == True]) / len(size_prs) * 100
                size_acceptance[size_category] = {
                    "total_prs": len(size_prs),
                    "acceptance_rate": acceptance_rate,
                }

        return {
            "total_prs_analyzed": len(df),
            "review_time_statistics": review_time_stats,
            "size_preferences": size_acceptance,
            "merge_rate": len(merged_prs) / len(df) * 100 if len(df) > 0 else 0,
            "avg_review_comments": df["review_comments"].mean(),
            "avg_discussion_comments": df["comments"].mean(),
        }

    def _analyze_maintainer_response_patterns(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze maintainer response time patterns."""
        # This would require additional API calls to get PR timeline events
        # For now, we'll provide a simplified analysis based on available data

        response_patterns = {
            "avg_first_response_time": "Not available (requires timeline data)",
            "response_time_by_day": "Not available (requires timeline data)",
            "response_time_by_pr_size": "Not available (requires timeline data)",
        }

        # Analyze based on available timestamps
        closed_prs = [pr for pr in prs if pr.get("closed_at")]

        if closed_prs:
            response_times = []
            for pr in closed_prs:
                try:
                    created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
                    closed = datetime.fromisoformat(pr["closed_at"].replace("Z", "+00:00"))
                    response_time = (closed - created).total_seconds() / 3600  # hours
                    response_times.append(response_time)
                except ValueError:
                    continue

            if response_times:
                response_patterns.update({
                    "avg_response_time_hours": statistics.mean(response_times),
                    "median_response_time_hours": statistics.median(response_times),
                    "fast_responses": len([t for t in response_times if t < 24]),
                    "slow_responses": len([t for t in response_times if t > 168]),  # 1 week
                })

        return response_patterns

    def _analyze_pr_acceptance_patterns(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze PR acceptance patterns."""
        if not prs:
            return {}

        total_prs = len(prs)
        merged_prs = len([pr for pr in prs if pr.get("merged", False)])
        closed_without_merge = len([pr for pr in prs if pr["state"] == "closed" and not pr.get("merged", False)])

        # Analyze acceptance by author type (new vs returning contributors)
        author_pr_counts = Counter(pr.get("author", "unknown") for pr in prs)

        new_contributor_prs = []
        returning_contributor_prs = []

        for pr in prs:
            author = pr.get("author", "unknown")
            if author_pr_counts[author] == 1:
                new_contributor_prs.append(pr)
            else:
                returning_contributor_prs.append(pr)

        new_contributor_acceptance = 0
        if new_contributor_prs:
            new_contributor_acceptance = len([pr for pr in new_contributor_prs if pr.get("merged", False)]) / len(new_contributor_prs) * 100

        returning_contributor_acceptance = 0
        if returning_contributor_prs:
            returning_contributor_acceptance = len([pr for pr in returning_contributor_prs if pr.get("merged", False)]) / len(returning_contributor_prs) * 100

        return {
            "overall_acceptance_rate": (merged_prs / total_prs * 100) if total_prs > 0 else 0,
            "total_prs": total_prs,
            "merged_prs": merged_prs,
            "closed_without_merge": closed_without_merge,
            "new_contributor_acceptance_rate": new_contributor_acceptance,
            "returning_contributor_acceptance_rate": returning_contributor_acceptance,
            "acceptance_by_size": self._analyze_acceptance_by_size(prs),
        }

    def _analyze_acceptance_by_size(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze acceptance rates by PR size."""
        size_categories = {
            "tiny": [],
            "small": [],
            "medium": [],
            "large": [],
            "huge": [],
        }

        for pr in prs:
            additions = pr.get("additions", 0)
            deletions = pr.get("deletions", 0)
            total_changes = additions + deletions

            if total_changes < 10:
                category = "tiny"
            elif total_changes < 50:
                category = "small"
            elif total_changes < 200:
                category = "medium"
            elif total_changes < 1000:
                category = "large"
            else:
                category = "huge"

            size_categories[category].append(pr)

        acceptance_by_size = {}
        for category, category_prs in size_categories.items():
            if category_prs:
                merged_count = len([pr for pr in category_prs if pr.get("merged", False)])
                acceptance_rate = (merged_count / len(category_prs)) * 100
                acceptance_by_size[category] = {
                    "total_prs": len(category_prs),
                    "merged_prs": merged_count,
                    "acceptance_rate": acceptance_rate,
                }

        return acceptance_by_size

    async def _analyze_communication_patterns(self, repo_name: str, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze communication patterns in PRs and issues."""
        # This would require additional API calls to get PR comments and reviews
        # For now, we'll provide a simplified analysis

        communication_stats = {
            "avg_comments_per_pr": statistics.mean([pr.get("comments", 0) for pr in prs]) if prs else 0,
            "avg_review_comments_per_pr": statistics.mean([pr.get("review_comments", 0) for pr in prs]) if prs else 0,
            "highly_discussed_prs": len([pr for pr in prs if pr.get("comments", 0) + pr.get("review_comments", 0) > 10]),
        }

        return communication_stats

    def _infer_maintainer_preferences(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Infer maintainer preferences from PR patterns."""
        if not prs:
            return {}

        merged_prs = [pr for pr in prs if pr.get("merged", False)]

        if not merged_prs:
            return {"error": "No merged PRs to analyze preferences"}

        # Analyze preferred PR characteristics
        merged_sizes = [pr.get("changed_files", 0) for pr in merged_prs]
        merged_additions = [pr.get("additions", 0) for pr in merged_prs]
        merged_commits = [pr.get("commits", 0) for pr in merged_prs]

        preferences = {
            "preferred_pr_size": {
                "avg_files_changed": statistics.mean(merged_sizes),
                "median_files_changed": statistics.median(merged_sizes),
                "max_files_changed": max(merged_sizes) if merged_sizes else 0,
            },
            "preferred_change_size": {
                "avg_additions": statistics.mean(merged_additions),
                "median_additions": statistics.median(merged_additions),
            },
            "preferred_commit_count": {
                "avg_commits": statistics.mean(merged_commits),
                "median_commits": statistics.median(merged_commits),
            },
            "quality_indicators": {
                "accepts_large_prs": len([s for s in merged_sizes if s > 20]) > 0,
                "prefers_small_prs": statistics.median(merged_sizes) <= 5,
                "accepts_multi_commit": statistics.median(merged_commits) > 1,
            },
        }

        return preferences
