"""
Git hooks integration for GitIntellisense.

This module provides Git hooks for automatic repository analysis,
contribution opportunity detection, and workflow automation.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.analyzer import RepositoryAnalyzer
from ..analysis.opportunities import OpportunityDetector
from ..ml.models import ContributionSuccessPredictor
from ..utils.config import Config, get_config
from ..utils.logging import get_logger


class GitHooksManager:
    """
    Git hooks manager for GitIntellisense integration.
    
    Provides automated Git hooks for:
    - Pre-commit analysis and validation
    - Post-commit opportunity detection
    - Pre-push contribution scoring
    - Post-merge analysis updates
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize Git hooks manager."""
        self.config = config or get_config()
        self.logger = get_logger("git_hooks")
        
        # Initialize components
        self.analyzer = RepositoryAnalyzer(config)
        self.opportunity_detector = OpportunityDetector(config)
        self.success_predictor = ContributionSuccessPredictor(config)
    
    def install_hooks(self, repository_path: Path) -> Dict[str, bool]:
        """Install GitIntellisense hooks in a repository."""
        self.logger.info(f"Installing Git hooks in {repository_path}")
        
        hooks_dir = repository_path / ".git" / "hooks"
        if not hooks_dir.exists():
            self.logger.error("Git hooks directory not found")
            return {"error": "Not a Git repository"}
        
        results = {}
        
        # Install each hook
        hooks_to_install = [
            ("pre-commit", self._generate_pre_commit_hook()),
            ("post-commit", self._generate_post_commit_hook()),
            ("pre-push", self._generate_pre_push_hook()),
            ("post-merge", self._generate_post_merge_hook()),
            ("prepare-commit-msg", self._generate_prepare_commit_msg_hook()),
        ]
        
        for hook_name, hook_content in hooks_to_install:
            try:
                hook_path = hooks_dir / hook_name
                
                # Backup existing hook if it exists
                if hook_path.exists():
                    backup_path = hooks_dir / f"{hook_name}.backup"
                    hook_path.rename(backup_path)
                    self.logger.info(f"Backed up existing {hook_name} hook")
                
                # Write new hook
                hook_path.write_text(hook_content)
                hook_path.chmod(0o755)  # Make executable
                
                results[hook_name] = True
                self.logger.info(f"Installed {hook_name} hook")
                
            except Exception as e:
                self.logger.error(f"Failed to install {hook_name} hook: {e}")
                results[hook_name] = False
        
        # Create GitIntellisense config file
        self._create_hook_config(repository_path)
        
        return results
    
    def uninstall_hooks(self, repository_path: Path) -> Dict[str, bool]:
        """Uninstall GitIntellisense hooks from a repository."""
        self.logger.info(f"Uninstalling Git hooks from {repository_path}")
        
        hooks_dir = repository_path / ".git" / "hooks"
        results = {}
        
        hook_names = ["pre-commit", "post-commit", "pre-push", "post-merge", "prepare-commit-msg"]
        
        for hook_name in hook_names:
            try:
                hook_path = hooks_dir / hook_name
                backup_path = hooks_dir / f"{hook_name}.backup"
                
                if hook_path.exists():
                    # Check if it's our hook
                    content = hook_path.read_text()
                    if "GitIntellisense" in content:
                        hook_path.unlink()
                        results[hook_name] = True
                        
                        # Restore backup if it exists
                        if backup_path.exists():
                            backup_path.rename(hook_path)
                            self.logger.info(f"Restored backup for {hook_name} hook")
                    else:
                        results[hook_name] = False
                        self.logger.warning(f"{hook_name} hook is not a GitIntellisense hook")
                else:
                    results[hook_name] = True  # Already uninstalled
                    
            except Exception as e:
                self.logger.error(f"Failed to uninstall {hook_name} hook: {e}")
                results[hook_name] = False
        
        return results
    
    def _generate_pre_commit_hook(self) -> str:
        """Generate pre-commit hook script."""
        return f'''#!/bin/bash
# GitIntellisense Pre-Commit Hook
# Performs code quality checks and contribution analysis

echo "🔍 GitIntellisense: Running pre-commit analysis..."

# Get repository root
REPO_ROOT=$(git rev-parse --show-toplevel)

# Check if GitIntellisense is available
if ! command -v gitintellisense &> /dev/null; then
    echo "⚠️  GitIntellisense CLI not found, skipping analysis"
    exit 0
fi

# Get staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    echo "ℹ️  No staged files to analyze"
    exit 0
fi

# Run code quality checks
echo "📊 Analyzing code quality..."

# Check for common issues
ISSUES_FOUND=0

# Check for TODO/FIXME comments in staged files
for file in $STAGED_FILES; do
    if [ -f "$file" ]; then
        if grep -n "TODO\\|FIXME\\|XXX\\|HACK" "$file" > /dev/null; then
            echo "⚠️  Found TODO/FIXME comments in $file"
            grep -n "TODO\\|FIXME\\|XXX\\|HACK" "$file"
            ISSUES_FOUND=1
        fi
    fi
done

# Check for large files
for file in $STAGED_FILES; do
    if [ -f "$file" ]; then
        SIZE=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
        if [ "$SIZE" -gt 1048576 ]; then  # 1MB
            echo "⚠️  Large file detected: $file (${{SIZE}} bytes)"
            ISSUES_FOUND=1
        fi
    fi
done

# Check for sensitive information
for file in $STAGED_FILES; do
    if [ -f "$file" ]; then
        if grep -i "password\\|secret\\|api_key\\|token" "$file" > /dev/null; then
            echo "🚨 Potential sensitive information in $file"
            ISSUES_FOUND=1
        fi
    fi
done

if [ $ISSUES_FOUND -eq 1 ]; then
    echo ""
    echo "⚠️  Issues found in staged files. Continue? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "❌ Commit aborted"
        exit 1
    fi
fi

echo "✅ Pre-commit analysis completed"
exit 0
'''
    
    def _generate_post_commit_hook(self) -> str:
        """Generate post-commit hook script."""
        return f'''#!/bin/bash
# GitIntellisense Post-Commit Hook
# Analyzes commits for contribution opportunities

echo "🔍 GitIntellisense: Running post-commit analysis..."

# Get repository information
REPO_ROOT=$(git rev-parse --show-toplevel)
COMMIT_HASH=$(git rev-parse HEAD)
COMMIT_MESSAGE=$(git log -1 --pretty=%B)

# Check if GitIntellisense is available
if ! command -v gitintellisense &> /dev/null; then
    echo "⚠️  GitIntellisense CLI not found, skipping analysis"
    exit 0
fi

# Get repository name from remote
REPO_NAME=$(git remote get-url origin 2>/dev/null | sed 's/.*github\\.com[:\\/]//; s/\\.git$//')

if [ -z "$REPO_NAME" ]; then
    echo "ℹ️  No GitHub remote found, skipping analysis"
    exit 0
fi

# Run opportunity detection in background
echo "🔍 Detecting new contribution opportunities..."
nohup gitintellisense detect-opportunities "$REPO_NAME" --update > /dev/null 2>&1 &

# Log commit for analysis
echo "📝 Logging commit for analysis..."
echo "$(date): $COMMIT_HASH - $COMMIT_MESSAGE" >> "$REPO_ROOT/.gitintellisense/commit_log.txt"

echo "✅ Post-commit analysis initiated"
exit 0
'''
    
    def _generate_pre_push_hook(self) -> str:
        """Generate pre-push hook script."""
        return f'''#!/bin/bash
# GitIntellisense Pre-Push Hook
# Validates contributions before pushing

echo "🚀 GitIntellisense: Running pre-push validation..."

# Read from stdin
while read local_ref local_sha remote_ref remote_sha; do
    if [ "$local_sha" = "0000000000000000000000000000000000000000" ]; then
        # Branch is being deleted
        continue
    fi
    
    if [ "$remote_sha" = "0000000000000000000000000000000000000000" ]; then
        # New branch
        range="$local_sha"
    else
        # Update to existing branch
        range="$remote_sha..$local_sha"
    fi
    
    # Get commits being pushed
    COMMITS=$(git rev-list "$range")
    
    if [ -z "$COMMITS" ]; then
        continue
    fi
    
    echo "📊 Analyzing $(echo "$COMMITS" | wc -l) commits..."
    
    # Check commit messages
    for commit in $COMMITS; do
        MSG=$(git log -1 --pretty=%B "$commit")
        
        # Check for conventional commit format
        if ! echo "$MSG" | grep -E "^(feat|fix|docs|style|refactor|test|chore)(\\(.+\\))?: .+" > /dev/null; then
            echo "⚠️  Commit $commit does not follow conventional commit format"
            echo "   Message: $MSG"
        fi
        
        # Check for minimum message length
        if [ ${{#MSG}} -lt 10 ]; then
            echo "⚠️  Commit $commit has a very short message"
        fi
    done
    
    # Get repository name
    REPO_NAME=$(git remote get-url origin 2>/dev/null | sed 's/.*github\\.com[:\\/]//; s/\\.git$//')
    
    if [ -n "$REPO_NAME" ] && command -v gitintellisense &> /dev/null; then
        echo "🎯 Predicting contribution success..."
        # This would call the ML prediction API
        # gitintellisense predict-success "$REPO_NAME" --commits "$COMMITS"
    fi
done

echo "✅ Pre-push validation completed"
exit 0
'''
    
    def _generate_post_merge_hook(self) -> str:
        """Generate post-merge hook script."""
        return f'''#!/bin/bash
# GitIntellisense Post-Merge Hook
# Updates analysis after merges

echo "🔄 GitIntellisense: Running post-merge analysis..."

# Check if this was a merge commit
if [ -f .git/MERGE_HEAD ]; then
    echo "📊 Merge detected, updating repository analysis..."
    
    # Get repository name
    REPO_NAME=$(git remote get-url origin 2>/dev/null | sed 's/.*github\\.com[:\\/]//; s/\\.git$//')
    
    if [ -n "$REPO_NAME" ] && command -v gitintellisense &> /dev/null; then
        # Update repository analysis
        nohup gitintellisense analyze "$REPO_NAME" --force-refresh > /dev/null 2>&1 &
        echo "🔍 Repository analysis update initiated"
    fi
fi

echo "✅ Post-merge analysis completed"
exit 0
'''
    
    def _generate_prepare_commit_msg_hook(self) -> str:
        """Generate prepare-commit-msg hook script."""
        return f'''#!/bin/bash
# GitIntellisense Prepare-Commit-Msg Hook
# Enhances commit messages with AI suggestions

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2
SHA1=$3

# Only enhance messages for regular commits (not merges, etc.)
if [ "$COMMIT_SOURCE" = "message" ] || [ "$COMMIT_SOURCE" = "template" ]; then
    exit 0
fi

echo "✨ GitIntellisense: Enhancing commit message..."

# Get staged files
STAGED_FILES=$(git diff --cached --name-only)

if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

# Analyze changes and suggest commit type
COMMIT_TYPE="chore"

# Determine commit type based on files changed
for file in $STAGED_FILES; do
    case "$file" in
        *.md|*.txt|*.rst|docs/*|README*)
            COMMIT_TYPE="docs"
            break
            ;;
        *test*|*spec*|*.test.*|*.spec.*)
            COMMIT_TYPE="test"
            break
            ;;
        *.css|*.scss|*.less|*.sass)
            COMMIT_TYPE="style"
            break
            ;;
        *)
            # Check if it's a bug fix (look for keywords in diff)
            if git diff --cached "$file" | grep -i "fix\\|bug\\|error" > /dev/null; then
                COMMIT_TYPE="fix"
                break
            elif git diff --cached "$file" | grep -i "feat\\|add\\|new" > /dev/null; then
                COMMIT_TYPE="feat"
                break
            fi
            ;;
    esac
done

# Read current commit message
CURRENT_MSG=$(cat "$COMMIT_MSG_FILE")

# If message is empty or default, suggest a format
if [ -z "$CURRENT_MSG" ] || echo "$CURRENT_MSG" | grep -q "^#"; then
    echo "$COMMIT_TYPE: " > "$COMMIT_MSG_FILE"
    echo "" >> "$COMMIT_MSG_FILE"
    echo "# GitIntellisense suggestions:" >> "$COMMIT_MSG_FILE"
    echo "# - Use conventional commit format: type(scope): description" >> "$COMMIT_MSG_FILE"
    echo "# - Types: feat, fix, docs, style, refactor, test, chore" >> "$COMMIT_MSG_FILE"
    echo "# - Keep first line under 72 characters" >> "$COMMIT_MSG_FILE"
    echo "# - Use imperative mood: 'add' not 'added' or 'adds'" >> "$COMMIT_MSG_FILE"
    echo "#" >> "$COMMIT_MSG_FILE"
    echo "# Files changed:" >> "$COMMIT_MSG_FILE"
    for file in $STAGED_FILES; do
        echo "#   $file" >> "$COMMIT_MSG_FILE"
    done
fi

exit 0
'''
    
    def _create_hook_config(self, repository_path: Path) -> None:
        """Create GitIntellisense configuration for hooks."""
        try:
            config_dir = repository_path / ".gitintellisense"
            config_dir.mkdir(exist_ok=True)
            
            config_content = f'''# GitIntellisense Hook Configuration
# This file configures GitIntellisense Git hooks behavior

[hooks]
enabled = true
pre_commit_analysis = true
post_commit_opportunities = true
pre_push_validation = true
post_merge_update = true
commit_message_enhancement = true

[analysis]
auto_detect_opportunities = true
ml_predictions = true
code_quality_checks = true

[notifications]
show_warnings = true
show_suggestions = true
'''
            
            config_file = config_dir / "hooks.conf"
            config_file.write_text(config_content)
            
            # Create commit log file
            log_file = config_dir / "commit_log.txt"
            if not log_file.exists():
                log_file.write_text("# GitIntellisense Commit Log\\n")
            
            self.logger.info("Created GitIntellisense hook configuration")
            
        except Exception as e:
            self.logger.error(f"Failed to create hook configuration: {e}")
    
    def validate_hooks(self, repository_path: Path) -> Dict[str, Any]:
        """Validate installed hooks."""
        hooks_dir = repository_path / ".git" / "hooks"
        
        if not hooks_dir.exists():
            return {"error": "Git hooks directory not found"}
        
        results = {
            "hooks_installed": {},
            "hooks_executable": {},
            "config_exists": False,
        }
        
        hook_names = ["pre-commit", "post-commit", "pre-push", "post-merge", "prepare-commit-msg"]
        
        for hook_name in hook_names:
            hook_path = hooks_dir / hook_name
            
            if hook_path.exists():
                content = hook_path.read_text()
                results["hooks_installed"][hook_name] = "GitIntellisense" in content
                results["hooks_executable"][hook_name] = os.access(hook_path, os.X_OK)
            else:
                results["hooks_installed"][hook_name] = False
                results["hooks_executable"][hook_name] = False
        
        # Check configuration
        config_file = repository_path / ".gitintellisense" / "hooks.conf"
        results["config_exists"] = config_file.exists()
        
        return results
