"""
Command-line interface for the GitHub Repository Scanner and Automated Contribution System.

This module provides a comprehensive CLI for interacting with the system,
performing repository analysis, and managing contributions.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.json import JSON

from .core.analyzer import RepositoryAnalyzer
from .analysis.opportunities import OpportunityDetector
from .generation.pr_generator import PRGenerator
from .batch.multi_scanner import MultiRepositoryScanner
from .ml.models import ContributionSuccessPredictor, OpportunityScorer
from .integrations.vscode_extension import VSCodeExtension
from .integrations.git_hooks import GitHooksManager
from .analytics.advanced_metrics import AdvancedMetricsEngine
from .automation.continuous_contributor import ContinuousContributor
from .web.api_server import APIServer
from .utils.config import Config, get_config
from .utils.logging import setup_logging, log_system_info
from .utils.database import DatabaseManager

console = Console()


@click.group()
@click.option("--config", "-c", help="Configuration file path")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def cli(ctx, config, verbose, debug):
    """GitHub Repository Scanner and Automated Contribution System."""
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Load configuration
    try:
        ctx.obj["config"] = get_config()
        if verbose:
            ctx.obj["config"].development.verbose_logging = True
        if debug:
            ctx.obj["config"].development.debug = True
            
        # Setup logging
        setup_logging(ctx.obj["config"])
        log_system_info()
        
        # Initialize database
        ctx.obj["db"] = DatabaseManager(ctx.obj["config"])
        
        console.print("[green]✓[/green] System initialized successfully")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to initialize system: {e}")
        sys.exit(1)


@cli.command()
@click.argument("repository")
@click.option("--quick", is_flag=True, help="Perform quick analysis only")
@click.option("--no-patterns", is_flag=True, help="Skip pattern analysis")
@click.option("--no-opportunities", is_flag=True, help="Skip opportunity detection")
@click.option("--output", "-o", help="Output file for results")
@click.option("--format", "output_format", type=click.Choice(["json", "table"]), default="table", help="Output format")
@click.pass_context
def analyze(ctx, repository, quick, no_patterns, no_opportunities, output, output_format):
    """Analyze a GitHub repository for contribution opportunities."""
    
    async def run_analysis():
        analyzer = RepositoryAnalyzer(ctx.obj["config"])
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                if quick:
                    task = progress.add_task("Performing quick analysis...", total=None)
                    results = await analyzer.analyze_repository_quick(repository)
                else:
                    task = progress.add_task("Performing comprehensive analysis...", total=None)
                    results = await analyzer.analyze_repository_comprehensive(
                        repository,
                        include_patterns=not no_patterns,
                        include_opportunities=not no_opportunities
                    )
                
                progress.update(task, description="Analysis complete!")
            
            # Store results in database
            analysis_type = "quick" if quick else "comprehensive"
            analysis_id = ctx.obj["db"].store_repository_analysis(
                repository, analysis_type, results
            )
            
            # Display results
            if output_format == "json":
                display_json_results(results)
            else:
                display_table_results(results, quick)
            
            # Save to file if requested
            if output:
                save_results_to_file(results, output)
                console.print(f"[green]✓[/green] Results saved to {output}")
            
            console.print(f"[green]✓[/green] Analysis stored with ID: {analysis_id}")
            
        except Exception as e:
            console.print(f"[red]✗[/red] Analysis failed: {e}")
            sys.exit(1)
        finally:
            await analyzer.close()
    
    asyncio.run(run_analysis())


@cli.command()
@click.argument("repository")
@click.option("--skills", help="Comma-separated list of your skills")
@click.option("--focus", help="Comma-separated list of focus areas")
@click.option("--min-score", type=float, help="Minimum opportunity score")
@click.option("--output", "-o", help="Output file for results")
@click.pass_context
def opportunities(ctx, repository, skills, focus, min_score, output):
    """Detect contribution opportunities in a repository."""
    
    async def run_detection():
        analyzer = RepositoryAnalyzer(ctx.obj["config"])
        detector = OpportunityDetector(ctx.obj["config"])
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                # First get repository analysis
                task1 = progress.add_task("Analyzing repository...", total=None)
                repo_analysis = await analyzer.analyze_repository_comprehensive(repository)
                progress.update(task1, description="Repository analysis complete")
                
                # Parse skills and focus areas
                contributor_skills = skills.split(",") if skills else None
                focus_areas = focus.split(",") if focus else None
                
                # Detect opportunities
                task2 = progress.add_task("Detecting opportunities...", total=None)
                opportunities_result = await detector.detect_opportunities(
                    repository,
                    repo_analysis,
                    contributor_skills,
                    focus_areas
                )
                progress.update(task2, description="Opportunity detection complete")
            
            # Store opportunities in database
            if opportunities_result.get("opportunities"):
                opportunity_ids = ctx.obj["db"].store_opportunities(
                    repository, opportunities_result["opportunities"]
                )
                console.print(f"[green]✓[/green] Stored {len(opportunity_ids)} opportunities")
            
            # Display opportunities
            display_opportunities(opportunities_result)
            
            # Save to file if requested
            if output:
                save_results_to_file(opportunities_result, output)
                console.print(f"[green]✓[/green] Results saved to {output}")
            
        except Exception as e:
            console.print(f"[red]✗[/red] Opportunity detection failed: {e}")
            sys.exit(1)
        finally:
            await analyzer.close()
    
    asyncio.run(run_detection())


@cli.command()
@click.argument("repository")
@click.option("--limit", type=int, default=10, help="Number of opportunities to show")
@click.pass_context
def list_opportunities(ctx, repository, limit):
    """List stored opportunities for a repository."""
    try:
        opportunities = ctx.obj["db"].get_opportunities(repository, limit=limit)
        
        if not opportunities:
            console.print(f"[yellow]No opportunities found for {repository}[/yellow]")
            return
        
        table = Table(title=f"Opportunities for {repository}")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Title", style="bold")
        table.add_column("Score", style="magenta")
        table.add_column("Complexity", style="yellow")
        table.add_column("Status", style="blue")
        
        for opp in opportunities:
            table.add_row(
                str(opp["id"]),
                opp["type"],
                opp["title"][:50] + "..." if len(opp["title"]) > 50 else opp["title"],
                f"{opp['score']:.1f}",
                opp["complexity"] or "Unknown",
                opp["status"]
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to list opportunities: {e}")


@cli.command()
@click.option("--repository", help="Filter by repository")
@click.pass_context
def stats(ctx, repository):
    """Show contribution statistics."""
    try:
        stats_data = ctx.obj["db"].get_contribution_stats(repository)
        
        if not stats_data:
            console.print("[yellow]No contribution statistics available[/yellow]")
            return
        
        panel_content = f"""
[bold]Contribution Statistics[/bold]

Total Attempts: {stats_data.get('total_attempts', 0)}
Merged: {stats_data.get('merged_attempts', 0)}
Closed: {stats_data.get('closed_attempts', 0)}
Success Rate: {stats_data.get('success_rate', 0):.1f}%
Repositories: {stats_data.get('repositories_contributed', 0)}
        """
        
        console.print(Panel(panel_content, title="Statistics", border_style="green"))
        
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to get statistics: {e}")


@cli.command()
@click.pass_context
def config_check(ctx):
    """Check system configuration."""
    try:
        config = ctx.obj["config"]
        
        # Check required credentials
        config.validate_required_credentials()
        
        table = Table(title="Configuration Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")
        
        # GitHub configuration
        table.add_row(
            "GitHub API",
            "✓ Configured",
            f"Username: {config.github.username}"
        )
        
        # OpenRouter configuration
        table.add_row(
            "OpenRouter AI",
            "✓ Configured",
            f"Model: {config.openrouter.model}"
        )
        
        # Database configuration
        table.add_row(
            "Database",
            "✓ Connected",
            f"URL: {config.database.url}"
        )
        
        # Feature flags
        enabled_features = [
            name for name, enabled in config.features.model_dump().items() 
            if enabled
        ]
        table.add_row(
            "Features",
            f"✓ {len(enabled_features)} enabled",
            ", ".join(enabled_features)
        )
        
        console.print(table)
        console.print("[green]✓[/green] Configuration is valid")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Configuration error: {e}")
        sys.exit(1)


@cli.command()
@click.argument("repository")
@click.option("--opportunity-id", type=int, help="Specific opportunity ID to generate PR for")
@click.option("--type", "pr_type", type=click.Choice(["bug_fix", "documentation", "testing", "feature"]), help="Type of PR to generate")
@click.option("--issue-number", type=int, help="Issue number for bug fix PRs")
@click.option("--dry-run", is_flag=True, default=True, help="Don't actually create PR (default: true)")
@click.option("--force", is_flag=True, help="Actually create PR (overrides dry-run)")
@click.pass_context
def generate_pr(ctx, repository, opportunity_id, pr_type, issue_number, dry_run, force):
    """Generate and optionally submit a pull request."""

    # Override dry_run if force is specified
    if force:
        dry_run = False

    async def run_pr_generation():
        pr_generator = PRGenerator(ctx.obj["config"])

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:

                if opportunity_id:
                    # Generate PR for specific opportunity
                    task = progress.add_task("Fetching opportunity...", total=None)
                    opportunities = ctx.obj["db"].get_opportunities(repository, limit=100)
                    opportunity = next((opp for opp in opportunities if opp["id"] == opportunity_id), None)

                    if not opportunity:
                        console.print(f"[red]✗[/red] Opportunity {opportunity_id} not found")
                        return

                    progress.update(task, description="Generating PR...")
                    result = await pr_generator.generate_and_submit_pr(opportunity, repository, dry_run)

                elif pr_type == "bug_fix" and issue_number:
                    # Generate bug fix PR
                    task = progress.add_task("Generating bug fix PR...", total=None)
                    result = await pr_generator.generate_bug_fix_pr(repository, issue_number, dry_run)

                elif pr_type == "documentation":
                    # Generate documentation PR
                    task = progress.add_task("Generating documentation PR...", total=None)
                    result = await pr_generator.generate_documentation_pr(repository, "readme", dry_run)

                elif pr_type == "testing":
                    # Generate testing PR
                    task = progress.add_task("Generating testing PR...", total=None)
                    result = await pr_generator.generate_test_pr(repository, "unit", dry_run)

                else:
                    console.print("[red]✗[/red] Please specify either --opportunity-id or --type with appropriate options")
                    return

                progress.update(task, description="PR generation complete!")

            # Display results
            display_pr_generation_results(result, dry_run)

            # Store contribution attempt if successful
            if result.get("status") == "success" and not dry_run:
                opportunity_id = result.get("opportunity_id")
                pr_info = result.get("pr", {})

                if opportunity_id and pr_info.get("pr_number"):
                    ctx.obj["db"].store_contribution_attempt(
                        opportunity_id,
                        repository,
                        "created",
                        pr_info["pr_number"],
                        pr_info.get("pr_url"),
                        "PR generated automatically"
                    )

        except Exception as e:
            console.print(f"[red]✗[/red] PR generation failed: {e}")
            sys.exit(1)

    asyncio.run(run_pr_generation())


@cli.command()
@click.argument("repositories", nargs=-1, required=True)
@click.option("--concurrent", type=int, default=5, help="Maximum concurrent scans")
@click.option("--priority-order", is_flag=True, help="Scan repositories in priority order")
@click.option("--include-opportunities", is_flag=True, default=True, help="Detect opportunities during scan")
@click.option("--force-refresh", is_flag=True, help="Force refresh of existing analyses")
@click.option("--output", type=click.Path(), help="Save results to file")
@click.pass_context
def batch_scan(ctx, repositories, concurrent, priority_order, include_opportunities, force_refresh, output):
    """Scan multiple repositories simultaneously."""

    async def run_batch_scan():
        scanner = MultiRepositoryScanner(ctx.obj["config"])

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:

                task = progress.add_task(
                    f"Scanning {len(repositories)} repositories...",
                    total=len(repositories)
                )

                # Configure scanner
                scanner.max_concurrent = concurrent

                # Start batch scan
                results = await scanner.scan_repositories(
                    list(repositories),
                    priority_order=priority_order,
                    include_opportunities=include_opportunities,
                    force_refresh=force_refresh
                )

                progress.update(task, completed=len(repositories))

            # Display results
            display_batch_scan_results(results)

            # Save to file if requested
            if output:
                save_results_to_file(results, output)
                console.print(f"[green]✓[/green] Results saved to {output}")

        except Exception as e:
            console.print(f"[red]✗[/red] Batch scan failed: {e}")
            sys.exit(1)

    asyncio.run(run_batch_scan())


@cli.command()
@click.option("--language", help="Programming language filter")
@click.option("--time-range", type=click.Choice(["daily", "weekly", "monthly"]), default="daily", help="Trending time range")
@click.option("--limit", type=int, default=25, help="Maximum repositories to scan")
@click.option("--output", type=click.Path(), help="Save results to file")
@click.pass_context
def scan_trending(ctx, language, time_range, limit, output):
    """Scan trending repositories from GitHub."""

    async def run_trending_scan():
        scanner = MultiRepositoryScanner(ctx.obj["config"])

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:

                task = progress.add_task(
                    f"Scanning trending {language or 'all'} repositories ({time_range})...",
                    total=None
                )

                results = await scanner.scan_github_trending(
                    language=language,
                    time_range=time_range,
                    limit=limit
                )

                progress.update(task, description="Trending scan complete!")

            # Display results
            display_batch_scan_results(results)

            # Save to file if requested
            if output:
                save_results_to_file(results, output)
                console.print(f"[green]✓[/green] Results saved to {output}")

        except Exception as e:
            console.print(f"[red]✗[/red] Trending scan failed: {e}")
            sys.exit(1)

    asyncio.run(run_trending_scan())


@cli.command()
@click.argument("organization")
@click.option("--include-forks", is_flag=True, help="Include forked repositories")
@click.option("--min-stars", type=int, default=0, help="Minimum star count")
@click.option("--max-repos", type=int, default=50, help="Maximum repositories to scan")
@click.option("--output", type=click.Path(), help="Save results to file")
@click.pass_context
def scan_org(ctx, organization, include_forks, min_stars, max_repos, output):
    """Scan all repositories from a GitHub organization."""

    async def run_org_scan():
        scanner = MultiRepositoryScanner(ctx.obj["config"])

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:

                task = progress.add_task(
                    f"Scanning {organization} repositories...",
                    total=None
                )

                results = await scanner.scan_organization_repositories(
                    organization=organization,
                    include_forks=include_forks,
                    min_stars=min_stars,
                    max_repositories=max_repos
                )

                progress.update(task, description="Organization scan complete!")

            # Display results
            display_batch_scan_results(results)

            # Save to file if requested
            if output:
                save_results_to_file(results, output)
                console.print(f"[green]✓[/green] Results saved to {output}")

        except Exception as e:
            console.print(f"[red]✗[/red] Organization scan failed: {e}")
            sys.exit(1)

    asyncio.run(run_org_scan())


@cli.command()
@click.option("--retrain", is_flag=True, help="Force retrain even if model exists")
@click.option("--model-type", type=click.Choice(["success", "scoring", "both"]), default="both", help="Type of model to train")
@click.pass_context
def train_ml(ctx, retrain, model_type):
    """Train machine learning models for contribution prediction."""

    async def run_ml_training():
        try:
            results = {}

            if model_type in ["success", "both"]:
                console.print("[blue]Training contribution success prediction model...[/blue]")

                predictor = ContributionSuccessPredictor(ctx.obj["config"])
                success_result = predictor.train_model(retrain=retrain)
                results["success_model"] = success_result

                if success_result["status"] == "trained":
                    metrics = success_result["metrics"]
                    console.print(f"[green]✓[/green] Success model trained!")
                    console.print(f"  Accuracy: {metrics['accuracy']:.3f}")
                    console.print(f"  F1 Score: {metrics['f1_score']:.3f}")
                    console.print(f"  Training samples: {success_result['training_samples']}")
                elif success_result["status"] == "loaded_existing":
                    console.print(f"[yellow]✓[/yellow] Loaded existing success model")
                else:
                    console.print(f"[red]✗[/red] Success model training failed: {success_result.get('error', 'Unknown error')}")

            if model_type in ["scoring", "both"]:
                console.print("[blue]Training opportunity scoring model...[/blue]")

                scorer = OpportunityScorer(ctx.obj["config"])
                scoring_result = scorer.train_scoring_model()
                results["scoring_model"] = scoring_result

                if scoring_result["status"] == "trained":
                    console.print(f"[green]✓[/green] Scoring model trained!")
                    console.print(f"  Train Score: {scoring_result['train_score']:.3f}")
                    console.print(f"  Test Score: {scoring_result['test_score']:.3f}")
                    console.print(f"  Training samples: {scoring_result['training_samples']}")
                elif scoring_result["status"] == "insufficient_data":
                    console.print(f"[yellow]⚠[/yellow] Insufficient data for scoring model")
                else:
                    console.print(f"[red]✗[/red] Scoring model training failed: {scoring_result.get('error', 'Unknown error')}")

            # Display summary
            console.print(Panel(f"[bold]ML Training Summary[/bold]", border_style="blue"))
            for model_name, result in results.items():
                status = result.get("status", "unknown")
                console.print(f"{model_name}: {status}")

        except Exception as e:
            console.print(f"[red]✗[/red] ML training failed: {e}")
            sys.exit(1)

    asyncio.run(run_ml_training())


@cli.command()
@click.argument("repository")
@click.argument("opportunity_id", type=int)
@click.pass_context
def predict_success(ctx, repository, opportunity_id):
    """Predict success probability for a contribution opportunity."""

    async def run_prediction():
        try:
            # Get opportunity details
            opportunities = ctx.obj["db"].get_opportunities(limit=1000)
            opportunity = next((opp for opp in opportunities if opp["id"] == opportunity_id), None)

            if not opportunity:
                console.print(f"[red]✗[/red] Opportunity {opportunity_id} not found")
                return

            # Make prediction
            predictor = ContributionSuccessPredictor(ctx.obj["config"])
            result = predictor.predict_success_probability(repository, opportunity)

            if "error" in result:
                console.print(f"[red]✗[/red] Prediction failed: {result['error']}")
                return

            # Display results
            probability = result["success_probability"]
            confidence = result["confidence"]

            console.print(Panel(f"[bold]Success Prediction[/bold]", border_style="green"))
            console.print(f"[bold]Repository:[/bold] {repository}")
            console.print(f"[bold]Opportunity:[/bold] #{opportunity_id} - {opportunity.get('title', 'Unknown')}")
            console.print(f"[bold]Success Probability:[/bold] {probability:.1%}")
            console.print(f"[bold]Confidence:[/bold] {confidence}")

            # Recommendation
            if probability > 0.7:
                console.print("[green]✓ High chance of success - Recommended![/green]")
            elif probability > 0.5:
                console.print("[yellow]⚠ Moderate chance of success[/yellow]")
            else:
                console.print("[red]⚠ Low chance of success - Consider other opportunities[/red]")

            # Top contributing factors
            feature_importance = result.get("feature_importance", {})
            if feature_importance:
                top_features = sorted(
                    feature_importance.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]

                console.print("\n[bold]Top Contributing Factors:[/bold]")
                for feature, importance in top_features:
                    console.print(f"  • {feature}: {importance:.3f}")

        except Exception as e:
            console.print(f"[red]✗[/red] Prediction failed: {e}")
            sys.exit(1)

    asyncio.run(run_prediction())


@cli.command()
@click.option("--output-dir", type=click.Path(), default="./gitintellisense-vscode", help="Output directory for extension")
@click.option("--install", is_flag=True, help="Install extension after creation")
@click.pass_context
def create_vscode_extension(ctx, output_dir, install):
    """Create VS Code extension for GitIntellisense."""

    try:
        extension = VSCodeExtension(ctx.obj["config"])
        output_path = Path(output_dir)

        console.print(f"[blue]Creating VS Code extension in {output_path}...[/blue]")

        # Create extension files
        extension.create_extension_files(output_path)

        console.print(f"[green]✓[/green] VS Code extension created in {output_path}")
        console.print(f"[green]✓[/green] Files created:")
        console.print(f"  • package.json")
        console.print(f"  • src/extension.ts")
        console.print(f"  • tsconfig.json")
        console.print(f"  • README.md")

        if install:
            console.print("[blue]Installing extension...[/blue]")
            if extension.install_extension(output_path):
                console.print("[green]✓[/green] Extension installed successfully")
            else:
                console.print("[red]✗[/red] Extension installation failed")
        else:
            console.print("\n[yellow]To install the extension:[/yellow]")
            console.print(f"  cd {output_path}")
            console.print("  npm install")
            console.print("  npm run compile")
            console.print("  npx vsce package")
            console.print("  code --install-extension *.vsix")

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to create VS Code extension: {e}")
        sys.exit(1)


@cli.command()
@click.argument("repository_path", type=click.Path(exists=True), default=".")
@click.option("--uninstall", is_flag=True, help="Uninstall hooks instead of installing")
@click.pass_context
def setup_git_hooks(ctx, repository_path, uninstall):
    """Setup Git hooks for GitIntellisense integration."""

    try:
        hooks_manager = GitHooksManager(ctx.obj["config"])
        repo_path = Path(repository_path).resolve()

        if uninstall:
            console.print(f"[blue]Uninstalling Git hooks from {repo_path}...[/blue]")
            results = hooks_manager.uninstall_hooks(repo_path)
        else:
            console.print(f"[blue]Installing Git hooks in {repo_path}...[/blue]")
            results = hooks_manager.install_hooks(repo_path)

        if "error" in results:
            console.print(f"[red]✗[/red] {results['error']}")
            sys.exit(1)

        # Display results
        action = "Uninstalled" if uninstall else "Installed"
        console.print(f"[green]✓[/green] Git hooks {action.lower()}:")

        for hook_name, success in results.items():
            status = "✓" if success else "✗"
            color = "green" if success else "red"
            console.print(f"  [{color}]{status}[/{color}] {hook_name}")

        if not uninstall:
            console.print("\n[blue]Git hooks features:[/blue]")
            console.print("  • Pre-commit: Code quality checks")
            console.print("  • Post-commit: Opportunity detection")
            console.print("  • Pre-push: Contribution validation")
            console.print("  • Post-merge: Analysis updates")
            console.print("  • Prepare-commit-msg: Message enhancement")

    except Exception as e:
        console.print(f"[red]✗[/red] Git hooks setup failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument("repository_path", type=click.Path(exists=True), default=".")
@click.pass_context
def validate_hooks(ctx, repository_path):
    """Validate installed Git hooks."""

    try:
        hooks_manager = GitHooksManager(ctx.obj["config"])
        repo_path = Path(repository_path).resolve()

        console.print(f"[blue]Validating Git hooks in {repo_path}...[/blue]")

        results = hooks_manager.validate_hooks(repo_path)

        if "error" in results:
            console.print(f"[red]✗[/red] {results['error']}")
            sys.exit(1)

        # Display validation results
        console.print("[bold]Hook Installation Status:[/bold]")
        for hook_name, installed in results["hooks_installed"].items():
            executable = results["hooks_executable"].get(hook_name, False)

            if installed and executable:
                console.print(f"  [green]✓[/green] {hook_name} - Installed and executable")
            elif installed:
                console.print(f"  [yellow]⚠[/yellow] {hook_name} - Installed but not executable")
            else:
                console.print(f"  [red]✗[/red] {hook_name} - Not installed")

        # Configuration status
        config_exists = results.get("config_exists", False)
        if config_exists:
            console.print(f"  [green]✓[/green] Configuration file exists")
        else:
            console.print(f"  [yellow]⚠[/yellow] Configuration file missing")

        # Overall status
        all_installed = all(results["hooks_installed"].values())
        all_executable = all(results["hooks_executable"].values())

        if all_installed and all_executable and config_exists:
            console.print("\n[green]✓ All hooks are properly installed and configured[/green]")
        else:
            console.print("\n[yellow]⚠ Some hooks may need attention[/yellow]")

    except Exception as e:
        console.print(f"[red]✗[/red] Hook validation failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument("repository")
@click.option("--include-trends", is_flag=True, default=True, help="Include trend analysis")
@click.option("--output", type=click.Path(), help="Save results to file")
@click.pass_context
def advanced_metrics(ctx, repository, include_trends, output):
    """Generate advanced metrics and health analysis for a repository."""

    async def run_advanced_metrics():
        try:
            metrics_engine = AdvancedMetricsEngine(ctx.obj["config"])

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:

                task = progress.add_task(
                    f"Analyzing {repository} with advanced metrics...",
                    total=None
                )

                # Calculate comprehensive health score
                health_analysis = await metrics_engine.calculate_comprehensive_health_score(
                    repository,
                    include_trends=include_trends
                )

                progress.update(task, description="Advanced metrics analysis complete!")

            # Display results
            display_advanced_metrics_results(health_analysis)

            # Save to file if requested
            if output:
                save_results_to_file(health_analysis, output)
                console.print(f"[green]✓[/green] Results saved to {output}")

        except Exception as e:
            console.print(f"[red]✗[/red] Advanced metrics analysis failed: {e}")
            sys.exit(1)

    asyncio.run(run_advanced_metrics())


@cli.command()
@click.argument("repository")
@click.option("--include-all", is_flag=True, help="Include all metrics (comprehensive report)")
@click.option("--output", type=click.Path(), help="Save results to file")
@click.pass_context
def generate_report(ctx, repository, include_all, output):
    """Generate comprehensive repository analysis report."""

    async def run_report_generation():
        try:
            metrics_engine = AdvancedMetricsEngine(ctx.obj["config"])

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:

                task = progress.add_task(
                    f"Generating comprehensive report for {repository}...",
                    total=None
                )

                # Generate comprehensive report
                report = await metrics_engine.generate_repository_report(
                    repository,
                    include_all_metrics=include_all
                )

                progress.update(task, description="Report generation complete!")

            # Display results
            display_comprehensive_report(report)

            # Save to file if requested
            if output:
                save_results_to_file(report, output)
                console.print(f"[green]✓[/green] Report saved to {output}")

        except Exception as e:
            console.print(f"[red]✗[/red] Report generation failed: {e}")
            sys.exit(1)

    asyncio.run(run_report_generation())


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind the server to")
@click.option("--port", type=int, default=8000, help="Port for the web server")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def web(ctx, host, port, debug):
    """Start the web dashboard server."""
    console.print(f"[blue]Starting GitIntellisense web dashboard...[/blue]")
    console.print(f"[green]Server will be available at: http://{host}:{port}[/green]")
    console.print(f"[green]API endpoints at: http://{host}:{port}/api[/green]")

    try:
        server = APIServer(ctx.obj["config"])
        server.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to start web server: {e}")
        sys.exit(1)


@cli.command()
@click.option("--port", type=int, default=8080, help="Port for metrics server")
@click.pass_context
def monitor(ctx, port):
    """Start monitoring dashboard."""
    console.print(f"[blue]Starting monitoring dashboard on port {port}...[/blue]")
    console.print("[yellow]Monitoring dashboard not yet implemented[/yellow]")
    console.print("This would start a web dashboard showing:")
    console.print("- System performance metrics")
    console.print("- Analysis success rates")
    console.print("- API usage statistics")
    console.print("- Contribution tracking")


def display_json_results(results: Dict[str, Any]) -> None:
    """Display results in JSON format."""
    console.print(JSON.from_data(results))


def display_table_results(results: Dict[str, Any], quick: bool = False) -> None:
    """Display results in table format."""
    repo_name = results.get("repository", "Unknown")
    
    if quick:
        summary = results.get("quick_summary", {})
        
        console.print(Panel(f"[bold]Quick Analysis Results for {repo_name}[/bold]", border_style="blue"))
        
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Repository Health", f"{summary.get('repository_health', 0):.1f}/100")
        table.add_row("Activity Level", summary.get('activity_level', 'Unknown'))
        table.add_row("Contribution Difficulty", summary.get('contribution_difficulty', 'Unknown'))
        table.add_row("Good First Issues", str(summary.get('good_first_issues_count', 0)))
        table.add_row("Has Guidelines", "Yes" if summary.get('has_contribution_guidelines') else "No")
        
        console.print(table)
        
        if summary.get('recommendation'):
            console.print(f"\n[bold]Recommendation:[/bold] {summary['recommendation']}")
    
    else:
        summary = results.get("comprehensive_summary", {})
        assessment = summary.get("overall_assessment", {})
        metrics = summary.get("key_metrics", {})
        
        console.print(Panel(f"[bold]Comprehensive Analysis Results for {repo_name}[/bold]", border_style="blue"))
        
        # Overall assessment
        table1 = Table(title="Overall Assessment")
        table1.add_column("Metric", style="cyan")
        table1.add_column("Value", style="green")
        
        table1.add_row("Health Score", f"{assessment.get('health_score', 0):.1f}/100")
        table1.add_row("Activity Level", assessment.get('activity_level', 'Unknown'))
        table1.add_row("Maturity", assessment.get('maturity', 'Unknown'))
        table1.add_row("Contribution Difficulty", assessment.get('contribution_difficulty', 'Unknown'))
        
        console.print(table1)
        
        # Key metrics
        table2 = Table(title="Key Metrics")
        table2.add_column("Metric", style="cyan")
        table2.add_column("Value", style="green")
        
        table2.add_row("Stars", str(metrics.get('stars', 0)))
        table2.add_row("Forks", str(metrics.get('forks', 0)))
        table2.add_row("Open Issues", str(metrics.get('open_issues', 0)))
        table2.add_row("Recent Commits", str(metrics.get('recent_commits', 0)))
        table2.add_row("Good First Issues", str(metrics.get('good_first_issues', 0)))
        
        console.print(table2)
        
        # Recommendations
        recommendations = summary.get("recommendations", [])
        if recommendations:
            console.print("\n[bold]Recommendations:[/bold]")
            for i, rec in enumerate(recommendations, 1):
                console.print(f"{i}. {rec}")


def display_opportunities(opportunities_result: Dict[str, Any]) -> None:
    """Display detected opportunities."""
    opportunities = opportunities_result.get("opportunities", [])
    summary = opportunities_result.get("summary", {})
    
    if not opportunities:
        console.print("[yellow]No opportunities detected[/yellow]")
        return
    
    console.print(Panel(f"[bold]Detected {len(opportunities)} Opportunities[/bold]", border_style="green"))
    
    # Summary
    if summary:
        console.print(f"Average Score: {summary.get('average_score', 0):.1f}")
        console.print(f"By Type: {summary.get('by_type', {})}")
        console.print()
    
    # Top opportunities
    table = Table(title="Top Opportunities")
    table.add_column("Rank", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Title", style="bold")
    table.add_column("Score", style="magenta")
    table.add_column("Complexity", style="yellow")
    table.add_column("Effort", style="blue")
    
    for i, opp in enumerate(opportunities[:10], 1):
        table.add_row(
            str(i),
            opp.get("type", "Unknown"),
            opp.get("title", "Unknown")[:40] + "..." if len(opp.get("title", "")) > 40 else opp.get("title", "Unknown"),
            f"{opp.get('score', 0):.1f}",
            opp.get("complexity", "Unknown"),
            opp.get("estimated_effort", "Unknown")
        )
    
    console.print(table)
    
    # Next steps
    next_steps = summary.get("recommended_next_steps", [])
    if next_steps:
        console.print("\n[bold]Recommended Next Steps:[/bold]")
        for step in next_steps:
            console.print(f"• {step}")


def display_pr_generation_results(result: Dict[str, Any], dry_run: bool) -> None:
    """Display PR generation results."""
    if "error" in result:
        console.print(f"[red]✗[/red] PR generation failed: {result['error']}")
        return

    status = result.get("status", "unknown")

    if status == "success":
        console.print(Panel(f"[bold green]PR Generation {'Simulated' if dry_run else 'Completed'}[/bold green]", border_style="green"))

        # Solution info
        solution = result.get("solution", {})
        if solution:
            console.print(f"[bold]Branch:[/bold] {solution.get('branch_name', 'unknown')}")
            console.print(f"[bold]Commit:[/bold] {solution.get('commit_message', 'unknown')}")
            console.print(f"[bold]Changes:[/bold] {len(solution.get('changes', []))} files modified")

        # Validation info
        validation = result.get("validation", {})
        if validation:
            valid = validation.get("valid", False)
            score = validation.get("score", 0)
            console.print(f"[bold]Validation:[/bold] {'✓ Passed' if valid else '✗ Failed'} (Score: {score})")

        # PR info
        pr_info = result.get("pr", {})
        if pr_info and not dry_run:
            if pr_info.get("pr_url"):
                console.print(f"[bold]PR URL:[/bold] {pr_info['pr_url']}")
                console.print(f"[bold]PR Number:[/bold] #{pr_info.get('pr_number', 'unknown')}")
            else:
                console.print(f"[yellow]PR creation status:[/yellow] {pr_info.get('status', 'unknown')}")
        elif dry_run:
            console.print("[yellow]Dry run mode - PR not actually created[/yellow]")

        # AI metadata
        ai_metadata = solution.get("ai_metadata", {})
        if ai_metadata:
            console.print(f"[dim]AI Model: {ai_metadata.get('model', 'unknown')}, Tokens: {ai_metadata.get('tokens_used', 0)}[/dim]")

    else:
        console.print(f"[yellow]PR generation status: {status}[/yellow]")


def display_batch_scan_results(results: Dict[str, Any]) -> None:
    """Display batch scan results."""
    if "error" in results:
        console.print(f"[red]✗[/red] Batch scan failed: {results['error']}")
        return

    status = results.get("status", "unknown")
    summary = results.get("summary", {})

    if status == "completed":
        console.print(Panel(f"[bold green]Batch Scan Completed[/bold green]", border_style="green"))

        # Summary statistics
        console.print(f"[bold]Total Repositories:[/bold] {summary.get('total_repositories', 0)}")
        console.print(f"[bold]Successful Scans:[/bold] {summary.get('successful_scans', 0)}")
        console.print(f"[bold]Failed Scans:[/bold] {summary.get('failed_scans', 0)}")
        console.print(f"[bold]Success Rate:[/bold] {summary.get('success_rate', 0):.1f}%")
        console.print(f"[bold]Total Opportunities:[/bold] {summary.get('total_opportunities', 0)}")
        console.print(f"[bold]Average Health Score:[/bold] {summary.get('avg_health_score', 0)}/100")
        console.print(f"[bold]Duration:[/bold] {summary.get('duration_seconds', 0):.1f} seconds")

        # Priority distribution
        priority_dist = results.get("priority_distribution", {})
        if priority_dist:
            console.print("\n[bold]Priority Distribution:[/bold]")
            console.print(f"  High Priority: {priority_dist.get('high_priority', 0)}")
            console.print(f"  Medium Priority: {priority_dist.get('medium_priority', 0)}")
            console.print(f"  Low Priority: {priority_dist.get('low_priority', 0)}")

        # Top repositories by health score
        detailed_results = results.get("detailed_results", {})
        successful_repos = [
            (repo, data) for repo, data in detailed_results.items()
            if data.get("status") == "success" and "analysis" in data
        ]

        if successful_repos:
            # Sort by health score
            successful_repos.sort(
                key=lambda x: x[1]["analysis"].get("health_score", 0),
                reverse=True
            )

            console.print("\n[bold]Top Repositories by Health Score:[/bold]")
            for i, (repo, data) in enumerate(successful_repos[:5], 1):
                health_score = data["analysis"].get("health_score", 0)
                opportunities = len(data.get("opportunities", []))
                console.print(f"  {i}. {repo} - Score: {health_score}/100, Opportunities: {opportunities}")

        # Failed repositories
        failed_repos = [
            (repo, data) for repo, data in detailed_results.items()
            if data.get("status") == "failed"
        ]

        if failed_repos:
            console.print(f"\n[bold red]Failed Repositories ({len(failed_repos)}):[/bold red]")
            for repo, data in failed_repos[:3]:  # Show first 3 failures
                error = data.get("error", "Unknown error")
                console.print(f"  • {repo}: {error}")

            if len(failed_repos) > 3:
                console.print(f"  ... and {len(failed_repos) - 3} more failures")

    else:
        console.print(f"[yellow]Batch scan status: {status}[/yellow]")


def display_advanced_metrics_results(results: Dict[str, Any]) -> None:
    """Display advanced metrics results."""
    if "error" in results:
        console.print(f"[red]✗[/red] Advanced metrics analysis failed: {results['error']}")
        return

    overall_score = results.get("overall_score", 0)
    dimension_scores = results.get("dimension_scores", {})

    console.print(Panel(f"[bold]Advanced Health Analysis[/bold]", border_style="blue"))
    console.print(f"[bold]Overall Health Score:[/bold] {overall_score}/100")

    # Dimension scores
    console.print("\n[bold]Dimension Scores:[/bold]")
    for dimension, score in dimension_scores.items():
        color = "green" if score >= 70 else "yellow" if score >= 50 else "red"
        console.print(f"  • {dimension.title()}: [{color}]{score:.1f}/100[/{color}]")

    # Recommendations
    recommendations = results.get("recommendations", [])
    if recommendations:
        console.print("\n[bold]Recommendations:[/bold]")
        for rec in recommendations:
            console.print(f"  • {rec}")


def display_trends_analysis_results(results: Dict[str, Any]) -> None:
    """Display trends analysis results."""
    if "error" in results:
        console.print(f"[red]✗[/red] Trends analysis failed: {results['error']}")
        return

    console.print(Panel(f"[bold]Contribution Trends Analysis[/bold]", border_style="blue"))

    trends = results.get("trends", {})
    for trend_type, trend_data in trends.items():
        console.print(f"\n[bold]{trend_type.title()} Trends:[/bold]")
        console.print(f"  Direction: {trend_data.get('direction', 'unknown')}")
        console.print(f"  Strength: {trend_data.get('strength', 'unknown')}")


def display_benchmark_results(results: Dict[str, Any]) -> None:
    """Display benchmark results."""
    if "error" in results:
        console.print(f"[red]✗[/red] Benchmarking failed: {results['error']}")
        return

    console.print(Panel(f"[bold]Repository Benchmarking[/bold]", border_style="blue"))

    target_repo = results.get("target_repository", "unknown")
    benchmarks = results.get("benchmarks", {})

    console.print(f"[bold]Target Repository:[/bold] {target_repo}")
    console.print(f"[bold]Comparison Repositories:[/bold] {len(results.get('comparison_repositories', []))}")

    if benchmarks:
        console.print("\n[bold]Benchmark Results:[/bold]")
        for metric, percentile in benchmarks.items():
            console.print(f"  • {metric}: {percentile}th percentile")


def display_comprehensive_report(results: Dict[str, Any]) -> None:
    """Display comprehensive report results."""
    if "error" in results:
        console.print(f"[red]✗[/red] Report generation failed: {results['error']}")
        return

    console.print(Panel(f"[bold]Comprehensive Repository Report[/bold]", border_style="blue"))

    # Executive summary
    exec_summary = results.get("executive_summary", {})
    if exec_summary:
        console.print(f"[bold]Health Level:[/bold] {exec_summary.get('overall_health_level', 'unknown')}")
        console.print(f"[bold]Overall Score:[/bold] {exec_summary.get('overall_score', 0)}/100")
        console.print(f"[bold]Description:[/bold] {exec_summary.get('health_description', 'No description')}")

        strengths = exec_summary.get("key_strengths", [])
        if strengths:
            console.print(f"[bold]Key Strengths:[/bold] {', '.join(strengths)}")

        weaknesses = exec_summary.get("key_weaknesses", [])
        if weaknesses:
            console.print(f"[bold]Key Weaknesses:[/bold] {', '.join(weaknesses)}")


def save_results_to_file(results: Dict[str, Any], filename: str) -> None:
    """Save results to a file."""
    output_path = Path(filename)

    # Add timestamp to results
    results["export_time"] = datetime.now().isoformat()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
