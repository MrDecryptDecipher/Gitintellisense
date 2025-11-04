"""
Validation pipeline for generated contributions.

This module provides comprehensive validation capabilities for generated
pull requests and contributions before submission.
"""

import ast
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..utils.config import Config, get_config
from ..utils.logging import get_logger


class ValidationPipeline:
    """
    Comprehensive validation pipeline for contribution quality assurance.

    Validates code quality, syntax, style, security, and compliance
    before submitting contributions.
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize validation pipeline."""
        self.config = config or get_config()
        self.logger = get_logger("validation_pipeline")

        # Validation rules
        self.validation_rules = {
            "syntax": True,
            "style": True,
            "security": True,
            "complexity": True,
            "documentation": True,
            "testing": True,
        }

    def validate_contribution(self, contribution: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a complete contribution before submission."""
        self.logger.info("Validating contribution")

        validation_results = {
            "valid": True,
            "score": 0.0,
            "checks": {},
            "warnings": [],
            "errors": [],
            "suggestions": [],
        }

        try:
            # Validate PR metadata
            metadata_result = self._validate_pr_metadata(contribution)
            validation_results["checks"]["metadata"] = metadata_result

            # Validate changes if present
            if "changes" in contribution:
                changes_result = self._validate_changes(contribution["changes"])
                validation_results["checks"]["changes"] = changes_result

            # Calculate overall score and validity
            validation_results = self._calculate_validation_score(validation_results)

            return validation_results

        except Exception as e:
            self.logger.error("Validation failed", error=str(e))
            return {
                "valid": False,
                "error": str(e),
                "score": 0.0,
                "checks": {},
                "warnings": [],
                "errors": [str(e)],
                "suggestions": [],
            }

    def validate_changes(
        self,
        local_path: str,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate applied changes in a local repository."""
        self.logger.info(f"Validating {len(changes)} changes in {local_path}")

        validation_results = {
            "valid": True,
            "checks": {},
            "warnings": [],
            "errors": [],
            "suggestions": [],
        }

        try:
            repo_path = Path(local_path)

            # Syntax validation
            syntax_result = self._validate_syntax(repo_path, changes)
            validation_results["checks"]["syntax"] = syntax_result

            # Style validation
            style_result = self._validate_style(repo_path, changes)
            validation_results["checks"]["style"] = style_result

            # Security validation
            security_result = self._validate_security(repo_path, changes)
            validation_results["checks"]["security"] = security_result

            # Complexity validation
            complexity_result = self._validate_complexity(repo_path, changes)
            validation_results["checks"]["complexity"] = complexity_result

            # Collect all errors and warnings
            for check_name, check_result in validation_results["checks"].items():
                validation_results["warnings"].extend(check_result.get("warnings", []))
                validation_results["errors"].extend(check_result.get("errors", []))
                validation_results["suggestions"].extend(check_result.get("suggestions", []))

            # Determine overall validity
            validation_results["valid"] = len(validation_results["errors"]) == 0

            return validation_results

        except Exception as e:
            self.logger.error("Changes validation failed", error=str(e))
            return {
                "valid": False,
                "error": str(e),
                "checks": {},
                "warnings": [],
                "errors": [str(e)],
                "suggestions": [],
            }

    def _validate_pr_metadata(self, contribution: Dict[str, Any]) -> Dict[str, Any]:
        """Validate PR metadata (title, description, etc.)."""
        result = {
            "passed": True,
            "warnings": [],
            "errors": [],
            "suggestions": [],
        }

        # Validate PR title
        pr_title = contribution.get("pr_title", "")
        if not pr_title:
            result["errors"].append("PR title is missing")
            result["passed"] = False
        elif len(pr_title) < 10:
            result["warnings"].append("PR title is very short")
        elif len(pr_title) > 72:
            result["warnings"].append("PR title exceeds recommended length (72 chars)")

        # Validate PR description
        pr_description = contribution.get("pr_description", "")
        if not pr_description:
            result["warnings"].append("PR description is missing")
        elif len(pr_description) < 50:
            result["warnings"].append("PR description is very short")

        # Validate commit message
        commit_message = contribution.get("commit_message", "")
        if not commit_message:
            result["errors"].append("Commit message is missing")
            result["passed"] = False
        elif not self._is_conventional_commit(commit_message):
            result["suggestions"].append("Consider using conventional commit format")

        # Validate branch name
        branch_name = contribution.get("branch_name", "")
        if not branch_name:
            result["errors"].append("Branch name is missing")
            result["passed"] = False
        elif not self._is_valid_branch_name(branch_name):
            result["warnings"].append("Branch name doesn't follow conventions")

        return result

    def _validate_changes(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate the changes themselves."""
        result = {
            "passed": True,
            "warnings": [],
            "errors": [],
            "suggestions": [],
        }

        if not changes:
            result["errors"].append("No changes provided")
            result["passed"] = False
            return result

        # Validate each change
        for i, change in enumerate(changes):
            change_result = self._validate_single_change(change, i)
            result["warnings"].extend(change_result["warnings"])
            result["errors"].extend(change_result["errors"])
            result["suggestions"].extend(change_result["suggestions"])

            if not change_result["passed"]:
                result["passed"] = False

        return result

    def _validate_single_change(self, change: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Validate a single change."""
        result = {
            "passed": True,
            "warnings": [],
            "errors": [],
            "suggestions": [],
        }

        # Validate change structure
        required_fields = ["type", "file_path"]
        for field in required_fields:
            if field not in change:
                result["errors"].append(f"Change {index}: Missing required field '{field}'")
                result["passed"] = False

        # Validate change type
        valid_types = ["create", "modify", "delete"]
        change_type = change.get("type", "")
        if change_type not in valid_types:
            result["errors"].append(f"Change {index}: Invalid change type '{change_type}'")
            result["passed"] = False

        # Validate file path
        file_path = change.get("file_path", "")
        if not file_path:
            result["errors"].append(f"Change {index}: Empty file path")
            result["passed"] = False
        elif file_path.startswith("/"):
            result["warnings"].append(f"Change {index}: Absolute file path used")

        # Validate content for create/modify operations
        if change_type in ["create", "modify"]:
            content = change.get("content", "")
            if not content:
                result["warnings"].append(f"Change {index}: Empty content for {change_type} operation")

        return result

    def _validate_syntax(
        self,
        repo_path: Path,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate syntax of changed files."""
        result = {
            "passed": True,
            "warnings": [],
            "errors": [],
            "suggestions": [],
        }

        for change in changes:
            if change.get("type") in ["create", "modify"]:
                file_path = repo_path / change.get("file_path", "")

                if file_path.exists():
                    syntax_check = self._check_file_syntax(file_path)
                    if not syntax_check["valid"]:
                        result["errors"].extend(syntax_check["errors"])
                        result["passed"] = False
                    result["warnings"].extend(syntax_check["warnings"])

        return result

    def _validate_style(
        self,
        repo_path: Path,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate code style of changed files."""
        result = {
            "passed": True,
            "warnings": [],
            "errors": [],
            "suggestions": [],
        }

        for change in changes:
            if change.get("type") in ["create", "modify"]:
                file_path = repo_path / change.get("file_path", "")

                if file_path.exists():
                    style_check = self._check_file_style(file_path)
                    result["warnings"].extend(style_check["warnings"])
                    result["suggestions"].extend(style_check["suggestions"])

        return result

    def _validate_security(
        self,
        repo_path: Path,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate security aspects of changed files."""
        result = {
            "passed": True,
            "warnings": [],
            "errors": [],
            "suggestions": [],
        }

        for change in changes:
            if change.get("type") in ["create", "modify"]:
                file_path = repo_path / change.get("file_path", "")

                if file_path.exists():
                    security_check = self._check_file_security(file_path)
                    result["warnings"].extend(security_check["warnings"])
                    result["errors"].extend(security_check["errors"])

                    if security_check["errors"]:
                        result["passed"] = False

        return result

    def _validate_complexity(
        self,
        repo_path: Path,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate code complexity of changed files."""
        result = {
            "passed": True,
            "warnings": [],
            "errors": [],
            "suggestions": [],
        }

        for change in changes:
            if change.get("type") in ["create", "modify"]:
                file_path = repo_path / change.get("file_path", "")

                if file_path.exists():
                    complexity_check = self._check_file_complexity(file_path)
                    result["warnings"].extend(complexity_check["warnings"])
                    result["suggestions"].extend(complexity_check["suggestions"])

        return result

    def _check_file_syntax(self, file_path: Path) -> Dict[str, Any]:
        """Check syntax of a single file."""
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }

        try:
            if file_path.suffix == ".py":
                # Python syntax check
                content = file_path.read_text(encoding="utf-8")
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    result["valid"] = False
                    result["errors"].append(f"Python syntax error in {file_path}: {e}")

            elif file_path.suffix in [".js", ".ts"]:
                # JavaScript/TypeScript syntax check (basic)
                content = file_path.read_text(encoding="utf-8")
                if "function(" in content and content.count("(") != content.count(")"):
                    result["warnings"].append(f"Possible parentheses mismatch in {file_path}")

            elif file_path.suffix in [".cpp", ".c", ".h"]:
                # C/C++ basic syntax check
                content = file_path.read_text(encoding="utf-8")
                if content.count("{") != content.count("}"):
                    result["warnings"].append(f"Possible brace mismatch in {file_path}")

        except Exception as e:
            result["warnings"].append(f"Could not check syntax for {file_path}: {e}")

        return result

    def _check_file_style(self, file_path: Path) -> Dict[str, Any]:
        """Check code style of a single file."""
        result = {
            "warnings": [],
            "suggestions": [],
        }

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            # Check line length
            for i, line in enumerate(lines, 1):
                if len(line) > 120:
                    result["warnings"].append(f"{file_path}:{i}: Line too long ({len(line)} > 120)")

            # Check for trailing whitespace
            for i, line in enumerate(lines, 1):
                if line.rstrip() != line:
                    result["suggestions"].append(f"{file_path}:{i}: Trailing whitespace")

            # Check for mixed tabs and spaces
            has_tabs = any("\t" in line for line in lines)
            has_spaces = any(line.startswith("    ") for line in lines)
            if has_tabs and has_spaces:
                result["warnings"].append(f"{file_path}: Mixed tabs and spaces")

            # Language-specific style checks
            if file_path.suffix == ".py":
                self._check_python_style(file_path, content, result)
            elif file_path.suffix in [".cpp", ".c", ".h"]:
                self._check_cpp_style(file_path, content, result)

        except Exception as e:
            result["warnings"].append(f"Could not check style for {file_path}: {e}")

        return result

    def _check_file_security(self, file_path: Path) -> Dict[str, Any]:
        """Check security aspects of a single file."""
        result = {
            "errors": [],
            "warnings": [],
        }

        try:
            content = file_path.read_text(encoding="utf-8")

            # Check for common security issues
            security_patterns = [
                (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password detected"),
                (r"api_key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key detected"),
                (r"secret\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret detected"),
                (r"eval\s*\(", "Use of eval() function (security risk)"),
                (r"exec\s*\(", "Use of exec() function (security risk)"),
                (r"system\s*\(", "Use of system() function (security risk)"),
                (r"shell=True", "Shell execution enabled (security risk)"),
            ]

            import re
            for pattern, message in security_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    result["warnings"].append(f"{file_path}: {message}")

            # Check for SQL injection patterns
            sql_patterns = [
                r"SELECT\s+.*\+.*",
                r"INSERT\s+.*\+.*",
                r"UPDATE\s+.*\+.*",
                r"DELETE\s+.*\+.*",
            ]

            for pattern in sql_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    result["warnings"].append(f"{file_path}: Possible SQL injection vulnerability")
                    break

        except Exception as e:
            result["warnings"].append(f"Could not check security for {file_path}: {e}")

        return result

    def _check_file_complexity(self, file_path: Path) -> Dict[str, Any]:
        """Check code complexity of a single file."""
        result = {
            "warnings": [],
            "suggestions": [],
        }

        try:
            if file_path.suffix == ".py":
                content = file_path.read_text(encoding="utf-8")

                # Simple complexity metrics
                lines = content.split("\n")
                non_empty_lines = [line for line in lines if line.strip()]

                if len(non_empty_lines) > 500:
                    result["warnings"].append(f"{file_path}: File is very large ({len(non_empty_lines)} lines)")

                # Count nested levels
                max_indent = 0
                for line in lines:
                    if line.strip():
                        indent = len(line) - len(line.lstrip())
                        max_indent = max(max_indent, indent // 4)  # Assuming 4-space indentation

                if max_indent > 6:
                    result["warnings"].append(f"{file_path}: High nesting level ({max_indent})")

                # Count functions
                function_count = content.count("def ")
                if function_count > 20:
                    result["suggestions"].append(f"{file_path}: Many functions ({function_count}), consider splitting")

        except Exception as e:
            result["warnings"].append(f"Could not check complexity for {file_path}: {e}")

        return result

    def _check_python_style(self, file_path: Path, content: str, result: Dict[str, Any]) -> None:
        """Check Python-specific style issues."""
        lines = content.split("\n")

        # Check for PEP 8 violations
        for i, line in enumerate(lines, 1):
            # Check for space after comma
            if "," in line and ",," not in line:
                import re
                if re.search(r",[^\s]", line):
                    result["suggestions"].append(f"{file_path}:{i}: Missing space after comma")

            # Check for space around operators
            if "=" in line and not any(op in line for op in ["==", "!=", "<=", ">="]):
                if re.search(r"[^\s]=|=[^\s]", line):
                    result["suggestions"].append(f"{file_path}:{i}: Missing space around assignment operator")

    def _check_cpp_style(self, file_path: Path, content: str, result: Dict[str, Any]) -> None:
        """Check C++-specific style issues."""
        lines = content.split("\n")

        # Check for common C++ style issues
        for i, line in enumerate(lines, 1):
            # Check for missing spaces around operators
            import re
            if re.search(r"[a-zA-Z0-9]\+[a-zA-Z0-9]", line):
                result["suggestions"].append(f"{file_path}:{i}: Consider adding spaces around + operator")

            # Check for pointer/reference style
            if re.search(r"\*[a-zA-Z]", line):
                result["suggestions"].append(f"{file_path}:{i}: Consider space after * in pointer declaration")

    def _is_conventional_commit(self, commit_message: str) -> bool:
        """Check if commit message follows conventional commit format."""
        import re
        pattern = r"^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .+"
        return bool(re.match(pattern, commit_message))

    def _is_valid_branch_name(self, branch_name: str) -> bool:
        """Check if branch name follows conventions."""
        import re
        # Allow alphanumeric, hyphens, underscores, and forward slashes
        pattern = r"^[a-zA-Z0-9\-_/]+$"
        return bool(re.match(pattern, branch_name)) and len(branch_name) <= 50

    def _calculate_validation_score(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall validation score."""
        total_checks = len(validation_results["checks"])
        if total_checks == 0:
            validation_results["score"] = 0.0
            validation_results["valid"] = False
            return validation_results

        passed_checks = sum(1 for check in validation_results["checks"].values() if check.get("passed", True))
        base_score = (passed_checks / total_checks) * 100

        # Deduct points for warnings and errors
        warning_penalty = len(validation_results["warnings"]) * 2
        error_penalty = len(validation_results["errors"]) * 10

        final_score = max(0, base_score - warning_penalty - error_penalty)
        validation_results["score"] = round(final_score, 1)

        # Set validity based on errors and critical warnings
        critical_errors = len(validation_results["errors"])
        validation_results["valid"] = critical_errors == 0 and final_score >= 70

        return validation_results
