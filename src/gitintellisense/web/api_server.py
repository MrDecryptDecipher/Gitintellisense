"""
FastAPI web server for GitIntellisense dashboard.

Provides REST API endpoints for the React dashboard to interact
with the GitIntellisense system.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from ..core.analyzer import RepositoryAnalyzer
from ..analysis.opportunities import OpportunityDetector
from ..generation.pr_generator import PRGenerator
from ..utils.config import Config, get_config
from ..utils.logging import get_logger
from ..utils.database import DatabaseManager


# Pydantic models for API requests/responses
class AnalyzeRepositoryRequest(BaseModel):
    repository: str
    force_refresh: bool = False


class PRGenerationRequest(BaseModel):
    repository: str
    opportunity_id: Optional[int] = None
    type: Optional[str] = None
    issue_number: Optional[int] = None
    dry_run: bool = True


class UpdateContributionRequest(BaseModel):
    status: str
    notes: Optional[str] = None


class DashboardStats(BaseModel):
    total_analyses: int
    total_opportunities: int
    total_contributions: int
    success_rate: float
    active_repositories: int


class RecentActivity(BaseModel):
    id: str
    type: str
    repository: str
    description: str
    timestamp: str
    status: str


class APIServer:
    """FastAPI server for GitIntellisense dashboard."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize API server."""
        self.config = config or get_config()
        self.logger = get_logger("api_server")
        
        # Initialize components
        self.db = DatabaseManager(config)
        self.analyzer = RepositoryAnalyzer(config)
        self.opportunity_detector = OpportunityDetector(config)
        self.pr_generator = PRGenerator(config)
        
        # Create FastAPI app
        self.app = FastAPI(
            title="GitIntellisense API",
            description="REST API for GitHub Repository Scanner and Automated Contribution System",
            version="1.0.0",
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React dev server
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # WebSocket connections for real-time updates
        self.websocket_connections: List[WebSocket] = []
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes."""
        
        # Dashboard endpoints
        @self.app.get("/api/dashboard/stats", response_model=DashboardStats)
        async def get_dashboard_stats():
            """Get dashboard statistics."""
            try:
                analyses = self.db.get_repository_analyses(limit=1000)
                opportunities = self.db.get_opportunities(limit=1000)
                contributions = self.db.get_contribution_attempts(limit=1000)
                
                # Calculate success rate
                successful_contributions = len([c for c in contributions if c.get("status") == "merged"])
                success_rate = (successful_contributions / len(contributions) * 100) if contributions else 0
                
                # Count active repositories (analyzed in last 30 days)
                recent_date = datetime.now() - timedelta(days=30)
                active_repos = len(set(
                    a["repository"] for a in analyses 
                    if datetime.fromisoformat(a["analysis_date"]) > recent_date
                ))
                
                return DashboardStats(
                    total_analyses=len(analyses),
                    total_opportunities=len(opportunities),
                    total_contributions=len(contributions),
                    success_rate=round(success_rate, 1),
                    active_repositories=active_repos,
                )
                
            except Exception as e:
                self.logger.error(f"Failed to get dashboard stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/dashboard/activity", response_model=List[RecentActivity])
        async def get_recent_activity():
            """Get recent activity."""
            try:
                activities = []
                
                # Get recent analyses
                analyses = self.db.get_repository_analyses(limit=5)
                for analysis in analyses:
                    activities.append(RecentActivity(
                        id=f"analysis_{analysis['id']}",
                        type="analysis",
                        repository=analysis["repository"],
                        description=f"Repository analysis completed (Score: {analysis['health_score']})",
                        timestamp=analysis["analysis_date"],
                        status="success",
                    ))
                
                # Get recent opportunities
                opportunities = self.db.get_opportunities(limit=5)
                for opp in opportunities:
                    activities.append(RecentActivity(
                        id=f"opportunity_{opp['id']}",
                        type="opportunity",
                        repository=opp["repository"],
                        description=f"Found {opp['type']} opportunity: {opp['title']}",
                        timestamp=opp["created_at"],
                        status="success",
                    ))
                
                # Get recent contributions
                contributions = self.db.get_contribution_attempts(limit=5)
                for contrib in contributions:
                    activities.append(RecentActivity(
                        id=f"contribution_{contrib['id']}",
                        type="contribution",
                        repository=contrib["repository"],
                        description=f"PR #{contrib.get('pr_number', 'N/A')} {contrib['status']}",
                        timestamp=contrib["created_at"],
                        status=contrib["status"],
                    ))
                
                # Sort by timestamp (most recent first)
                activities.sort(key=lambda x: x.timestamp, reverse=True)
                
                return activities[:10]  # Return top 10
                
            except Exception as e:
                self.logger.error(f"Failed to get recent activity: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/pr-analysis")
        async def get_pr_analysis():
            """Get PR success analysis and recommendations."""
            try:
                # Real PR analysis data for MrDecryptDecipher
                analysis = {
                    "total_prs": 17,
                    "merged_prs": 0,
                    "open_prs": 4,
                    "closed_prs": 13,
                    "success_rate": 0.0,
                    "failure_patterns": {
                        "spam_content": 5,
                        "generic_templates": 8,
                        "missing_requirements": 3,
                        "no_code_implementation": 8,
                        "wrong_targeting": 5
                    },
                    "recommendations": [
                        "🛑 STOP submitting generic templates",
                        "📋 READ contribution guidelines FIRST",
                        "💻 Include actual code implementation",
                        "🎯 Target specific issues, not generic improvements",
                        "✅ Start with 'good first issue' labels"
                    ],
                    "next_steps": [
                        "Choose ONE repository to focus on",
                        "Study contribution guidelines thoroughly",
                        "Find a genuine 'good first issue'",
                        "Create small, focused PR with actual code",
                        "Build reputation gradually"
                    ],
                    "critical_issues": [
                        "0% success rate indicates fundamental problems",
                        "Multiple PRs flagged as spam",
                        "No actual code implementations",
                        "Generic copy-paste approach"
                    ]
                }

                return analysis

            except Exception as e:
                self.logger.error(f"Failed to get PR analysis: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/analytics/data")
        async def get_analytics_data(period: str = "7d"):
            """Get analytics data for charts."""
            try:
                # Generate mock data for now
                # In production, this would query actual database metrics
                data = []
                days = 7 if period == "7d" else 30

                for i in range(days):
                    date = datetime.now() - timedelta(days=days-1-i)
                    data.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "analyses": max(0, 5 + (i % 3) - 1),
                        "opportunities": max(0, 15 + (i % 5) - 2),
                        "contributions": max(0, 3 + (i % 2)),
                    })
                
                return {"data": data, "status": 200}
                
            except Exception as e:
                self.logger.error(f"Failed to get analytics data: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Repository analysis endpoints
        @self.app.post("/api/analysis/analyze")
        async def analyze_repository(request: AnalyzeRepositoryRequest, background_tasks: BackgroundTasks):
            """Analyze a repository."""
            try:
                # Start analysis in background
                background_tasks.add_task(self._analyze_repository_background, request.repository)
                
                return {
                    "status": "started",
                    "message": f"Analysis started for {request.repository}",
                    "repository": request.repository,
                }
                
            except Exception as e:
                self.logger.error(f"Failed to start repository analysis: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/analysis/list")
        async def get_repository_analyses(limit: int = 50):
            """Get repository analyses."""
            try:
                analyses = self.db.get_repository_analyses(limit=limit)
                return {"data": analyses, "status": 200}
                
            except Exception as e:
                self.logger.error(f"Failed to get repository analyses: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/analysis/{analysis_id}")
        async def get_repository_analysis(analysis_id: int):
            """Get specific repository analysis."""
            try:
                analyses = self.db.get_repository_analyses(limit=1000)
                analysis = next((a for a in analyses if a["id"] == analysis_id), None)
                
                if not analysis:
                    raise HTTPException(status_code=404, detail="Analysis not found")
                
                return {"data": analysis, "status": 200}
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Failed to get repository analysis: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Opportunities endpoints
        @self.app.get("/api/opportunities")
        async def get_opportunities(repository: Optional[str] = None, limit: int = 50):
            """Get contribution opportunities."""
            try:
                opportunities = self.db.get_opportunities(repository=repository, limit=limit)
                return {"data": opportunities, "status": 200}
                
            except Exception as e:
                self.logger.error(f"Failed to get opportunities: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/opportunities/{opportunity_id}")
        async def get_opportunity(opportunity_id: int):
            """Get specific opportunity."""
            try:
                opportunities = self.db.get_opportunities(limit=1000)
                opportunity = next((o for o in opportunities if o["id"] == opportunity_id), None)
                
                if not opportunity:
                    raise HTTPException(status_code=404, detail="Opportunity not found")
                
                return {"data": opportunity, "status": 200}
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Failed to get opportunity: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # PR Generation endpoints
        @self.app.post("/api/pr-generation/generate")
        async def generate_pr(request: PRGenerationRequest, background_tasks: BackgroundTasks):
            """Generate a pull request."""
            try:
                # Start PR generation in background
                background_tasks.add_task(self._generate_pr_background, request)
                
                return {
                    "status": "started",
                    "message": f"PR generation started for {request.repository}",
                    "dry_run": request.dry_run,
                }
                
            except Exception as e:
                self.logger.error(f"Failed to start PR generation: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # WebSocket endpoint for real-time updates
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
        
        # Health check endpoint
        @self.app.get("/api/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
            }
    
    async def _analyze_repository_background(self, repository: str):
        """Background task for repository analysis."""
        try:
            self.logger.info(f"Starting background analysis for {repository}")
            
            # Perform analysis
            result = await self.analyzer.analyze_repository(repository)
            
            # Broadcast update via WebSocket
            await self._broadcast_update({
                "type": "analysis_complete",
                "repository": repository,
                "result": result,
            })
            
        except Exception as e:
            self.logger.error(f"Background analysis failed for {repository}: {e}")
            await self._broadcast_update({
                "type": "analysis_failed",
                "repository": repository,
                "error": str(e),
            })
    
    async def _generate_pr_background(self, request: PRGenerationRequest):
        """Background task for PR generation."""
        try:
            self.logger.info(f"Starting background PR generation for {request.repository}")
            
            # Create opportunity object if needed
            if request.opportunity_id:
                opportunities = self.db.get_opportunities(limit=1000)
                opportunity = next((o for o in opportunities if o["id"] == request.opportunity_id), None)
                if not opportunity:
                    raise ValueError(f"Opportunity {request.opportunity_id} not found")
            else:
                # Create synthetic opportunity
                opportunity = {
                    "type": request.type or "bug_fix",
                    "title": f"Generated {request.type or 'fix'} for {request.repository}",
                    "description": f"Automated {request.type or 'fix'} contribution",
                    "issue_number": request.issue_number,
                }
            
            # Generate PR
            result = await self.pr_generator.generate_and_submit_pr(
                opportunity, 
                request.repository, 
                request.dry_run
            )
            
            # Broadcast update via WebSocket
            await self._broadcast_update({
                "type": "pr_generation_complete",
                "repository": request.repository,
                "result": result,
            })
            
        except Exception as e:
            self.logger.error(f"Background PR generation failed for {request.repository}: {e}")
            await self._broadcast_update({
                "type": "pr_generation_failed",
                "repository": request.repository,
                "error": str(e),
            })
    
    async def _broadcast_update(self, message: Dict[str, Any]):
        """Broadcast update to all WebSocket connections."""
        if not self.websocket_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = []
        
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(message_str)
            except Exception:
                disconnected.append(websocket)
        
        # Remove disconnected websockets
        for websocket in disconnected:
            self.websocket_connections.remove(websocket)
    
    def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
        """Run the API server."""
        self.logger.info(f"Starting API server on {host}:{port}")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            debug=debug,
            log_level="info" if not debug else "debug",
        )


def create_app(config: Optional[Config] = None) -> FastAPI:
    """Create FastAPI application."""
    server = APIServer(config)
    return server.app


if __name__ == "__main__":
    server = APIServer()
    server.run(debug=True)
