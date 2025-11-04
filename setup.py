#!/usr/bin/env python3
"""
Setup script for GitHub Repository Scanner and Automated Contribution System
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="gitintellisense",
    version="1.0.0",
    author="The Augster",
    author_email="augster@example.com",
    description="Sophisticated GitHub Repository Scanner and Automated Contribution System",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/gitintellisense",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.11",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "isort>=5.13.0",
            "flake8>=6.1.0",
            "mypy>=1.8.0",
            "pre-commit>=3.6.0",
        ],
        "docs": [
            "sphinx>=7.2.0",
            "sphinx-rtd-theme>=2.0.0",
        ],
        "security": [
            "bandit>=1.7.5",
            "safety>=2.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "gitintellisense=gitintellisense.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "gitintellisense": [
            "templates/*.j2",
            "config/*.yaml",
            "data/*.json",
        ],
    },
    zip_safe=False,
    keywords=[
        "github",
        "repository",
        "analysis",
        "ai",
        "automation",
        "contribution",
        "blockchain",
        "bitcoin",
        "code-analysis",
        "machine-learning",
    ],
    project_urls={
        "Bug Reports": "https://github.com/yourusername/gitintellisense/issues",
        "Source": "https://github.com/yourusername/gitintellisense",
        "Documentation": "https://gitintellisense.readthedocs.io/",
    },
)
