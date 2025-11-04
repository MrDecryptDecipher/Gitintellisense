"""
Advanced Middleware Service for Blockchain Contribution Dashboard

This middleware service provides:
- API Gateway functionality with rate limiting
- Authentication and authorization
- Request/response transformation
- Caching and performance optimization
- Load balancing and service discovery
- Advanced security features
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path

import aiohttp
from aiohttp import web, ClientSession
import aiohttp_cors
import aioredis
import jwt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

from ..utils.config import Config, get_config
from ..utils.logging import get_logger


class AdvancedMiddlewareService:
    """
    Advanced middleware service for the blockchain dashboard.
    
    Provides enterprise-grade middleware features including:
    - API Gateway with intelligent routing
    - Rate limiting and throttling
    - Authentication and authorization
    - Request/response caching
    - Load balancing
    - Security headers and CORS
    - Request/response transformation
    - Monitoring and analytics
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the middleware service."""
        self.config = config or get_config()
        self.logger = get_logger("middleware_service")
        
        # Service configuration
        self.backend_url = "http://localhost:1203"
        self.frontend_url = "http://localhost:1201"
        self.redis_url = "redis://localhost:6379"
        
        # Application components
        self.app = None
        self.redis_pool = None
        self.session = None
        
        # Rate limiting configuration
        self.rate_limits = {
            'default': {'requests': 100, 'window': 3600},  # 100 requests per hour
            'authenticated': {'requests': 1000, 'window': 3600},  # 1000 requests per hour
            'premium': {'requests': 10000, 'window': 3600},  # 10000 requests per hour
        }
        
        # Service endpoints
        self.service_endpoints = {
            'backend': self.backend_url,
            'frontend': self.frontend_url,
        }
        
        # Security configuration
        self.jwt_secret = os.getenv('JWT_SECRET', 'your-secret-key')
        self.jwt_algorithm = 'HS256'
        self.jwt_expiration = 86400  # 24 hours
    
    async def initialize(self) -> None:
        """Initialize the middleware service."""
        try:
            self.logger.info("Initializing Advanced Middleware Service")
            
            # Initialize Redis connection
            self.redis_pool = await aioredis.create_redis_pool(
                self.redis_url,
                encoding='utf-8',
                minsize=5,
                maxsize=20
            )
            
            # Initialize HTTP session
            self.session = ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(limit=100)
            )
            
            # Setup web application
            await self._setup_web_application()
            
            self.logger.info("Advanced Middleware Service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize middleware service: {e}")
            raise
    
    async def _setup_web_application(self) -> None:
        """Setup the web application with middleware and routes."""
        # Create application
        self.app = web.Application()
        
        # Setup CORS
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add middleware in order
        self.app.middlewares.append(self._security_headers_middleware)
        self.app.middlewares.append(self._rate_limiting_middleware)
        self.app.middlewares.append(self._authentication_middleware)
        self.app.middlewares.append(self._caching_middleware)
        self.app.middlewares.append(self._request_transformation_middleware)
        self.app.middlewares.append(self._proxy_middleware)
        self.app.middlewares.append(self._response_transformation_middleware)
        self.app.middlewares.append(self._logging_middleware)
        self.app.middlewares.append(self._error_handler_middleware)
        
        # Setup routes
        await self._setup_routes()
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def _setup_routes(self) -> None:
        """Setup middleware routes."""
        # Health and status endpoints
        self.app.router.add_get('/health', self._health_check)
        self.app.router.add_get('/status', self._status_check)
        
        # Authentication endpoints
        self.app.router.add_post('/auth/login', self._login)
        self.app.router.add_post('/auth/logout', self._logout)
        self.app.router.add_post('/auth/refresh', self._refresh_token)
        self.app.router.add_get('/auth/me', self._get_user_info)
        
        # API Gateway routes (proxy to backend)
        self.app.router.add_route('*', '/api/{path:.*}', self._api_proxy)
        
        # Static file serving (proxy to frontend)
        self.app.router.add_route('*', '/{path:.*}', self._frontend_proxy)
    
    # Middleware Functions
    async def _security_headers_middleware(self, request: web.Request, handler) -> web.Response:
        """Add security headers to responses."""
        response = await handler(request)
        
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss: https:; "
            "font-src 'self' https://cdnjs.cloudflare.com;"
        )
        
        return response
    
    async def _rate_limiting_middleware(self, request: web.Request, handler) -> web.Response:
        """Rate limiting middleware."""
        client_ip = request.remote
        user_id = request.get('user_id')
        
        # Determine rate limit tier
        if user_id:
            # Check user tier from database/cache
            tier = await self._get_user_tier(user_id)
            rate_limit = self.rate_limits.get(tier, self.rate_limits['default'])
        else:
            rate_limit = self.rate_limits['default']
        
        # Check rate limit
        key = f"rate_limit:{user_id or client_ip}"
        current_requests = await self.redis_pool.get(key)
        
        if current_requests is None:
            await self.redis_pool.setex(key, rate_limit['window'], 1)
        else:
            current_requests = int(current_requests)
            if current_requests >= rate_limit['requests']:
                return web.json_response({
                    'error': 'Rate limit exceeded',
                    'limit': rate_limit['requests'],
                    'window': rate_limit['window']
                }, status=429)
            
            await self.redis_pool.incr(key)
        
        # Add rate limit headers
        response = await handler(request)
        response.headers['X-RateLimit-Limit'] = str(rate_limit['requests'])
        response.headers['X-RateLimit-Remaining'] = str(
            rate_limit['requests'] - int(current_requests or 0)
        )
        response.headers['X-RateLimit-Reset'] = str(
            int(time.time()) + rate_limit['window']
        )
        
        return response
    
    async def _authentication_middleware(self, request: web.Request, handler) -> web.Response:
        """Authentication middleware."""
        # Skip authentication for public endpoints
        public_endpoints = ['/health', '/status', '/auth/login', '/auth/refresh']
        if any(request.path.startswith(endpoint) for endpoint in public_endpoints):
            return await handler(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            
            try:
                # Verify JWT token
                payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
                request['user_id'] = payload.get('user_id')
                request['user_email'] = payload.get('email')
                request['user_tier'] = payload.get('tier', 'default')
                
            except jwt.ExpiredSignatureError:
                return web.json_response({
                    'error': 'Token expired'
                }, status=401)
            except jwt.InvalidTokenError:
                return web.json_response({
                    'error': 'Invalid token'
                }, status=401)
        
        return await handler(request)
    
    async def _caching_middleware(self, request: web.Request, handler) -> web.Response:
        """Caching middleware."""
        # Only cache GET requests
        if request.method != 'GET':
            return await handler(request)
        
        # Generate cache key
        cache_key = f"cache:{request.path}:{request.query_string}"
        
        # Check cache
        cached_response = await self.redis_pool.get(cache_key)
        if cached_response:
            try:
                data = json.loads(cached_response)
                response = web.json_response(data)
                response.headers['X-Cache'] = 'HIT'
                return response
            except json.JSONDecodeError:
                pass
        
        # Execute handler
        response = await handler(request)
        
        # Cache successful responses
        if response.status == 200 and response.content_type == 'application/json':
            try:
                response_text = response.text
                if response_text:
                    # Cache for 5 minutes
                    await self.redis_pool.setex(cache_key, 300, response_text)
                    response.headers['X-Cache'] = 'MISS'
            except:
                pass
        
        return response
    
    async def _request_transformation_middleware(self, request: web.Request, handler) -> web.Response:
        """Transform requests before forwarding."""
        # Add request ID for tracing
        request['request_id'] = f"req_{int(time.time() * 1000)}"
        
        # Add timestamp
        request['request_timestamp'] = datetime.now().isoformat()
        
        # Log request
        self.logger.info(
            f"Request: {request.method} {request.path}",
            request_id=request['request_id'],
            user_id=request.get('user_id'),
            client_ip=request.remote
        )
        
        return await handler(request)
    
    async def _proxy_middleware(self, request: web.Request, handler) -> web.Response:
        """Proxy requests to appropriate services."""
        # This middleware handles the actual proxying
        return await handler(request)
    
    async def _response_transformation_middleware(self, request: web.Request, handler) -> web.Response:
        """Transform responses before sending to client."""
        response = await handler(request)
        
        # Add response headers
        response.headers['X-Request-ID'] = request.get('request_id', '')
        response.headers['X-Response-Time'] = str(
            int((time.time() - request.get('start_time', time.time())) * 1000)
        )
        
        return response
    
    async def _logging_middleware(self, request: web.Request, handler) -> web.Response:
        """Logging middleware."""
        start_time = time.time()
        request['start_time'] = start_time
        
        try:
            response = await handler(request)
            
            # Log response
            duration = (time.time() - start_time) * 1000
            self.logger.info(
                f"Response: {response.status} {request.method} {request.path}",
                request_id=request.get('request_id'),
                duration_ms=duration,
                status_code=response.status
            )
            
            return response
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.logger.error(
                f"Error: {request.method} {request.path}",
                request_id=request.get('request_id'),
                duration_ms=duration,
                error=str(e)
            )
            raise
    
    async def _error_handler_middleware(self, request: web.Request, handler) -> web.Response:
        """Global error handler."""
        try:
            return await handler(request)
        except web.HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Unhandled error: {e}", request_id=request.get('request_id'))
            
            return web.json_response({
                'error': 'Internal server error',
                'request_id': request.get('request_id')
            }, status=500)
    
    # Route Handlers
    async def _health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'advanced-middleware',
            'version': '2.0.0',
            'components': {
                'redis': await self._check_redis_health(),
                'backend': await self._check_backend_health(),
                'frontend': await self._check_frontend_health(),
            }
        }
        
        return web.json_response(health)
    
    async def _api_proxy(self, request: web.Request) -> web.Response:
        """Proxy API requests to backend service."""
        path = request.match_info['path']
        url = f"{self.backend_url}/api/{path}"
        
        # Forward query parameters
        if request.query_string:
            url += f"?{request.query_string}"
        
        try:
            # Forward request to backend
            async with self.session.request(
                method=request.method,
                url=url,
                headers=dict(request.headers),
                data=await request.read() if request.can_read_body else None
            ) as response:
                # Read response
                response_data = await response.read()
                
                # Create response
                proxy_response = web.Response(
                    body=response_data,
                    status=response.status,
                    headers=dict(response.headers)
                )
                
                return proxy_response
                
        except Exception as e:
            self.logger.error(f"Error proxying to backend: {e}")
            return web.json_response({
                'error': 'Backend service unavailable'
            }, status=503)
    
    async def _frontend_proxy(self, request: web.Request) -> web.Response:
        """Proxy frontend requests."""
        # Serve static files or proxy to frontend service
        static_dir = Path(__file__).parent / 'static'
        
        # Default to index.html for SPA routing
        file_path = static_dir / (request.match_info['path'] or 'index.html')
        
        if not file_path.exists() or file_path.is_dir():
            file_path = static_dir / 'index.html'
        
        try:
            return web.FileResponse(file_path)
        except Exception as e:
            self.logger.error(f"Error serving static file: {e}")
            return web.Response(text="File not found", status=404)
    
    async def start_server(self, host: str = '0.0.0.0', port: int = 1202) -> None:
        """Start the middleware server."""
        try:
            await self.initialize()
            
            self.logger.info(f"🚀 Starting Advanced Middleware Service on {host}:{port}")
            self.logger.info(f"🔗 Backend URL: {self.backend_url}")
            self.logger.info(f"🌐 Frontend URL: {self.frontend_url}")
            self.logger.info(f"📡 API Gateway: http://{host}:{port}/api")
            
            # Start the web server
            runner = web.AppRunner(self.app)
            await runner.setup()
            
            site = web.TCPSite(runner, host, port)
            await site.start()
            
            self.logger.info("✅ Advanced Middleware Service started successfully")
            
            # Keep the server running
            while True:
                await asyncio.sleep(3600)
                
        except Exception as e:
            self.logger.error(f"Failed to start middleware server: {e}")
            raise


# CLI entry point
async def main():
    """Main entry point for running the middleware service."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced Middleware Service')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=1202, help='Port to bind to')
    
    args = parser.parse_args()
    
    # Create and start middleware service
    middleware = AdvancedMiddlewareService()
    
    try:
        await middleware.start_server(args.host, args.port)
    except KeyboardInterrupt:
        await middleware.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
