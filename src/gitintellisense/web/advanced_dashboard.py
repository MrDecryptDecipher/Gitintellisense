"""
Advanced Blockchain Contribution Dashboard

Enterprise-grade web dashboard that extends the existing Gitintellisense system
with real-time analytics, advanced visualizations, and comprehensive monitoring.

This module provides:
- Real-time WebSocket connections for live updates
- Advanced data visualization with interactive charts
- Comprehensive API middleware for GitHub integration
- Database integration for persistent tracking
- Advanced authentication and security measures
- Scalable microservices architecture
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

import aiohttp
from aiohttp import web, WSMsgType
from aiohttp_cors import setup as cors_setup, ResourceOptions
import aiohttp_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
import aioredis
import motor.motor_asyncio
from cryptography import fernet

from ..core.analyzer import RepositoryAnalyzer
from ..analysis.repository import RepositoryIntelligence
from ..analysis.opportunities import OpportunityDetector
from ..generation.pr_generator import PRGenerator
from ..ml.models import ContributionSuccessPredictor, OpportunityScorer
from ..automation.continuous_contributor import ContinuousContributor
from ..analytics.advanced_metrics import AdvancedMetricsEngine
from ..utils.config import Config, get_config
from ..utils.logging import get_logger
from ..utils.database import DatabaseManager


class AdvancedBlockchainDashboard:
    """
    Advanced blockchain contribution dashboard with enterprise features.
    
    Features:
    - Real-time WebSocket connections for live updates
    - Advanced analytics and metrics visualization
    - Comprehensive GitHub API integration
    - Machine learning-powered insights
    - Scalable microservices architecture
    - Advanced security and authentication
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the advanced dashboard."""
        self.config = config or get_config()
        self.logger = get_logger("advanced_dashboard")
        
        # Initialize core components
        self.analyzer = RepositoryAnalyzer(self.config)
        self.repo_intelligence = RepositoryIntelligence(self.config)
        self.opportunity_detector = OpportunityDetector(self.config)
        self.pr_generator = PRGenerator(self.config)
        self.success_predictor = ContributionSuccessPredictor(self.config)
        self.opportunity_scorer = OpportunityScorer(self.config)
        self.continuous_contributor = ContinuousContributor(self.config)
        self.metrics_engine = AdvancedMetricsEngine(self.config)
        self.database_manager = DatabaseManager(self.config)
        
        # Web application components
        self.app = None
        self.redis_pool = None
        self.mongo_client = None
        self.websocket_connections: Set[web.WebSocketResponse] = set()
        
        # Dashboard state
        self.dashboard_state = {
            'active_analyses': {},
            'real_time_metrics': {},
            'connected_clients': 0,
            'last_update': None,
        }
        
        # Blockchain ecosystems to monitor
        self.blockchain_ecosystems = [
            'ethereum', 'bitcoin', 'solana', 'polkadot', 'cosmos',
            'near', 'algorand', 'cardano', 'avalanche', 'polygon',
            'binance-smart-chain', 'fantom', 'arbitrum', 'optimism',
            'defi', 'nft', 'dao', 'gaming', 'infrastructure'
        ]
        
        # Target repositories for advanced monitoring
        self.target_repositories = [
            'ethereum/go-ethereum', 'ethereum/solidity', 'bitcoin/bitcoin',
            'solana-labs/solana', 'paritytech/substrate', 'cosmos/cosmos-sdk',
            'near/nearcore', 'algorand/go-algorand', 'input-output-hk/cardano-node',
            'ava-labs/avalanchego', '0xPolygon/polygon-edge', 'fantom-foundation/go-opera',
            'offchainlabs/arbitrum', 'ethereum-optimism/optimism', 'Uniswap/v3-core',
            'aave/aave-v3-core', 'compound-finance/compound-protocol', 'makerdao/dss',
            'curvefi/curve-contract', 'balancer/balancer-v2-monorepo', 'foundry-rs/foundry',
            'chainlink/chainlink', 'OpenZeppelin/openzeppelin-contracts'
        ]
    
    async def initialize(self) -> None:
        """Initialize the dashboard application and dependencies."""
        try:
            self.logger.info("Initializing Advanced Blockchain Dashboard")
            
            # Initialize Redis connection
            self.redis_pool = await aioredis.create_redis_pool(
                'redis://localhost:6379',
                encoding='utf-8',
                minsize=5,
                maxsize=20
            )
            
            # Initialize MongoDB connection
            self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
                'mongodb://localhost:27017'
            )
            self.mongo_db = self.mongo_client.blockchain_dashboard
            
            # Initialize web application
            await self._setup_web_application()
            
            # Initialize database collections
            await self._setup_database_collections()
            
            # Start background tasks
            await self._start_background_tasks()
            
            self.logger.info("Advanced Blockchain Dashboard initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize dashboard: {e}")
            raise
    
    async def _setup_web_application(self) -> None:
        """Setup the web application with middleware and routes."""
        # Create application
        self.app = web.Application()
        
        # Setup session middleware with encryption
        secret_key = fernet.Fernet.generate_key()
        aiohttp_session.setup(
            self.app, 
            EncryptedCookieStorage(secret_key, max_age=86400)  # 24 hours
        )
        
        # Setup CORS
        cors = cors_setup(self.app, defaults={
            "*": ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add middleware
        self.app.middlewares.append(self._auth_middleware)
        self.app.middlewares.append(self._rate_limit_middleware)
        self.app.middlewares.append(self._logging_middleware)
        self.app.middlewares.append(self._error_handler_middleware)
        
        # Setup routes
        await self._setup_routes()
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def _setup_routes(self) -> None:
        """Setup API routes and WebSocket endpoints."""
        # Health and status endpoints
        self.app.router.add_get('/api/health', self._health_check)
        self.app.router.add_get('/api/status', self._status_check)
        
        # Dashboard API endpoints
        self.app.router.add_get('/api/dashboard/overview', self._dashboard_overview)
        self.app.router.add_get('/api/dashboard/metrics', self._dashboard_metrics)
        self.app.router.add_get('/api/dashboard/analytics', self._dashboard_analytics)
        
        # Repository endpoints
        self.app.router.add_get('/api/repositories', self._list_repositories)
        self.app.router.add_get('/api/repositories/{repo_id}', self._get_repository)
        self.app.router.add_post('/api/repositories/{repo_id}/analyze', self._analyze_repository)
        
        # Contribution endpoints
        self.app.router.add_get('/api/contributions', self._list_contributions)
        self.app.router.add_get('/api/contributions/{contrib_id}', self._get_contribution)
        self.app.router.add_post('/api/contributions', self._create_contribution)
        
        # Analytics endpoints
        self.app.router.add_get('/api/analytics/trends', self._analytics_trends)
        self.app.router.add_get('/api/analytics/predictions', self._analytics_predictions)
        self.app.router.add_get('/api/analytics/insights', self._analytics_insights)
        
        # Machine Learning endpoints
        self.app.router.add_post('/api/ml/predict-success', self._predict_success)
        self.app.router.add_post('/api/ml/score-opportunity', self._score_opportunity)
        self.app.router.add_get('/api/ml/model-metrics', self._ml_model_metrics)
        
        # Automation endpoints
        self.app.router.add_get('/api/automation/status', self._automation_status)
        self.app.router.add_post('/api/automation/start', self._start_automation)
        self.app.router.add_post('/api/automation/stop', self._stop_automation)
        
        # WebSocket endpoint for real-time updates
        self.app.router.add_get('/ws', self._websocket_handler)
        
        # Static file serving for frontend
        self.app.router.add_static('/', path=str(Path(__file__).parent / 'static'), name='static')
    
    async def _setup_database_collections(self) -> None:
        """Setup MongoDB collections with proper indexes."""
        try:
            # Repositories collection
            repos_collection = self.mongo_db.repositories
            await repos_collection.create_index([
                ('full_name', 1),
                ('ecosystem', 1),
                ('stars', -1),
                ('last_analyzed', -1)
            ])
            
            # Contributions collection
            contribs_collection = self.mongo_db.contributions
            await contribs_collection.create_index([
                ('repository', 1),
                ('state', 1),
                ('created_at', -1),
                ('quality_score', -1)
            ])
            
            # Analytics collection
            analytics_collection = self.mongo_db.analytics
            await analytics_collection.create_index([
                ('timestamp', -1),
                ('metric_type', 1),
                ('repository', 1)
            ])
            
            # Opportunities collection
            opportunities_collection = self.mongo_db.opportunities
            await opportunities_collection.create_index([
                ('repository', 1),
                ('score', -1),
                ('difficulty', 1),
                ('created_at', -1)
            ])
            
            self.logger.info("Database collections and indexes created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup database collections: {e}")
            raise
    
    async def _start_background_tasks(self) -> None:
        """Start background tasks for data collection and processing."""
        try:
            # Start real-time metrics collection
            asyncio.create_task(self._collect_real_time_metrics())
            
            # Start repository monitoring
            asyncio.create_task(self._monitor_repositories())
            
            # Start opportunity detection
            asyncio.create_task(self._detect_opportunities())
            
            # Start analytics processing
            asyncio.create_task(self._process_analytics())
            
            # Start WebSocket heartbeat
            asyncio.create_task(self._websocket_heartbeat())
            
            self.logger.info("Background tasks started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start background tasks: {e}")
            raise
    
    async def _collect_real_time_metrics(self) -> None:
        """Collect real-time metrics for the dashboard."""
        while True:
            try:
                # Collect current metrics
                metrics = await self.metrics_engine.calculate_real_time_metrics()
                
                # Update dashboard state
                self.dashboard_state['real_time_metrics'] = metrics
                self.dashboard_state['last_update'] = datetime.now().isoformat()
                
                # Broadcast to WebSocket clients
                await self._broadcast_to_websockets({
                    'type': 'metrics_update',
                    'data': metrics,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Store in Redis for caching
                await self.redis_pool.setex(
                    'dashboard:real_time_metrics',
                    300,  # 5 minutes TTL
                    json.dumps(metrics, default=str)
                )
                
                # Wait before next collection
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error collecting real-time metrics: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _monitor_repositories(self) -> None:
        """Monitor target repositories for changes and opportunities."""
        while True:
            try:
                for repo_name in self.target_repositories:
                    try:
                        # Analyze repository
                        analysis = await self.analyzer.analyze_repository_quick(repo_name)
                        
                        # Store analysis results
                        await self._store_repository_analysis(repo_name, analysis)
                        
                        # Check for new opportunities
                        opportunities = await self.opportunity_detector.detect_opportunities(
                            repo_name, analysis
                        )
                        
                        if opportunities:
                            await self._store_opportunities(repo_name, opportunities)
                            
                            # Broadcast new opportunities
                            await self._broadcast_to_websockets({
                                'type': 'new_opportunities',
                                'repository': repo_name,
                                'opportunities': opportunities,
                                'timestamp': datetime.now().isoformat()
                            })
                        
                        # Rate limiting
                        await asyncio.sleep(10)
                        
                    except Exception as e:
                        self.logger.error(f"Error monitoring repository {repo_name}: {e}")
                        continue
                
                # Wait before next monitoring cycle
                await asyncio.sleep(300)  # 5 minutes between full cycles
                
            except Exception as e:
                self.logger.error(f"Error in repository monitoring: {e}")
                await asyncio.sleep(600)  # Wait longer on error

    # API Handler Methods
    async def _health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0',
            'service': 'advanced-blockchain-dashboard',
            'components': {
                'redis': await self._check_redis_health(),
                'mongodb': await self._check_mongodb_health(),
                'github_api': await self._check_github_api_health(),
                'ml_models': await self._check_ml_models_health(),
            },
            'metrics': {
                'active_connections': len(self.websocket_connections),
                'active_analyses': len(self.dashboard_state['active_analyses']),
                'uptime_seconds': time.time() - self.dashboard_state.get('start_time', time.time()),
            }
        }

        # Determine overall health
        component_health = list(health_status['components'].values())
        overall_healthy = all(component_health)

        status_code = 200 if overall_healthy else 503
        health_status['status'] = 'healthy' if overall_healthy else 'degraded'

        return web.json_response(health_status, status=status_code)

    async def _status_check(self, request: web.Request) -> web.Response:
        """Detailed status endpoint."""
        status = {
            'dashboard_state': self.dashboard_state,
            'target_repositories': len(self.target_repositories),
            'blockchain_ecosystems': self.blockchain_ecosystems,
            'active_background_tasks': await self._get_active_tasks_count(),
            'cache_stats': await self._get_cache_stats(),
            'database_stats': await self._get_database_stats(),
        }

        return web.json_response(status)

    async def _dashboard_overview(self, request: web.Request) -> web.Response:
        """Dashboard overview with key metrics."""
        try:
            # Get cached metrics or calculate fresh
            cached_overview = await self.redis_pool.get('dashboard:overview')

            if cached_overview:
                overview = json.loads(cached_overview)
            else:
                overview = await self._calculate_dashboard_overview()
                await self.redis_pool.setex(
                    'dashboard:overview',
                    180,  # 3 minutes cache
                    json.dumps(overview, default=str)
                )

            return web.json_response({
                'success': True,
                'data': overview,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            self.logger.error(f"Error getting dashboard overview: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def _dashboard_metrics(self, request: web.Request) -> web.Response:
        """Real-time dashboard metrics."""
        try:
            metrics = self.dashboard_state.get('real_time_metrics', {})

            # Add additional computed metrics
            enhanced_metrics = {
                **metrics,
                'performance_indicators': await self._calculate_performance_indicators(),
                'ecosystem_health': await self._calculate_ecosystem_health(),
                'contribution_velocity': await self._calculate_contribution_velocity(),
                'quality_trends': await self._calculate_quality_trends(),
            }

            return web.json_response({
                'success': True,
                'data': enhanced_metrics,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            self.logger.error(f"Error getting dashboard metrics: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def _dashboard_analytics(self, request: web.Request) -> web.Response:
        """Advanced analytics and insights."""
        try:
            # Get query parameters
            timeframe = request.query.get('timeframe', '30d')
            ecosystem = request.query.get('ecosystem', 'all')

            # Calculate analytics
            analytics = await self.metrics_engine.calculate_advanced_analytics(
                timeframe=timeframe,
                ecosystem=ecosystem
            )

            # Add ML-powered insights
            insights = await self._generate_ml_insights(analytics)

            # Add predictive analytics
            predictions = await self._generate_predictions(analytics)

            response_data = {
                'analytics': analytics,
                'insights': insights,
                'predictions': predictions,
                'metadata': {
                    'timeframe': timeframe,
                    'ecosystem': ecosystem,
                    'generated_at': datetime.now().isoformat()
                }
            }

            return web.json_response({
                'success': True,
                'data': response_data,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            self.logger.error(f"Error getting dashboard analytics: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def _list_repositories(self, request: web.Request) -> web.Response:
        """List monitored repositories with filtering."""
        try:
            # Get query parameters
            ecosystem = request.query.get('ecosystem')
            category = request.query.get('category')
            sort_by = request.query.get('sort_by', 'stars')
            limit = int(request.query.get('limit', 50))
            offset = int(request.query.get('offset', 0))

            # Build query
            query = {}
            if ecosystem:
                query['ecosystem'] = ecosystem
            if category:
                query['category'] = category

            # Get repositories from database
            repositories = await self.mongo_db.repositories.find(query)\
                .sort(sort_by, -1)\
                .skip(offset)\
                .limit(limit)\
                .to_list(length=limit)

            # Get total count
            total_count = await self.mongo_db.repositories.count_documents(query)

            return web.json_response({
                'success': True,
                'data': repositories,
                'meta': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
            })

        except Exception as e:
            self.logger.error(f"Error listing repositories: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def _analyze_repository(self, request: web.Request) -> web.Response:
        """Trigger repository analysis."""
        try:
            repo_id = request.match_info['repo_id']

            # Get analysis options from request body
            data = await request.json() if request.content_type == 'application/json' else {}
            deep_analysis = data.get('deep_analysis', False)
            include_opportunities = data.get('include_opportunities', True)

            # Start analysis (async)
            analysis_id = f"analysis_{repo_id}_{int(time.time())}"
            self.dashboard_state['active_analyses'][analysis_id] = {
                'repository': repo_id,
                'started_at': datetime.now().isoformat(),
                'status': 'running'
            }

            # Run analysis in background
            asyncio.create_task(self._run_repository_analysis(
                analysis_id, repo_id, deep_analysis, include_opportunities
            ))

            return web.json_response({
                'success': True,
                'data': {
                    'analysis_id': analysis_id,
                    'status': 'started',
                    'repository': repo_id
                }
            })

        except Exception as e:
            self.logger.error(f"Error starting repository analysis: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def _websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """WebSocket handler for real-time updates."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # Add to active connections
        self.websocket_connections.add(ws)
        self.dashboard_state['connected_clients'] = len(self.websocket_connections)

        self.logger.info(f"WebSocket client connected. Total connections: {len(self.websocket_connections)}")

        try:
            # Send initial state
            await ws.send_str(json.dumps({
                'type': 'connection_established',
                'data': {
                    'dashboard_state': self.dashboard_state,
                    'real_time_metrics': self.dashboard_state.get('real_time_metrics', {}),
                },
                'timestamp': datetime.now().isoformat()
            }))

            # Handle incoming messages
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_websocket_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            'type': 'error',
                            'message': 'Invalid JSON format'
                        }))
                elif msg.type == WSMsgType.ERROR:
                    self.logger.error(f'WebSocket error: {ws.exception()}')
                    break

        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
        finally:
            # Remove from active connections
            self.websocket_connections.discard(ws)
            self.dashboard_state['connected_clients'] = len(self.websocket_connections)
            self.logger.info(f"WebSocket client disconnected. Total connections: {len(self.websocket_connections)}")

        return ws

    async def _handle_websocket_message(self, ws: web.WebSocketResponse, data: Dict[str, Any]) -> None:
        """Handle incoming WebSocket messages."""
        try:
            message_type = data.get('type')

            if message_type == 'subscribe_repository':
                # Subscribe to repository updates
                repo_name = data.get('repository')
                if repo_name:
                    # Add subscription logic here
                    await ws.send_str(json.dumps({
                        'type': 'subscription_confirmed',
                        'repository': repo_name,
                        'timestamp': datetime.now().isoformat()
                    }))

            elif message_type == 'request_analysis':
                # Request repository analysis
                repo_name = data.get('repository')
                if repo_name:
                    analysis_id = f"ws_analysis_{repo_name}_{int(time.time())}"
                    asyncio.create_task(self._run_repository_analysis(
                        analysis_id, repo_name, False, True
                    ))

                    await ws.send_str(json.dumps({
                        'type': 'analysis_started',
                        'analysis_id': analysis_id,
                        'repository': repo_name,
                        'timestamp': datetime.now().isoformat()
                    }))

            elif message_type == 'ping':
                # Respond to ping with pong
                await ws.send_str(json.dumps({
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                }))

        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {e}")
            await ws.send_str(json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def _broadcast_to_websockets(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected WebSocket clients."""
        if not self.websocket_connections:
            return

        message_str = json.dumps(message, default=str)

        # Send to all connections, remove closed ones
        closed_connections = set()

        for ws in self.websocket_connections:
            try:
                if ws.closed:
                    closed_connections.add(ws)
                else:
                    await ws.send_str(message_str)
            except Exception as e:
                self.logger.error(f"Error broadcasting to WebSocket: {e}")
                closed_connections.add(ws)

        # Remove closed connections
        self.websocket_connections -= closed_connections
        self.dashboard_state['connected_clients'] = len(self.websocket_connections)

    async def _websocket_heartbeat(self) -> None:
        """Send periodic heartbeat to WebSocket clients."""
        while True:
            try:
                if self.websocket_connections:
                    await self._broadcast_to_websockets({
                        'type': 'heartbeat',
                        'timestamp': datetime.now().isoformat(),
                        'connected_clients': len(self.websocket_connections)
                    })

                await asyncio.sleep(30)  # Heartbeat every 30 seconds

            except Exception as e:
                self.logger.error(f"Error in WebSocket heartbeat: {e}")
                await asyncio.sleep(60)

    # Utility Methods
    async def _check_redis_health(self) -> bool:
        """Check Redis connection health."""
        try:
            await self.redis_pool.ping()
            return True
        except:
            return False

    async def _check_mongodb_health(self) -> bool:
        """Check MongoDB connection health."""
        try:
            await self.mongo_client.admin.command('ping')
            return True
        except:
            return False

    async def _check_github_api_health(self) -> bool:
        """Check GitHub API health."""
        try:
            # Simple API call to check connectivity
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.github.com/rate_limit') as response:
                    return response.status == 200
        except:
            return False

    async def _check_ml_models_health(self) -> bool:
        """Check ML models health."""
        try:
            # Test model prediction
            test_result = await self.success_predictor.predict_success({
                'repository': 'test/repo',
                'contribution_type': 'feature',
                'complexity': 'medium'
            })
            return 'error' not in test_result
        except:
            return False

    async def start_server(self, host: str = '0.0.0.0', port: int = 1201) -> None:
        """Start the dashboard server."""
        try:
            await self.initialize()

            # Record start time
            self.dashboard_state['start_time'] = time.time()

            self.logger.info(f"🚀 Starting Advanced Blockchain Dashboard on {host}:{port}")
            self.logger.info(f"📊 Monitoring {len(self.target_repositories)} repositories")
            self.logger.info(f"🌐 Tracking {len(self.blockchain_ecosystems)} blockchain ecosystems")
            self.logger.info(f"🔗 WebSocket endpoint: ws://{host}:{port}/ws")
            self.logger.info(f"📡 API endpoint: http://{host}:{port}/api")

            # Start the web server
            runner = web.AppRunner(self.app)
            await runner.setup()

            site = web.TCPSite(runner, host, port)
            await site.start()

            self.logger.info("✅ Advanced Blockchain Dashboard started successfully")

            # Keep the server running
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour

        except Exception as e:
            self.logger.error(f"Failed to start dashboard server: {e}")
            raise

    async def shutdown(self) -> None:
        """Gracefully shutdown the dashboard."""
        try:
            self.logger.info("Shutting down Advanced Blockchain Dashboard...")

            # Close WebSocket connections
            for ws in self.websocket_connections:
                await ws.close()

            # Close Redis connection
            if self.redis_pool:
                self.redis_pool.close()
                await self.redis_pool.wait_closed()

            # Close MongoDB connection
            if self.mongo_client:
                self.mongo_client.close()

            self.logger.info("Advanced Blockchain Dashboard shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


# Factory function for easy deployment
async def create_advanced_dashboard(config: Optional[Config] = None) -> AdvancedBlockchainDashboard:
    """Create and initialize an advanced blockchain dashboard instance."""
    dashboard = AdvancedBlockchainDashboard(config)
    await dashboard.initialize()
    return dashboard


# CLI entry point
async def main():
    """Main entry point for running the dashboard."""
    import argparse

    parser = argparse.ArgumentParser(description='Advanced Blockchain Contribution Dashboard')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=1201, help='Port to bind to')
    parser.add_argument('--config', help='Path to configuration file')

    args = parser.parse_args()

    # Load configuration
    config = get_config()
    if args.config:
        config.load_from_file(args.config)

    # Create and start dashboard
    dashboard = AdvancedBlockchainDashboard(config)

    try:
        await dashboard.start_server(args.host, args.port)
    except KeyboardInterrupt:
        await dashboard.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
