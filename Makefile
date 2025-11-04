# GitHub Repository Scanner and Automated Contribution System
# Makefile for development and deployment automation

.PHONY: help install install-dev setup clean test test-cov lint format type-check security docs build deploy

# Default target
help:
	@echo "GitHub Repository Scanner and Automated Contribution System"
	@echo "Available targets:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  setup        - Complete development environment setup"
	@echo "  clean        - Clean build artifacts and cache"
	@echo "  test         - Run test suite"
	@echo "  test-cov     - Run tests with coverage report"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code with black and isort"
	@echo "  type-check   - Run type checking with mypy"
	@echo "  security     - Run security checks"
	@echo "  docs         - Build documentation"
	@echo "  build        - Build distribution packages"
	@echo "  deploy       - Deploy to production"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev,docs,security,performance]"
	pre-commit install

# Setup development environment
setup: install-dev
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file from template"; fi
	mkdir -p logs data backups
	@echo "Development environment setup complete!"
	@echo "Please edit .env file with your API keys and configuration"

# Cleanup targets
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Testing targets
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src/gitintellisense --cov-report=html --cov-report=term-missing

test-integration:
	pytest tests/ -m integration -v

test-unit:
	pytest tests/ -m unit -v

# Code quality targets
lint:
	flake8 src/ tests/
	bandit -r src/

format:
	black src/ tests/
	isort src/ tests/

type-check:
	mypy src/gitintellisense/

security:
	bandit -r src/
	safety check

# Quality check combination
check: lint type-check security test

# Documentation targets
docs:
	cd docs && make html

docs-serve:
	cd docs/_build/html && python -m http.server 8000

# Build targets
build: clean
	python -m build

build-wheel:
	python -m build --wheel

build-sdist:
	python -m build --sdist

# Development targets
dev-server:
	python -m gitintellisense serve --debug

dev-analyze:
	python -m gitintellisense analyze bitcoin/bitcoin --verbose

dev-monitor:
	python -m gitintellisense monitor --dashboard

# Database targets
db-init:
	python -m gitintellisense db init

db-migrate:
	python -m gitintellisense db migrate

db-upgrade:
	python -m gitintellisense db upgrade

db-reset:
	python -m gitintellisense db reset

# Deployment targets
deploy-staging:
	@echo "Deploying to staging environment..."
	# Add staging deployment commands here

deploy-production:
	@echo "Deploying to production environment..."
	# Add production deployment commands here

# Monitoring targets
logs:
	tail -f logs/gitintellisense.log

metrics:
	python -m gitintellisense metrics --dashboard

health:
	python -m gitintellisense health-check

# Backup targets
backup:
	python -m gitintellisense backup create

restore:
	python -m gitintellisense backup restore

# Performance targets
profile:
	python -m gitintellisense profile --output=profile.html

benchmark:
	python -m gitintellisense benchmark --iterations=100

# Git hooks
pre-commit: format lint type-check test

# CI/CD targets
ci: check test-cov security

# Release targets
release-patch:
	bump2version patch

release-minor:
	bump2version minor

release-major:
	bump2version major
