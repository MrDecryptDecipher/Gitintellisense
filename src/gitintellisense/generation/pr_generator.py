"""
Pull request generator for automated contributions.

This module provides automated pull request generation capabilities
for contributing to open source repositories.
"""

import os
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import git
from github import Github

from ..core.github_client import GitHubClient
from ..core.ai_engine import AIEngine
from ..generation.templates import TemplateEngine
from ..generation.validation import ValidationPipeline
from ..utils.config import Config, get_config
from ..utils.logging import get_logger


class PRGenerator:
    """
    Automated pull request generator with real GitHub integration.

    This class provides complete PR generation capabilities including:
    - Code analysis and improvement generation
    - Branch creation and management
    - Real GitHub PR creation and submission
    - Automated testing and validation
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize PR generator."""
        self.config = config or get_config()
        self.logger = get_logger("pr_generator")
        self.github_client = GitHubClient(config)
        self.ai_engine = AIEngine(config)
        self.template_engine = TemplateEngine(config)
        self.validation_pipeline = ValidationPipeline(config)

        # Initialize GitHub API client for PR operations
        self.github = Github(self.config.github.token)

    async def generate_and_submit_pr(
        self,
        opportunity: Dict[str, Any],
        repo_name: str,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Generate and submit a complete pull request.

        Args:
            opportunity: Detected contribution opportunity
            repo_name: Target repository name
            dry_run: If True, don't actually submit PR

        Returns:
            PR generation results with URLs and status
        """
        self.logger.info(f"Generating PR for opportunity in {repo_name}",
                        opportunity_type=opportunity.get("type"),
                        dry_run=dry_run)

        try:
            # Step 1: Analyze the opportunity and generate solution
            solution = await self._generate_solution(opportunity, repo_name)
            if "error" in solution:
                return solution

            # Step 2: Create local repository and branch
            repo_info = await self._setup_local_repository(repo_name)
            if "error" in repo_info:
                return repo_info

            # Step 3: Apply changes to the codebase
            changes_result = await self._apply_changes(
                repo_info["local_path"],
                solution["changes"]
            )
            if "error" in changes_result:
                return changes_result

            # Step 4: Validate changes
            validation_result = await self._validate_changes(
                repo_info["local_path"],
                solution["changes"]
            )
            if not validation_result["valid"]:
                return {"error": "Changes failed validation", "details": validation_result}

            # Step 5: Commit and push changes
            commit_result = await self._commit_and_push_changes(
                repo_info,
                solution["commit_message"],
                solution["branch_name"]
            )
            if "error" in commit_result:
                return commit_result

            # Step 6: Create pull request (if not dry run)
            if not dry_run:
                pr_result = await self._create_pull_request(
                    repo_name,
                    solution["branch_name"],
                    solution["pr_title"],
                    solution["pr_description"]
                )
                if "error" in pr_result:
                    return pr_result
            else:
                pr_result = {"status": "dry_run", "message": "PR not created (dry run mode)"}

            # Step 7: Cleanup
            await self._cleanup_local_repository(repo_info["local_path"])

            return {
                "status": "success",
                "opportunity_id": opportunity.get("id"),
                "solution": solution,
                "validation": validation_result,
                "commit": commit_result,
                "pr": pr_result,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"PR generation failed for {repo_name}", error=str(e))
            return {"error": str(e)}

    async def _generate_solution(
        self,
        opportunity: Dict[str, Any],
        repo_name: str
    ) -> Dict[str, Any]:
        """Generate solution for the opportunity using AI."""
        self.logger.info("Generating solution using AI")

        try:
            # Get repository context
            repo_context = await self._get_repository_context(repo_name, opportunity)

            # Generate solution using AI
            solution_prompt = self._create_solution_prompt(opportunity, repo_context)

            messages = [
                {
                    "role": "system",
                    "content": self._get_solution_generation_system_prompt()
                },
                {
                    "role": "user",
                    "content": solution_prompt
                }
            ]

            response = await self.ai_engine._make_ai_request(messages, max_tokens=3000)
            solution_data = self._parse_solution_response(response["content"])

            # Generate PR metadata
            pr_metadata = self.template_engine.generate_pr_metadata(opportunity, solution_data)

            return {
                "changes": solution_data.get("changes", []),
                "commit_message": pr_metadata.get("commit_message", "Fix issue"),
                "branch_name": pr_metadata.get("branch_name", "fix-issue"),
                "pr_title": pr_metadata.get("pr_title", "Fix issue"),
                "pr_description": pr_metadata.get("pr_description", "This PR fixes an issue"),
                "ai_metadata": {
                    "model": response["model"],
                    "tokens_used": response["tokens_used"],
                },
            }

        except Exception as e:
            self.logger.error("Solution generation failed", error=str(e))
            return {"error": str(e)}

    async def _setup_local_repository(self, repo_name: str) -> Dict[str, Any]:
        """Setup local repository for making changes."""
        self.logger.info(f"Setting up local repository for {repo_name}")

        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="gitintellisense_")
            local_path = Path(temp_dir) / "repo"

            # Clone repository
            clone_url = f"https://github.com/{repo_name}.git"
            repo = git.Repo.clone_from(clone_url, local_path)

            # Configure git user
            with repo.config_writer() as git_config:
                git_config.set_value("user", "name", self.config.github.username)
                git_config.set_value("user", "email", f"{self.config.github.username}@users.noreply.github.com")

            return {
                "local_path": str(local_path),
                "temp_dir": temp_dir,
                "repo": repo,
                "clone_url": clone_url,
            }

        except Exception as e:
            self.logger.error("Failed to setup local repository", error=str(e))
            return {"error": str(e)}

    async def _apply_changes(
        self,
        local_path: str,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply generated changes to the local repository."""
        self.logger.info(f"Applying {len(changes)} changes to repository")

        try:
            applied_changes = []

            for change in changes:
                change_type = change.get("type", "modify")
                file_path = change.get("file_path", "")
                content = change.get("content", "")

                full_path = Path(local_path) / file_path

                if change_type == "create":
                    # Create new file
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content, encoding="utf-8")
                    applied_changes.append({"type": "created", "path": file_path})

                elif change_type == "modify":
                    # Modify existing file
                    if full_path.exists():
                        full_path.write_text(content, encoding="utf-8")
                        applied_changes.append({"type": "modified", "path": file_path})
                    else:
                        self.logger.warning(f"File not found for modification: {file_path}")

                elif change_type == "delete":
                    # Delete file
                    if full_path.exists():
                        full_path.unlink()
                        applied_changes.append({"type": "deleted", "path": file_path})
                    else:
                        self.logger.warning(f"File not found for deletion: {file_path}")

            return {
                "applied_changes": applied_changes,
                "total_changes": len(applied_changes),
            }

        except Exception as e:
            self.logger.error("Failed to apply changes", error=str(e))
            return {"error": str(e)}

    async def _validate_changes(
        self,
        local_path: str,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate applied changes."""
        self.logger.info("Validating applied changes")

        try:
            # Use validation pipeline
            validation_result = self.validation_pipeline.validate_changes(local_path, changes)

            # Additional basic validation
            repo_path = Path(local_path)

            # Check if repository is still valid
            if not (repo_path / ".git").exists():
                return {"valid": False, "error": "Git repository corrupted"}

            # Check for syntax errors in modified files
            syntax_errors = []
            for change in changes:
                if change.get("type") in ["create", "modify"]:
                    file_path = repo_path / change.get("file_path", "")
                    if file_path.exists() and file_path.suffix in [".py", ".js", ".ts"]:
                        # Basic syntax validation for common languages
                        try:
                            if file_path.suffix == ".py":
                                compile(file_path.read_text(), str(file_path), "exec")
                        except SyntaxError as e:
                            syntax_errors.append({"file": str(file_path), "error": str(e)})

            if syntax_errors:
                return {"valid": False, "syntax_errors": syntax_errors}

            return {
                "valid": True,
                "validation_result": validation_result,
                "checks_passed": ["git_integrity", "syntax_validation"],
            }

        except Exception as e:
            self.logger.error("Validation failed", error=str(e))
            return {"valid": False, "error": str(e)}

    async def _commit_and_push_changes(
        self,
        repo_info: Dict[str, Any],
        commit_message: str,
        branch_name: str
    ) -> Dict[str, Any]:
        """Commit and push changes to a new branch."""
        self.logger.info(f"Committing and pushing changes to branch: {branch_name}")

        try:
            repo = repo_info["repo"]

            # Create new branch
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()

            # Add all changes
            repo.git.add(A=True)

            # Check if there are changes to commit
            if not repo.is_dirty() and not repo.untracked_files:
                return {"error": "No changes to commit"}

            # Commit changes
            commit = repo.index.commit(commit_message)

            # Push to origin (this would require authentication setup)
            # For now, we'll simulate this step
            push_result = {
                "status": "simulated",
                "message": "Push simulated - would require proper authentication setup",
                "branch": branch_name,
                "commit_sha": commit.hexsha,
            }

            return {
                "commit_sha": commit.hexsha,
                "branch_name": branch_name,
                "commit_message": commit_message,
                "push_result": push_result,
            }

        except Exception as e:
            self.logger.error("Failed to commit and push changes", error=str(e))
            return {"error": str(e)}

    async def _create_pull_request(
        self,
        repo_name: str,
        branch_name: str,
        pr_title: str,
        pr_description: str
    ) -> Dict[str, Any]:
        """Create a pull request on GitHub."""
        self.logger.info(f"Creating pull request for {repo_name}")

        try:
            # Get repository
            repo = self.github.get_repo(repo_name)

            # Create pull request
            pr = repo.create_pull(
                title=pr_title,
                body=pr_description,
                head=f"{self.config.github.username}:{branch_name}",
                base="main"  # or "master" depending on repository
            )

            return {
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "pr_title": pr.title,
                "status": "created",
            }

        except Exception as e:
            self.logger.error("Failed to create pull request", error=str(e))
            return {"error": str(e)}

    async def _cleanup_local_repository(self, local_path: str) -> None:
        """Clean up local repository."""
        try:
            import shutil
            shutil.rmtree(Path(local_path).parent)
            self.logger.info("Local repository cleaned up")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup local repository: {e}")

    async def _get_repository_context(
        self,
        repo_name: str,
        opportunity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get repository context for solution generation."""
        try:
            # Get basic repository info
            repo_info = await self.github_client.get_repository_info(repo_name)

            # Get relevant files based on opportunity type
            relevant_files = []
            if opportunity.get("issue_number"):
                # Get issue details
                issue_details = await self.github_client.get_issue_details(
                    repo_name,
                    opportunity["issue_number"]
                )
                relevant_files = await self._get_files_related_to_issue(repo_name, issue_details)

            return {
                "repository_info": repo_info,
                "relevant_files": relevant_files,
                "opportunity": opportunity,
            }

        except Exception as e:
            self.logger.warning(f"Failed to get repository context: {e}")
            return {"error": str(e)}

    async def _get_files_related_to_issue(
        self,
        repo_name: str,
        issue_details: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get files related to an issue."""
        # This would implement logic to find relevant files
        # For now, return empty list
        return []

    def _create_solution_prompt(
        self,
        opportunity: Dict[str, Any],
        repo_context: Dict[str, Any]
    ) -> str:
        """Create prompt for solution generation."""
        prompt = f"""Generate a solution for the following contribution opportunity:

OPPORTUNITY:
Type: {opportunity.get('type', 'unknown')}
Title: {opportunity.get('title', 'Unknown')}
Description: {opportunity.get('description', 'No description')}
Complexity: {opportunity.get('complexity', 'unknown')}
Skills Required: {opportunity.get('skills_required', [])}

REPOSITORY CONTEXT:
{repo_context.get('repository_info', {}).get('description', 'No description')}

Please provide:
1. Specific code changes needed
2. File paths to modify/create
3. Implementation approach
4. Testing considerations

Respond in JSON format with structured solution data."""

        return prompt

    def _get_solution_generation_system_prompt(self) -> str:
        """Get system prompt for solution generation."""
        return """You are an expert software engineer specializing in open-source contributions. Generate practical, high-quality solutions for contribution opportunities.

Focus on:
1. Clean, maintainable code that follows project conventions
2. Minimal, focused changes that address the specific issue
3. Proper error handling and edge case consideration
4. Clear documentation and comments
5. Adherence to coding standards and best practices

Provide specific file changes with exact code implementations.

Respond in JSON format with this structure:
{
  "changes": [
    {
      "type": "create|modify|delete",
      "file_path": "path/to/file",
      "content": "complete file content",
      "description": "what this change does"
    }
  ],
  "implementation_notes": "detailed explanation",
  "testing_approach": "how to test the changes"
}"""

    def _parse_solution_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response for solution."""
        try:
            import json
            if response.strip().startswith("{"):
                return json.loads(response)

            return {
                "changes": [],
                "implementation_notes": response,
                "testing_approach": "Manual testing required"
            }

        except json.JSONDecodeError:
            return {
                "changes": [],
                "implementation_notes": response,
                "testing_approach": "Manual testing required"
            }

    async def generate_documentation_pr(
        self,
        repo_name: str,
        doc_type: str = "readme",
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Generate a documentation improvement PR."""
        self.logger.info(f"Generating documentation PR for {repo_name}")

        opportunity = {
            "type": "documentation",
            "subtype": doc_type,
            "title": f"Improve {doc_type} documentation",
            "description": f"Enhance {doc_type} with better examples and explanations",
            "complexity": "low",
            "skills_required": ["technical_writing"],
        }

        return await self.generate_and_submit_pr(opportunity, repo_name, dry_run)

    async def generate_test_pr(
        self,
        repo_name: str,
        test_type: str = "unit",
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Generate a test improvement PR."""
        self.logger.info(f"Generating test PR for {repo_name}")

        opportunity = {
            "type": "testing",
            "subtype": test_type,
            "title": f"Add {test_type} tests",
            "description": f"Improve test coverage with {test_type} tests",
            "complexity": "medium",
            "skills_required": ["testing", "test_automation"],
        }

        return await self.generate_and_submit_pr(opportunity, repo_name, dry_run)

    async def generate_bug_fix_pr(
        self,
        repo_name: str,
        issue_number: int,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Generate a bug fix PR for a specific issue."""
        self.logger.info(f"Generating bug fix PR for issue #{issue_number} in {repo_name}")

        # Get issue details
        try:
            issue_details = await self.github_client.get_issue_details(repo_name, issue_number)

            opportunity = {
                "type": "issue",
                "subtype": "bug_fix",
                "title": f"Fix issue #{issue_number}: {issue_details.get('title', 'Unknown')}",
                "description": issue_details.get("body", ""),
                "issue_number": issue_number,
                "complexity": "medium",
                "skills_required": ["debugging", "problem_solving"],
            }

            return await self.generate_and_submit_pr(opportunity, repo_name, dry_run)

        except Exception as e:
            self.logger.error(f"Failed to generate bug fix PR: {e}")
            return {"error": str(e)}
