"""
AI engine for advanced code analysis and contribution generation.

This module provides AI-powered analysis capabilities using OpenRouter's
Gemini 2.0 Flash Experimental model for sophisticated code understanding
and professional contribution generation.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import openai
from openai import AsyncOpenAI

from ..utils.config import Config, get_config
from ..utils.logging import get_logger


class AIEngine:
    """
    AI-powered analysis engine using OpenRouter's Gemini 2.0 Flash Experimental.
    
    Provides sophisticated code analysis, pattern recognition, and professional
    contribution generation capabilities.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize AI engine."""
        self.config = config or get_config()
        self.logger = get_logger("ai_engine")
        
        # Initialize OpenAI client configured for OpenRouter
        self.client = AsyncOpenAI(
            api_key=self.config.openrouter.api_key,
            base_url=self.config.openrouter.base_url,
        )
        
        # Rate limiting
        self.last_request_time = 0.0
        self.request_count = 0
        self.window_start = time.time()
    
    async def _rate_limit(self) -> None:
        """Apply rate limiting for AI requests."""
        current_time = time.time()
        
        # Reset window if needed (per minute)
        if current_time - self.window_start >= 60:
            self.request_count = 0
            self.window_start = current_time
        
        # Check if we've exceeded the per-minute limit
        if self.request_count >= self.config.openrouter.rate_limit_per_minute:
            sleep_time = 60 - (current_time - self.window_start)
            if sleep_time > 0:
                self.logger.info(f"Rate limit reached, sleeping for {sleep_time} seconds")
                await asyncio.sleep(sleep_time)
                self.request_count = 0
                self.window_start = time.time()
        
        self.request_count += 1
    
    async def _make_ai_request(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make an AI request with error handling and logging."""
        await self._rate_limit()
        
        # Use config defaults if not specified
        temperature = temperature or self.config.openrouter.temperature
        max_tokens = max_tokens or self.config.openrouter.max_tokens
        
        start_time = datetime.now()
        
        try:
            self.logger.ai_analysis_start(
                model=self.config.openrouter.model,
                prompt_length=sum(len(msg.get("content", "")) for msg in messages)
            )
            
            response = await self.client.chat.completions.create(
                model=self.config.openrouter.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=self.config.openrouter.top_p,
                frequency_penalty=self.config.openrouter.frequency_penalty,
                presence_penalty=self.config.openrouter.presence_penalty,
                **kwargs
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            self.logger.ai_analysis_complete(
                model=self.config.openrouter.model,
                tokens_used=tokens_used,
                duration=duration
            )
            
            return {
                "content": response.choices[0].message.content,
                "tokens_used": tokens_used,
                "model": self.config.openrouter.model,
                "duration": duration,
            }
            
        except Exception as e:
            self.logger.error(f"AI request failed", error=str(e))
            raise
    
    async def analyze_repository_for_opportunities(
        self,
        repo_analysis: Dict[str, Any],
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze repository data to identify contribution opportunities.

        Args:
            repo_analysis: Comprehensive repository analysis data
            focus_areas: Specific areas to focus on (e.g., ["testing", "documentation"])

        Returns:
            AI-generated opportunity analysis
        """
        self.logger.info("Analyzing repository for contribution opportunities")

        # Prepare analysis prompt
        prompt = self._create_opportunity_analysis_prompt(repo_analysis, focus_areas)

        messages = [
            {
                "role": "system",
                "content": self._get_opportunity_analysis_system_prompt()
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        try:
            response = await self._make_ai_request(messages)

            # Parse the AI response
            opportunities = self._parse_opportunity_response(response["content"])

            return {
                "opportunities": opportunities,
                "ai_metadata": {
                    "model": response["model"],
                    "tokens_used": response["tokens_used"],
                    "analysis_time": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            self.logger.error("Failed to analyze repository for opportunities", error=str(e))
            return {"error": str(e)}

    async def analyze_code_architecture(
        self,
        repo_name: str,
        code_files: List[Dict[str, Any]],
        language: str = "cpp"
    ) -> Dict[str, Any]:
        """
        Perform deep architectural analysis of codebase.

        Args:
            repo_name: Repository name
            code_files: List of code files with content
            language: Primary programming language

        Returns:
            Comprehensive architectural analysis
        """
        self.logger.info(f"Performing architectural analysis for {repo_name}")

        prompt = self._create_architecture_analysis_prompt(repo_name, code_files, language)

        messages = [
            {
                "role": "system",
                "content": self._get_architecture_analysis_system_prompt()
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        try:
            response = await self._make_ai_request(messages, max_tokens=4000)

            analysis = self._parse_architecture_response(response["content"])

            return {
                "architecture_analysis": analysis,
                "ai_metadata": {
                    "model": response["model"],
                    "tokens_used": response["tokens_used"],
                    "analysis_time": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            self.logger.error("Failed to analyze code architecture", error=str(e))
            return {"error": str(e)}

    async def analyze_security_vulnerabilities(
        self,
        code_files: List[Dict[str, Any]],
        language: str = "cpp"
    ) -> Dict[str, Any]:
        """
        Analyze code for security vulnerabilities and best practices.

        Args:
            code_files: List of code files with content
            language: Programming language

        Returns:
            Security vulnerability analysis
        """
        self.logger.info(f"Analyzing security vulnerabilities for {language}")

        prompt = self._create_security_analysis_prompt(code_files, language)

        messages = [
            {
                "role": "system",
                "content": self._get_security_analysis_system_prompt()
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        try:
            response = await self._make_ai_request(messages, max_tokens=3000)

            analysis = self._parse_security_response(response["content"])

            return {
                "security_analysis": analysis,
                "ai_metadata": {
                    "model": response["model"],
                    "tokens_used": response["tokens_used"],
                    "analysis_time": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            self.logger.error("Failed to analyze security vulnerabilities", error=str(e))
            return {"error": str(e)}

    async def analyze_performance_bottlenecks(
        self,
        code_files: List[Dict[str, Any]],
        language: str = "cpp"
    ) -> Dict[str, Any]:
        """
        Analyze code for performance bottlenecks and optimization opportunities.

        Args:
            code_files: List of code files with content
            language: Programming language

        Returns:
            Performance analysis with optimization suggestions
        """
        self.logger.info(f"Analyzing performance bottlenecks for {language}")

        prompt = self._create_performance_analysis_prompt(code_files, language)

        messages = [
            {
                "role": "system",
                "content": self._get_performance_analysis_system_prompt()
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        try:
            response = await self._make_ai_request(messages, max_tokens=3000)

            analysis = self._parse_performance_response(response["content"])

            return {
                "performance_analysis": analysis,
                "ai_metadata": {
                    "model": response["model"],
                    "tokens_used": response["tokens_used"],
                    "analysis_time": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            self.logger.error("Failed to analyze performance bottlenecks", error=str(e))
            return {"error": str(e)}
    
    async def analyze_code_quality(
        self, 
        code_samples: List[Dict[str, str]],
        language: str = "cpp"
    ) -> Dict[str, Any]:
        """
        Analyze code quality and suggest improvements.
        
        Args:
            code_samples: List of code samples with metadata
            language: Programming language
        
        Returns:
            AI-generated code quality analysis
        """
        self.logger.info(f"Analyzing code quality for {language}")
        
        prompt = self._create_code_quality_prompt(code_samples, language)
        
        messages = [
            {
                "role": "system",
                "content": self._get_code_quality_system_prompt()
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            response = await self._make_ai_request(messages)
            
            analysis = self._parse_code_quality_response(response["content"])
            
            return {
                "quality_analysis": analysis,
                "ai_metadata": {
                    "model": response["model"],
                    "tokens_used": response["tokens_used"],
                    "analysis_time": datetime.now().isoformat(),
                },
            }
            
        except Exception as e:
            self.logger.error("Failed to analyze code quality", error=str(e))
            return {"error": str(e)}
    
    async def generate_contribution_strategy(
        self, 
        opportunities: List[Dict[str, Any]],
        contributor_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a strategic contribution plan.
        
        Args:
            opportunities: List of identified opportunities
            contributor_profile: Contributor's skills and preferences
        
        Returns:
            AI-generated contribution strategy
        """
        self.logger.info("Generating contribution strategy")
        
        prompt = self._create_strategy_prompt(opportunities, contributor_profile)
        
        messages = [
            {
                "role": "system",
                "content": self._get_strategy_system_prompt()
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            response = await self._make_ai_request(messages)
            
            strategy = self._parse_strategy_response(response["content"])
            
            return {
                "strategy": strategy,
                "ai_metadata": {
                    "model": response["model"],
                    "tokens_used": response["tokens_used"],
                    "analysis_time": datetime.now().isoformat(),
                },
            }
            
        except Exception as e:
            self.logger.error("Failed to generate contribution strategy", error=str(e))
            return {"error": str(e)}
    
    def _get_opportunity_analysis_system_prompt(self) -> str:
        """Get system prompt for opportunity analysis."""
        return """You are an expert software engineer and open-source contributor with deep expertise in blockchain technology, particularly Bitcoin Core. Your task is to analyze repository data and identify meaningful contribution opportunities.

Focus on:
1. Technical opportunities that demonstrate deep understanding
2. Areas where contributions would provide genuine value
3. Opportunities suitable for different skill levels
4. Security, performance, and code quality improvements
5. Documentation and testing gaps

Provide specific, actionable recommendations with clear rationale for each opportunity. Consider the maintainer preferences and project culture when making recommendations.

Respond in JSON format with structured opportunity data."""
    
    def _get_code_quality_system_prompt(self) -> str:
        """Get system prompt for code quality analysis."""
        return """You are a senior software architect with expertise in code quality, security, and performance optimization. Analyze the provided code samples and identify specific improvement opportunities.

Focus on:
1. Code complexity and maintainability issues
2. Security vulnerabilities and best practices
3. Performance optimization opportunities
4. Testing gaps and edge cases
5. Documentation and code clarity improvements

Provide specific, actionable recommendations with code examples where appropriate. Consider industry best practices and the specific context of the codebase.

Respond in JSON format with structured analysis data."""
    
    def _get_strategy_system_prompt(self) -> str:
        """Get system prompt for strategy generation."""
        return """You are a strategic advisor for open-source contributions with deep understanding of project dynamics and contributor success patterns. Generate a comprehensive contribution strategy based on the identified opportunities and contributor profile.

Focus on:
1. Prioritizing opportunities based on impact and feasibility
2. Creating a logical progression of contributions
3. Building reputation and trust with maintainers
4. Maximizing learning and skill development
5. Ensuring sustainable contribution patterns

Provide a detailed, actionable strategy with timelines, milestones, and success metrics.

Respond in JSON format with structured strategy data."""

    def _get_architecture_analysis_system_prompt(self) -> str:
        """Get system prompt for architecture analysis."""
        return """You are a senior software architect with expertise in large-scale system design, code organization, and architectural patterns. Analyze the provided codebase for architectural quality, design patterns, and improvement opportunities.

Focus on:
1. Overall architectural patterns and design principles
2. Code organization and module structure
3. Dependency management and coupling analysis
4. Scalability and maintainability concerns
5. Design pattern usage and anti-patterns
6. Technical debt identification
7. Refactoring opportunities

Provide specific, actionable recommendations with clear rationale and implementation guidance.

Respond in JSON format with structured architectural analysis."""

    def _get_security_analysis_system_prompt(self) -> str:
        """Get system prompt for security analysis."""
        return """You are a cybersecurity expert specializing in secure coding practices and vulnerability assessment. Analyze the provided code for security vulnerabilities, potential attack vectors, and security best practices.

Focus on:
1. Common vulnerability patterns (OWASP Top 10)
2. Input validation and sanitization
3. Memory safety issues (buffer overflows, use-after-free)
4. Cryptographic implementation flaws
5. Authentication and authorization weaknesses
6. Race conditions and concurrency issues
7. Information disclosure risks

Provide specific vulnerability findings with severity ratings, exploitation scenarios, and remediation steps.

Respond in JSON format with structured security analysis."""

    def _get_performance_analysis_system_prompt(self) -> str:
        """Get system prompt for performance analysis."""
        return """You are a performance optimization expert with deep knowledge of algorithmic complexity, system performance, and optimization techniques. Analyze the provided code for performance bottlenecks and optimization opportunities.

Focus on:
1. Algorithmic complexity analysis (time and space)
2. Memory usage patterns and optimization
3. I/O operations and blocking calls
4. CPU-intensive operations and parallelization opportunities
5. Cache efficiency and data locality
6. Database query optimization
7. Network communication efficiency

Provide specific performance issues with impact assessment, optimization strategies, and expected improvements.

Respond in JSON format with structured performance analysis."""
    
    def _create_opportunity_analysis_prompt(
        self, 
        repo_analysis: Dict[str, Any], 
        focus_areas: Optional[List[str]]
    ) -> str:
        """Create prompt for opportunity analysis."""
        repo_name = repo_analysis.get("repository", "unknown")
        basic_info = repo_analysis.get("repository_intelligence", {}).get("basic_info", {})
        issues_prs = repo_analysis.get("repository_intelligence", {}).get("issues_prs", {})
        
        prompt = f"""Analyze the following repository data for {repo_name} and identify contribution opportunities:

REPOSITORY OVERVIEW:
- Health Score: {basic_info.get('health_score', 'unknown')}
- Activity Level: {basic_info.get('activity_level', 'unknown')}
- Maturity: {basic_info.get('maturity', 'unknown')}
- Stars: {basic_info.get('stars', 0)}
- Open Issues: {issues_prs.get('open_issues', {}).get('total', 0)}

GOOD FIRST ISSUES:
{json.dumps(issues_prs.get('good_first_issues', [])[:5], indent=2)}

RECENT ACTIVITY:
{json.dumps(repo_analysis.get('repository_intelligence', {}).get('activity', {}), indent=2)}
"""
        
        if focus_areas:
            prompt += f"\nFOCUS AREAS: {', '.join(focus_areas)}"
        
        prompt += """

Please identify and prioritize contribution opportunities, considering:
1. Technical complexity and required expertise
2. Potential impact on the project
3. Alignment with maintainer preferences
4. Learning opportunities for contributors
5. Likelihood of acceptance

Provide specific recommendations with clear rationale."""
        
        return prompt
    
    def _create_code_quality_prompt(
        self, 
        code_samples: List[Dict[str, str]], 
        language: str
    ) -> str:
        """Create prompt for code quality analysis."""
        prompt = f"Analyze the following {language} code samples for quality improvements:\n\n"
        
        for i, sample in enumerate(code_samples[:3]):  # Limit to 3 samples
            prompt += f"CODE SAMPLE {i+1}:\n"
            prompt += f"File: {sample.get('file', 'unknown')}\n"
            prompt += f"```{language}\n{sample.get('content', '')}\n```\n\n"
        
        prompt += """Please analyze for:
1. Code complexity and readability
2. Security vulnerabilities
3. Performance optimization opportunities
4. Testing coverage gaps
5. Documentation improvements
6. Best practice violations

Provide specific, actionable recommendations."""
        
        return prompt

    def _create_architecture_analysis_prompt(
        self,
        repo_name: str,
        code_files: List[Dict[str, Any]],
        language: str
    ) -> str:
        """Create prompt for architecture analysis."""
        prompt = f"Analyze the architectural quality of {repo_name} ({language} codebase):\n\n"

        for i, file_data in enumerate(code_files[:5]):  # Limit to 5 files
            prompt += f"FILE {i+1}: {file_data.get('path', 'unknown')}\n"
            prompt += f"```{language}\n{file_data.get('content', '')[:2000]}\n```\n\n"

        prompt += """Please analyze for:
1. Architectural patterns and design principles
2. Code organization and module structure
3. Dependency management and coupling
4. Scalability and maintainability
5. Design patterns and anti-patterns
6. Technical debt and refactoring opportunities

Provide specific recommendations with implementation guidance."""

        return prompt

    def _create_security_analysis_prompt(
        self,
        code_files: List[Dict[str, Any]],
        language: str
    ) -> str:
        """Create prompt for security analysis."""
        prompt = f"Analyze the following {language} code for security vulnerabilities:\n\n"

        for i, file_data in enumerate(code_files[:3]):  # Limit to 3 files
            prompt += f"FILE {i+1}: {file_data.get('path', 'unknown')}\n"
            prompt += f"```{language}\n{file_data.get('content', '')[:1500]}\n```\n\n"

        prompt += """Please analyze for:
1. Common vulnerabilities (OWASP Top 10)
2. Input validation and sanitization
3. Memory safety issues
4. Cryptographic implementation flaws
5. Authentication and authorization
6. Race conditions and concurrency
7. Information disclosure risks

Provide specific findings with severity ratings and remediation steps."""

        return prompt

    def _create_performance_analysis_prompt(
        self,
        code_files: List[Dict[str, Any]],
        language: str
    ) -> str:
        """Create prompt for performance analysis."""
        prompt = f"Analyze the following {language} code for performance bottlenecks:\n\n"

        for i, file_data in enumerate(code_files[:3]):  # Limit to 3 files
            prompt += f"FILE {i+1}: {file_data.get('path', 'unknown')}\n"
            prompt += f"```{language}\n{file_data.get('content', '')[:1500]}\n```\n\n"

        prompt += """Please analyze for:
1. Algorithmic complexity (time and space)
2. Memory usage patterns
3. I/O operations and blocking calls
4. CPU-intensive operations
5. Cache efficiency and data locality
6. Database query optimization
7. Network communication efficiency

Provide specific bottlenecks with optimization strategies and expected improvements."""

        return prompt
    
    def _create_strategy_prompt(
        self, 
        opportunities: List[Dict[str, Any]], 
        contributor_profile: Dict[str, Any]
    ) -> str:
        """Create prompt for strategy generation."""
        prompt = f"""Generate a contribution strategy based on:

IDENTIFIED OPPORTUNITIES:
{json.dumps(opportunities[:10], indent=2)}

CONTRIBUTOR PROFILE:
{json.dumps(contributor_profile, indent=2)}

Create a strategic plan that includes:
1. Prioritized list of opportunities
2. Recommended contribution sequence
3. Skill development pathway
4. Timeline and milestones
5. Success metrics
6. Risk mitigation strategies

Consider the contributor's current skills and the project's needs."""
        
        return prompt
    
    def _parse_opportunity_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse AI response for opportunities."""
        try:
            # Try to parse as JSON first
            if response.strip().startswith("{") or response.strip().startswith("["):
                return json.loads(response)
            
            # If not JSON, create structured response from text
            return [{"description": response, "type": "general", "priority": "medium"}]
            
        except json.JSONDecodeError:
            # Fallback to text parsing
            return [{"description": response, "type": "general", "priority": "medium"}]
    
    def _parse_code_quality_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response for code quality analysis."""
        try:
            if response.strip().startswith("{"):
                return json.loads(response)
            
            return {"analysis": response, "recommendations": []}
            
        except json.JSONDecodeError:
            return {"analysis": response, "recommendations": []}
    
    def _parse_strategy_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response for strategy."""
        try:
            if response.strip().startswith("{"):
                return json.loads(response)

            return {"strategy": response, "priorities": [], "timeline": "not_specified"}

        except json.JSONDecodeError:
            return {"strategy": response, "priorities": [], "timeline": "not_specified"}

    def _parse_architecture_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response for architecture analysis."""
        try:
            if response.strip().startswith("{"):
                return json.loads(response)

            return {
                "analysis": response,
                "patterns": [],
                "recommendations": [],
                "technical_debt": [],
                "quality_score": 0
            }

        except json.JSONDecodeError:
            return {
                "analysis": response,
                "patterns": [],
                "recommendations": [],
                "technical_debt": [],
                "quality_score": 0
            }

    def _parse_security_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response for security analysis."""
        try:
            if response.strip().startswith("{"):
                return json.loads(response)

            return {
                "analysis": response,
                "vulnerabilities": [],
                "risk_score": "unknown",
                "recommendations": []
            }

        except json.JSONDecodeError:
            return {
                "analysis": response,
                "vulnerabilities": [],
                "risk_score": "unknown",
                "recommendations": []
            }

    def _parse_performance_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response for performance analysis."""
        try:
            if response.strip().startswith("{"):
                return json.loads(response)

            return {
                "analysis": response,
                "bottlenecks": [],
                "optimizations": [],
                "performance_score": 0
            }

        except json.JSONDecodeError:
            return {
                "analysis": response,
                "bottlenecks": [],
                "optimizations": [],
                "performance_score": 0
            }
