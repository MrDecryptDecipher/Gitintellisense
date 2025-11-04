"""
Template engine for generating contribution content.

This module provides template-based content generation for
pull requests, issues, and other contribution materials.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils.config import Config, get_config
from ..utils.logging import get_logger


class TemplateEngine:
    """
    Professional template engine for contribution content generation.

    Generates high-quality PR descriptions, commit messages, and other
    contribution materials using proven templates and best practices.
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize template engine."""
        self.config = config or get_config()
        self.logger = get_logger("template_engine")

        # Load templates
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """Load contribution templates."""
        return {
            "pr_descriptions": {
                "bug_fix": """## Description
{description}

## Changes Made
{changes_summary}

## Testing
{testing_info}

## Checklist
- [x] Code follows project style guidelines
- [x] Self-review of code completed
- [x] Code is commented where necessary
- [x] Changes generate no new warnings
- [x] Tests added/updated as needed
- [x] All tests pass locally

## Related Issues
{related_issues}

## Additional Notes
{additional_notes}""",

                "feature": """## Description
{description}

## Motivation and Context
{motivation}

## Changes Made
{changes_summary}

## Testing
{testing_info}

## Screenshots (if applicable)
{screenshots}

## Checklist
- [x] Code follows project style guidelines
- [x] Self-review of code completed
- [x] Code is commented where necessary
- [x] Documentation updated as needed
- [x] Changes generate no new warnings
- [x] Tests added for new functionality
- [x] All tests pass locally

## Breaking Changes
{breaking_changes}

## Additional Notes
{additional_notes}""",

                "documentation": """## Description
{description}

## Changes Made
{changes_summary}

## Motivation
{motivation}

## Checklist
- [x] Documentation is clear and accurate
- [x] Examples are working and tested
- [x] Links are valid and accessible
- [x] Formatting follows project standards
- [x] Content is up-to-date with current codebase

## Additional Notes
{additional_notes}""",

                "testing": """## Description
{description}

## Test Coverage Added
{test_coverage}

## Changes Made
{changes_summary}

## Testing Approach
{testing_approach}

## Checklist
- [x] Tests cover new functionality
- [x] Tests cover edge cases
- [x] All tests pass locally
- [x] Test names are descriptive
- [x] Tests are maintainable and readable

## Additional Notes
{additional_notes}"""
            },

            "commit_messages": {
                "bug_fix": "fix: {summary}\n\n{description}\n\nFixes #{issue_number}",
                "feature": "feat: {summary}\n\n{description}",
                "documentation": "docs: {summary}\n\n{description}",
                "testing": "test: {summary}\n\n{description}",
                "refactor": "refactor: {summary}\n\n{description}",
                "style": "style: {summary}\n\n{description}",
                "chore": "chore: {summary}\n\n{description}"
            },

            "branch_names": {
                "bug_fix": "fix/issue-{issue_number}-{slug}",
                "feature": "feat/{slug}",
                "documentation": "docs/{slug}",
                "testing": "test/{slug}",
                "refactor": "refactor/{slug}",
                "style": "style/{slug}",
                "chore": "chore/{slug}"
            }
        }

    def generate_pr_description(
        self,
        opportunity: Dict[str, Any],
        solution_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate professional PR description from opportunity."""
        self.logger.info("Generating PR description", opportunity_type=opportunity.get("type"))

        opportunity_type = opportunity.get("type", "bug_fix")
        template = self.templates["pr_descriptions"].get(opportunity_type,
                                                        self.templates["pr_descriptions"]["bug_fix"])

        # Prepare template variables
        variables = {
            "description": opportunity.get("description", "No description provided"),
            "changes_summary": self._generate_changes_summary(solution_data),
            "testing_info": self._generate_testing_info(solution_data),
            "related_issues": self._generate_related_issues(opportunity),
            "additional_notes": self._generate_additional_notes(opportunity, solution_data),
            "motivation": opportunity.get("description", "Improving code quality"),
            "screenshots": "N/A",
            "breaking_changes": "None",
            "test_coverage": self._generate_test_coverage_info(solution_data),
            "testing_approach": solution_data.get("testing_approach", "Manual testing") if solution_data else "Manual testing"
        }

        return self._fill_template(template, variables)

    def generate_commit_message(
        self,
        opportunity: Dict[str, Any],
        solution_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate conventional commit message."""
        self.logger.info("Generating commit message", opportunity_type=opportunity.get("type"))

        opportunity_type = opportunity.get("type", "bug_fix")
        template = self.templates["commit_messages"].get(opportunity_type,
                                                        self.templates["commit_messages"]["bug_fix"])

        # Generate summary
        title = opportunity.get("title", "Fix issue")
        summary = self._generate_commit_summary(title)

        variables = {
            "summary": summary,
            "description": opportunity.get("description", "")[:200],  # Limit description length
            "issue_number": opportunity.get("issue_number", "")
        }

        return self._fill_template(template, variables)

    def generate_branch_name(
        self,
        opportunity: Dict[str, Any]
    ) -> str:
        """Generate branch name following conventions."""
        self.logger.info("Generating branch name", opportunity_type=opportunity.get("type"))

        opportunity_type = opportunity.get("type", "bug_fix")
        template = self.templates["branch_names"].get(opportunity_type,
                                                     self.templates["branch_names"]["bug_fix"])

        # Generate slug from title
        title = opportunity.get("title", "fix-issue")
        slug = self._generate_slug(title)

        variables = {
            "issue_number": opportunity.get("issue_number", ""),
            "slug": slug
        }

        branch_name = self._fill_template(template, variables)

        # Clean up branch name
        branch_name = re.sub(r'[^a-zA-Z0-9\-_/]', '-', branch_name)
        branch_name = re.sub(r'-+', '-', branch_name)
        branch_name = branch_name.strip('-')

        return branch_name[:50]  # Limit length

    def generate_pr_metadata(
        self,
        opportunity: Dict[str, Any],
        solution_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate complete PR metadata."""
        return {
            "pr_title": self._generate_pr_title(opportunity),
            "pr_description": self.generate_pr_description(opportunity, solution_data),
            "commit_message": self.generate_commit_message(opportunity, solution_data),
            "branch_name": self.generate_branch_name(opportunity),
            "labels": self._generate_labels(opportunity),
            "assignees": [],
            "reviewers": [],
        }

    def _generate_pr_title(self, opportunity: Dict[str, Any]) -> str:
        """Generate PR title."""
        title = opportunity.get("title", "Fix issue")

        # Add type prefix if not present
        opportunity_type = opportunity.get("type", "fix")
        type_prefixes = {
            "bug_fix": "Fix:",
            "feature": "Add:",
            "documentation": "Docs:",
            "testing": "Test:",
            "refactor": "Refactor:",
            "style": "Style:",
            "chore": "Chore:"
        }

        prefix = type_prefixes.get(opportunity_type, "Fix:")

        if not any(title.lower().startswith(p.lower()) for p in type_prefixes.values()):
            title = f"{prefix} {title}"

        return title[:72]  # GitHub's recommended limit

    def _generate_changes_summary(self, solution_data: Optional[Dict[str, Any]]) -> str:
        """Generate summary of changes made."""
        if not solution_data or "changes" not in solution_data:
            return "- Code improvements and bug fixes"

        changes = solution_data["changes"]
        summary_lines = []

        for change in changes[:5]:  # Limit to 5 changes
            change_type = change.get("type", "modify")
            file_path = change.get("file_path", "unknown")
            description = change.get("description", f"{change_type} {file_path}")

            summary_lines.append(f"- {description}")

        if len(changes) > 5:
            summary_lines.append(f"- ... and {len(changes) - 5} more changes")

        return "\n".join(summary_lines)

    def _generate_testing_info(self, solution_data: Optional[Dict[str, Any]]) -> str:
        """Generate testing information."""
        if solution_data and "testing_approach" in solution_data:
            return solution_data["testing_approach"]

        return """- [x] Manual testing completed
- [x] All existing tests pass
- [x] Code review completed"""

    def _generate_related_issues(self, opportunity: Dict[str, Any]) -> str:
        """Generate related issues section."""
        issue_number = opportunity.get("issue_number")
        if issue_number:
            return f"Closes #{issue_number}"
        return "N/A"

    def _generate_additional_notes(
        self,
        opportunity: Dict[str, Any],
        solution_data: Optional[Dict[str, Any]]
    ) -> str:
        """Generate additional notes."""
        notes = []

        if solution_data and "implementation_notes" in solution_data:
            notes.append(solution_data["implementation_notes"])

        complexity = opportunity.get("complexity", "")
        if complexity:
            notes.append(f"Complexity: {complexity}")

        skills = opportunity.get("skills_required", [])
        if skills:
            notes.append(f"Skills involved: {', '.join(skills)}")

        return "\n".join(notes) if notes else "None"

    def _generate_test_coverage_info(self, solution_data: Optional[Dict[str, Any]]) -> str:
        """Generate test coverage information."""
        if solution_data and "testing_approach" in solution_data:
            return solution_data["testing_approach"]

        return "- Unit tests for core functionality\n- Integration tests for API endpoints\n- Edge case testing"

    def _generate_commit_summary(self, title: str) -> str:
        """Generate concise commit summary."""
        # Remove common prefixes and clean up
        title = re.sub(r'^(fix|add|update|improve|remove|refactor):\s*', '', title, flags=re.IGNORECASE)
        title = title.strip()

        # Limit length and ensure it starts with lowercase
        summary = title[:50].strip()
        if summary:
            summary = summary[0].lower() + summary[1:]

        return summary or "improve code quality"

    def _generate_slug(self, text: str) -> str:
        """Generate URL-friendly slug from text."""
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')

        return slug[:30]  # Limit length

    def _generate_labels(self, opportunity: Dict[str, Any]) -> List[str]:
        """Generate appropriate labels for the PR."""
        labels = []

        opportunity_type = opportunity.get("type", "")
        type_labels = {
            "bug_fix": ["bug", "fix"],
            "feature": ["enhancement", "feature"],
            "documentation": ["documentation"],
            "testing": ["testing"],
            "refactor": ["refactor"],
            "style": ["style"],
            "chore": ["chore"]
        }

        labels.extend(type_labels.get(opportunity_type, []))

        complexity = opportunity.get("complexity", "")
        if complexity == "low":
            labels.append("good first issue")
        elif complexity == "high":
            labels.append("complex")

        return labels

    def _fill_template(self, template: str, variables: Dict[str, Any]) -> str:
        """Fill template with variables."""
        try:
            return template.format(**variables)
        except KeyError as e:
            self.logger.warning(f"Missing template variable: {e}")
            # Fill missing variables with placeholder
            for key in re.findall(r'\{(\w+)\}', template):
                if key not in variables:
                    variables[key] = f"[{key}]"
            return template.format(**variables)
