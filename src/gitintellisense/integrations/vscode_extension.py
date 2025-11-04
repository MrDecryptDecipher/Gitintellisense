"""
VS Code extension integration for GitIntellisense.

This module provides VS Code extension capabilities for seamless
integration with the GitIntellisense system directly in the IDE.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.analyzer import RepositoryAnalyzer
from ..analysis.opportunities import OpportunityDetector
from ..generation.pr_generator import PRGenerator
from ..ml.models import ContributionSuccessPredictor, OpportunityScorer
from ..utils.config import Config, get_config
from ..utils.logging import get_logger


class VSCodeExtension:
    """
    VS Code extension integration for GitIntellisense.
    
    Provides IDE integration features including:
    - Repository analysis from within VS Code
    - Opportunity detection and display
    - PR generation assistance
    - Success probability predictions
    - Code quality suggestions
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize VS Code extension."""
        self.config = config or get_config()
        self.logger = get_logger("vscode_extension")
        
        # Initialize components
        self.analyzer = RepositoryAnalyzer(config)
        self.opportunity_detector = OpportunityDetector(config)
        self.pr_generator = PRGenerator(config)
        self.success_predictor = ContributionSuccessPredictor(config)
        self.opportunity_scorer = OpportunityScorer(config)
    
    def generate_extension_manifest(self) -> Dict[str, Any]:
        """Generate VS Code extension manifest (package.json)."""
        return {
            "name": "gitintellisense",
            "displayName": "GitIntellisense",
            "description": "AI-powered GitHub contribution assistant",
            "version": "1.0.0",
            "publisher": "gitintellisense",
            "engines": {
                "vscode": "^1.74.0"
            },
            "categories": [
                "Other",
                "Machine Learning",
                "SCM Providers"
            ],
            "keywords": [
                "github",
                "contributions",
                "open-source",
                "ai",
                "machine-learning"
            ],
            "activationEvents": [
                "onCommand:gitintellisense.analyzeRepository",
                "onCommand:gitintellisense.findOpportunities",
                "onCommand:gitintellisense.generatePR",
                "onCommand:gitintellisense.predictSuccess",
                "workspaceContains:.git"
            ],
            "main": "./out/extension.js",
            "contributes": {
                "commands": [
                    {
                        "command": "gitintellisense.analyzeRepository",
                        "title": "Analyze Repository",
                        "category": "GitIntellisense"
                    },
                    {
                        "command": "gitintellisense.findOpportunities",
                        "title": "Find Contribution Opportunities",
                        "category": "GitIntellisense"
                    },
                    {
                        "command": "gitintellisense.generatePR",
                        "title": "Generate Pull Request",
                        "category": "GitIntellisense"
                    },
                    {
                        "command": "gitintellisense.predictSuccess",
                        "title": "Predict Contribution Success",
                        "category": "GitIntellisense"
                    },
                    {
                        "command": "gitintellisense.showDashboard",
                        "title": "Open Dashboard",
                        "category": "GitIntellisense"
                    }
                ],
                "menus": {
                    "explorer/context": [
                        {
                            "command": "gitintellisense.analyzeRepository",
                            "when": "explorerResourceIsFolder",
                            "group": "gitintellisense"
                        }
                    ],
                    "scm/title": [
                        {
                            "command": "gitintellisense.findOpportunities",
                            "group": "navigation"
                        },
                        {
                            "command": "gitintellisense.generatePR",
                            "group": "navigation"
                        }
                    ]
                },
                "configuration": {
                    "title": "GitIntellisense",
                    "properties": {
                        "gitintellisense.apiUrl": {
                            "type": "string",
                            "default": "http://localhost:8000",
                            "description": "GitIntellisense API server URL"
                        },
                        "gitintellisense.autoAnalyze": {
                            "type": "boolean",
                            "default": true,
                            "description": "Automatically analyze repositories when opened"
                        },
                        "gitintellisense.showNotifications": {
                            "type": "boolean",
                            "default": true,
                            "description": "Show opportunity notifications"
                        },
                        "gitintellisense.githubToken": {
                            "type": "string",
                            "default": "",
                            "description": "GitHub personal access token"
                        }
                    }
                },
                "views": {
                    "explorer": [
                        {
                            "id": "gitintellisenseOpportunities",
                            "name": "Contribution Opportunities",
                            "when": "gitintellisense.hasOpportunities"
                        }
                    ]
                },
                "viewsContainers": {
                    "activitybar": [
                        {
                            "id": "gitintellisense",
                            "title": "GitIntellisense",
                            "icon": "$(github)"
                        }
                    ]
                }
            },
            "scripts": {
                "vscode:prepublish": "npm run compile",
                "compile": "tsc -p ./",
                "watch": "tsc -watch -p ./"
            },
            "devDependencies": {
                "@types/vscode": "^1.74.0",
                "@types/node": "16.x",
                "typescript": "^4.9.4"
            },
            "dependencies": {
                "axios": "^1.4.0",
                "ws": "^8.13.0"
            }
        }
    
    def generate_extension_code(self) -> str:
        """Generate TypeScript extension code."""
        return r'''import * as vscode from 'vscode';
import axios from 'axios';

export function activate(context: vscode.ExtensionContext) {
    console.log('GitIntellisense extension is now active!');

    // Register commands
    const analyzeCommand = vscode.commands.registerCommand('gitintellisense.analyzeRepository', async () => {
        await analyzeCurrentRepository();
    });

    const findOpportunitiesCommand = vscode.commands.registerCommand('gitintellisense.findOpportunities', async () => {
        await findContributionOpportunities();
    });

    const generatePRCommand = vscode.commands.registerCommand('gitintellisense.generatePR', async () => {
        await generatePullRequest();
    });

    const predictSuccessCommand = vscode.commands.registerCommand('gitintellisense.predictSuccess', async () => {
        await predictContributionSuccess();
    });

    const showDashboardCommand = vscode.commands.registerCommand('gitintellisense.showDashboard', async () => {
        await showDashboard();
    });

    context.subscriptions.push(
        analyzeCommand,
        findOpportunitiesCommand,
        generatePRCommand,
        predictSuccessCommand,
        showDashboardCommand
    );

    // Auto-analyze on workspace open
    if (vscode.workspace.workspaceFolders) {
        const config = vscode.workspace.getConfiguration('gitintellisense');
        if (config.get('autoAnalyze')) {
            setTimeout(() => analyzeCurrentRepository(), 2000);
        }
    }
}

async function analyzeCurrentRepository() {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        vscode.window.showErrorMessage('No workspace folder found');
        return;
    }

    const repositoryName = await getRepositoryName(workspaceFolder.uri.fsPath);
    if (!repositoryName) {
        vscode.window.showErrorMessage('Not a Git repository or unable to determine repository name');
        return;
    }

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `Analyzing ${repositoryName}...`,
        cancellable: false
    }, async (progress) => {
        try {
            const apiUrl = getApiUrl();
            const response = await axios.post(`${apiUrl}/api/analysis/analyze`, {
                repository: repositoryName
            });

            vscode.window.showInformationMessage(
                `Repository analysis started for ${repositoryName}. Check the GitIntellisense dashboard for results.`
            );
        } catch (error) {
            vscode.window.showErrorMessage(`Analysis failed: ${error}`);
        }
    });
}

async function findContributionOpportunities() {
    const repositoryName = await getCurrentRepositoryName();
    if (!repositoryName) return;

    try {
        const apiUrl = getApiUrl();
        const response = await axios.get(`${apiUrl}/api/opportunities?repository=${repositoryName}`);
        const opportunities = response.data.data;

        if (opportunities.length === 0) {
            vscode.window.showInformationMessage('No contribution opportunities found for this repository.');
            return;
        }

        // Show opportunities in quick pick
        const items = opportunities.map((opp: any) => ({
            label: opp.title,
            description: `${opp.type} • ${opp.complexity}`,
            detail: opp.description,
            opportunity: opp
        }));

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: 'Select a contribution opportunity'
        });

        if (selected) {
            const action = await vscode.window.showInformationMessage(
                `Selected: ${selected.label}`,
                'Generate PR',
                'Predict Success',
                'View Details'
            );

            if (action === 'Generate PR') {
                await generatePRForOpportunity(selected.opportunity);
            } else if (action === 'Predict Success') {
                await predictSuccessForOpportunity(repositoryName, selected.opportunity);
            }
        }
    } catch (error) {
        vscode.window.showErrorMessage(`Failed to find opportunities: ${error}`);
    }
}

async function generatePullRequest() {
    const repositoryName = await getCurrentRepositoryName();
    if (!repositoryName) return;

    const prType = await vscode.window.showQuickPick([
        { label: 'Bug Fix', value: 'bug_fix' },
        { label: 'Documentation', value: 'documentation' },
        { label: 'Testing', value: 'testing' },
        { label: 'Feature', value: 'feature' }
    ], {
        placeHolder: 'Select PR type'
    });

    if (!prType) return;

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Generating pull request...',
        cancellable: false
    }, async (progress) => {
        try {
            const apiUrl = getApiUrl();
            const response = await axios.post(`${apiUrl}/api/pr-generation/generate`, {
                repository: repositoryName,
                type: prType.value,
                dry_run: true
            });

            vscode.window.showInformationMessage(
                'PR generation started! Check the GitIntellisense dashboard for results.'
            );
        } catch (error) {
            vscode.window.showErrorMessage(`PR generation failed: ${error}`);
        }
    });
}

async function predictContributionSuccess() {
    vscode.window.showInformationMessage('Success prediction feature coming soon!');
}

async function showDashboard() {
    const apiUrl = getApiUrl();
    const dashboardUrl = apiUrl.replace('/api', '').replace(':8000', ':3000');
    vscode.env.openExternal(vscode.Uri.parse(dashboardUrl));
}

async function generatePRForOpportunity(opportunity: any) {
    const repositoryName = await getCurrentRepositoryName();
    if (!repositoryName) return;

    try {
        const apiUrl = getApiUrl();
        await axios.post(`${apiUrl}/api/pr-generation/generate`, {
            repository: repositoryName,
            opportunity_id: opportunity.id,
            dry_run: true
        });

        vscode.window.showInformationMessage(
            `PR generation started for opportunity: ${opportunity.title}`
        );
    } catch (error) {
        vscode.window.showErrorMessage(`PR generation failed: ${error}`);
    }
}

async function predictSuccessForOpportunity(repository: string, opportunity: any) {
    try {
        const apiUrl = getApiUrl();
        const response = await axios.get(
            `${apiUrl}/api/predict-success/${repository}/${opportunity.id}`
        );

        const probability = response.data.success_probability;
        const confidence = response.data.confidence;

        vscode.window.showInformationMessage(
            `Success probability: ${(probability * 100).toFixed(1)}% (${confidence} confidence)`
        );
    } catch (error) {
        vscode.window.showErrorMessage(`Prediction failed: ${error}`);
    }
}

async function getCurrentRepositoryName(): Promise<string | null> {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        vscode.window.showErrorMessage('No workspace folder found');
        return null;
    }

    return await getRepositoryName(workspaceFolder.uri.fsPath);
}

async function getRepositoryName(workspacePath: string): Promise<string | null> {
    try {
        // Try to get repository name from git remote
        const { exec } = require('child_process');
        const { promisify } = require('util');
        const execAsync = promisify(exec);

        const { stdout } = await execAsync('git remote get-url origin', { cwd: workspacePath });
        const remoteUrl = stdout.trim();

        // Extract repository name from URL
        const match = remoteUrl.match(/github\\.com[:/]([^/]+\/[^/]+?)(\\.git)?$/);
        return match ? match[1] : null;
    } catch (error) {
        return null;
    }
}

function getApiUrl(): string {
    const config = vscode.workspace.getConfiguration('gitintellisense');
    return config.get('apiUrl') || 'http://localhost:8000';
}

export function deactivate() {}
'''
    
    def create_extension_files(self, output_dir: Path) -> None:
        """Create VS Code extension files."""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create package.json
            manifest = self.generate_extension_manifest()
            with open(output_dir / "package.json", "w") as f:
                json.dump(manifest, f, indent=2)
            
            # Create src directory and extension.ts
            src_dir = output_dir / "src"
            src_dir.mkdir(exist_ok=True)
            
            extension_code = self.generate_extension_code()
            with open(src_dir / "extension.ts", "w") as f:
                f.write(extension_code)
            
            # Create tsconfig.json
            tsconfig = {
                "compilerOptions": {
                    "module": "commonjs",
                    "target": "ES2020",
                    "outDir": "out",
                    "lib": ["ES2020"],
                    "sourceMap": True,
                    "rootDir": "src",
                    "strict": True
                },
                "exclude": ["node_modules", ".vscode-test"]
            }
            
            with open(output_dir / "tsconfig.json", "w") as f:
                json.dump(tsconfig, f, indent=2)
            
            # Create README.md
            readme_content = """# GitIntellisense VS Code Extension

AI-powered GitHub contribution assistant for VS Code.

## Features

- **Repository Analysis**: Analyze GitHub repositories for contribution opportunities
- **Opportunity Detection**: Find and rank contribution opportunities
- **PR Generation**: Generate pull requests automatically
- **Success Prediction**: Predict contribution success probability
- **Dashboard Integration**: Access web dashboard directly from VS Code

## Installation

1. Install the extension from the VS Code marketplace
2. Configure your GitHub token in settings
3. Set the GitIntellisense API URL if using a custom server

## Usage

1. Open a Git repository in VS Code
2. Use Command Palette (Ctrl+Shift+P) and search for "GitIntellisense"
3. Run analysis and find opportunities
4. Generate PRs with AI assistance

## Configuration

- `gitintellisense.apiUrl`: API server URL (default: http://localhost:8000)
- `gitintellisense.autoAnalyze`: Auto-analyze repositories (default: true)
- `gitintellisense.githubToken`: GitHub personal access token

## Commands

- `GitIntellisense: Analyze Repository`
- `GitIntellisense: Find Contribution Opportunities`
- `GitIntellisense: Generate Pull Request`
- `GitIntellisense: Predict Contribution Success`
- `GitIntellisense: Open Dashboard`
"""
            
            with open(output_dir / "README.md", "w") as f:
                f.write(readme_content)
            
            self.logger.info(f"VS Code extension files created in {output_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to create extension files: {e}")
            raise
    
    def install_extension(self, extension_dir: Path) -> bool:
        """Install the VS Code extension."""
        try:
            # Build the extension
            subprocess.run(["npm", "install"], cwd=extension_dir, check=True)
            subprocess.run(["npm", "run", "compile"], cwd=extension_dir, check=True)
            
            # Package the extension
            subprocess.run(["npx", "vsce", "package"], cwd=extension_dir, check=True)
            
            # Install the extension
            vsix_files = list(extension_dir.glob("*.vsix"))
            if vsix_files:
                subprocess.run(["code", "--install-extension", str(vsix_files[0])], check=True)
                self.logger.info("VS Code extension installed successfully")
                return True
            else:
                self.logger.error("No VSIX file found")
                return False
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install extension: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Extension installation failed: {e}")
            return False
