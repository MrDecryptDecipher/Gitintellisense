/**
 * PM2 Ecosystem Configuration for Advanced Blockchain Dashboard
 * 
 * This configuration manages three microservices:
 * - Frontend (Port 1201): React-based dashboard interface
 * - Middleware (Port 1202): API Gateway and authentication service
 * - Backend (Port 1203): Core data processing and WebSocket service
 */

module.exports = {
  apps: [
    {
      name: 'blockchain-dashboard-frontend',
      script: 'python',
      args: ['-m', 'http.server', '1201'],
      cwd: '/home/ubuntu/Sandeep/projects/Gitintellisense/src/gitintellisense/web/static',
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      max_memory_restart: '200M',
      env: {
        NODE_ENV: 'production',
        PORT: 1201,
        SERVICE_NAME: 'blockchain-dashboard-frontend'
      },
      error_file: '/home/ubuntu/Sandeep/projects/Gitintellisense/logs/frontend-error.log',
      out_file: '/home/ubuntu/Sandeep/projects/Gitintellisense/logs/frontend-out.log',
      log_file: '/home/ubuntu/Sandeep/projects/Gitintellisense/logs/frontend-combined.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 5000
    },
    {
      name: 'blockchain-dashboard-middleware',
      script: 'python',
      args: ['-m', 'gitintellisense.web.middleware_service', '--host', '0.0.0.0', '--port', '1202'],
      cwd: '/home/ubuntu/Sandeep/projects/Gitintellisense/src',
      instances: 2,
      exec_mode: 'cluster',
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        PORT: 1202,
        SERVICE_NAME: 'blockchain-dashboard-middleware',
        REDIS_URL: 'redis://localhost:6379',
        JWT_SECRET: 'your-super-secret-jwt-key-change-in-production',
        BACKEND_URL: 'http://localhost:1203',
        FRONTEND_URL: 'http://localhost:1201'
      },
      error_file: '/home/ubuntu/Sandeep/projects/Gitintellisense/logs/middleware-error.log',
      out_file: '/home/ubuntu/Sandeep/projects/Gitintellisense/logs/middleware-out.log',
      log_file: '/home/ubuntu/Sandeep/projects/Gitintellisense/logs/middleware-combined.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 5000
    },
    {
      name: 'blockchain-dashboard-backend',
      script: 'python',
      args: ['-m', 'gitintellisense.web.advanced_dashboard', '--host', '0.0.0.0', '--port', '1203'],
      cwd: '/home/ubuntu/Sandeep/projects/Gitintellisense/src',
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PORT: 1203,
        SERVICE_NAME: 'blockchain-dashboard-backend',
        MONGODB_URL: 'mongodb://localhost:27017/blockchain_dashboard',
        REDIS_URL: 'redis://localhost:6379',
        GITHUB_TOKEN: process.env.GITHUB_TOKEN,
        LOG_LEVEL: 'info',
        LOG_DIR: '/home/ubuntu/Sandeep/projects/Gitintellisense/logs'
      },
      error_file: '/home/ubuntu/Sandeep/projects/Gitintellisense/logs/backend-error.log',
      out_file: '/home/ubuntu/Sandeep/projects/Gitintellisense/logs/backend-out.log',
      log_file: '/home/ubuntu/Sandeep/projects/Gitintellisense/logs/backend-combined.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 5000
    }
  ],

  deploy: {
    production: {
      user: 'ubuntu',
      host: '3.111.22.56',
      ref: 'origin/main',
      repo: 'git@github.com:blockchain-dashboard/dashboard.git',
      path: '/home/ubuntu/Sandeep/projects/Gitintellisense',
      'pre-deploy-local': '',
      'post-deploy': 'npm install && pm2 reload ecosystem.config.js --env production',
      'pre-setup': ''
    }
  }
};
