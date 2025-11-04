"""
Database management for the GitHub Repository Scanner and Automated Contribution System.

This module provides database management capabilities for storing analysis results,
tracking contributions, and maintaining system metrics.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .config import Config, get_config
from .logging import get_logger

Base = declarative_base()


class RepositoryAnalysis(Base):
    """Table for storing repository analysis results."""
    
    __tablename__ = "repository_analyses"
    
    id = Column(Integer, primary_key=True)
    repository_name = Column(String(255), nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False)
    analysis_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    analysis_data = Column(JSON, nullable=False)
    health_score = Column(Float)
    activity_level = Column(String(50))
    maturity = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContributionOpportunity(Base):
    """Table for storing detected contribution opportunities."""
    
    __tablename__ = "contribution_opportunities"
    
    id = Column(Integer, primary_key=True)
    repository_name = Column(String(255), nullable=False, index=True)
    opportunity_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    score = Column(Float, nullable=False)
    complexity = Column(String(50))
    estimated_effort = Column(String(100))
    skills_required = Column(JSON)
    issue_number = Column(Integer)
    url = Column(String(500))
    status = Column(String(50), default="detected")
    detection_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContributionAttempt(Base):
    """Table for tracking contribution attempts."""
    
    __tablename__ = "contribution_attempts"
    
    id = Column(Integer, primary_key=True)
    opportunity_id = Column(Integer, nullable=False)
    repository_name = Column(String(255), nullable=False, index=True)
    pr_number = Column(Integer)
    pr_url = Column(String(500))
    status = Column(String(50), nullable=False)  # created, merged, closed, rejected
    created_time = Column(DateTime, nullable=False)
    merged_time = Column(DateTime)
    closed_time = Column(DateTime)
    feedback = Column(Text)
    lessons_learned = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemMetrics(Base):
    """Table for storing system performance metrics."""
    
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(50))
    repository_name = Column(String(255))
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    extra_metadata = Column(JSON)


class AIAnalysis(Base):
    """Table for storing AI analysis results."""
    
    __tablename__ = "ai_analyses"
    
    id = Column(Integer, primary_key=True)
    repository_name = Column(String(255), nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False)
    model_used = Column(String(100), nullable=False)
    tokens_used = Column(Integer)
    analysis_duration = Column(Float)
    analysis_result = Column(JSON, nullable=False)
    analysis_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class DatabaseManager:
    """
    Database manager for the GitHub Repository Scanner system.
    
    Provides high-level database operations for storing and retrieving
    analysis results, opportunities, and system metrics.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize database manager."""
        self.config = config or get_config()
        self.logger = get_logger("database_manager")
        
        # Create engine
        self.engine = create_engine(
            self.config.database.url,
            pool_size=self.config.database.pool_size,
            max_overflow=self.config.database.max_overflow,
            echo=self.config.database.echo,
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        self.create_tables()
    
    def create_tables(self) -> None:
        """Create database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            self.logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to create database tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    def store_repository_analysis(
        self, 
        repository_name: str,
        analysis_type: str,
        analysis_data: Dict[str, Any]
    ) -> int:
        """
        Store repository analysis results.
        
        Args:
            repository_name: Repository name
            analysis_type: Type of analysis performed
            analysis_data: Analysis results
        
        Returns:
            ID of the stored analysis
        """
        session = self.get_session()
        try:
            # Extract key metrics
            basic_info = analysis_data.get("repository_intelligence", {}).get("basic_info", {})
            
            analysis = RepositoryAnalysis(
                repository_name=repository_name,
                analysis_type=analysis_type,
                analysis_data=analysis_data,
                health_score=basic_info.get("health_score"),
                activity_level=basic_info.get("activity_level"),
                maturity=basic_info.get("maturity"),
            )
            
            session.add(analysis)
            session.commit()
            
            analysis_id = analysis.id
            self.logger.info(f"Stored analysis for {repository_name}", analysis_id=analysis_id)
            
            return analysis_id
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to store repository analysis: {e}")
            raise
        finally:
            session.close()
    
    def store_opportunities(
        self, 
        repository_name: str,
        opportunities: List[Dict[str, Any]]
    ) -> List[int]:
        """
        Store detected contribution opportunities.
        
        Args:
            repository_name: Repository name
            opportunities: List of detected opportunities
        
        Returns:
            List of opportunity IDs
        """
        session = self.get_session()
        try:
            opportunity_ids = []
            
            for opp_data in opportunities:
                opportunity = ContributionOpportunity(
                    repository_name=repository_name,
                    opportunity_type=opp_data.get("type", "unknown"),
                    title=opp_data.get("title", ""),
                    description=opp_data.get("description", ""),
                    score=opp_data.get("score", 0.0),
                    complexity=opp_data.get("complexity"),
                    estimated_effort=opp_data.get("estimated_effort"),
                    skills_required=opp_data.get("skills_required", []),
                    issue_number=opp_data.get("issue_number"),
                    url=opp_data.get("url"),
                )
                
                session.add(opportunity)
                session.flush()  # Get the ID
                opportunity_ids.append(opportunity.id)
            
            session.commit()
            
            self.logger.info(
                f"Stored {len(opportunities)} opportunities for {repository_name}",
                opportunity_ids=opportunity_ids
            )
            
            return opportunity_ids
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to store opportunities: {e}")
            raise
        finally:
            session.close()
    
    def store_contribution_attempt(
        self,
        opportunity_id: int,
        repository_name: str,
        status: str,
        pr_number: Optional[int] = None,
        pr_url: Optional[str] = None,
        feedback: Optional[str] = None
    ) -> int:
        """
        Store contribution attempt.
        
        Args:
            opportunity_id: ID of the opportunity
            repository_name: Repository name
            status: Status of the contribution
            pr_number: Pull request number
            pr_url: Pull request URL
            feedback: Feedback received
        
        Returns:
            ID of the stored attempt
        """
        session = self.get_session()
        try:
            attempt = ContributionAttempt(
                opportunity_id=opportunity_id,
                repository_name=repository_name,
                pr_number=pr_number,
                pr_url=pr_url,
                status=status,
                created_time=datetime.utcnow(),
                feedback=feedback,
            )
            
            session.add(attempt)
            session.commit()
            
            attempt_id = attempt.id
            self.logger.info(
                f"Stored contribution attempt for {repository_name}",
                attempt_id=attempt_id,
                opportunity_id=opportunity_id,
                status=status
            )
            
            return attempt_id
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to store contribution attempt: {e}")
            raise
        finally:
            session.close()
    
    def store_ai_analysis(
        self,
        repository_name: str,
        analysis_type: str,
        model_used: str,
        tokens_used: int,
        analysis_duration: float,
        analysis_result: Dict[str, Any]
    ) -> int:
        """
        Store AI analysis results.
        
        Args:
            repository_name: Repository name
            analysis_type: Type of AI analysis
            model_used: AI model used
            tokens_used: Number of tokens consumed
            analysis_duration: Duration of analysis
            analysis_result: Analysis results
        
        Returns:
            ID of the stored analysis
        """
        session = self.get_session()
        try:
            ai_analysis = AIAnalysis(
                repository_name=repository_name,
                analysis_type=analysis_type,
                model_used=model_used,
                tokens_used=tokens_used,
                analysis_duration=analysis_duration,
                analysis_result=analysis_result,
            )
            
            session.add(ai_analysis)
            session.commit()
            
            analysis_id = ai_analysis.id
            self.logger.info(
                f"Stored AI analysis for {repository_name}",
                analysis_id=analysis_id,
                model=model_used,
                tokens=tokens_used
            )
            
            return analysis_id
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to store AI analysis: {e}")
            raise
        finally:
            session.close()
    
    def store_metric(
        self,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        repository_name: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Store system metric.

        Args:
            metric_name: Name of the metric
            metric_value: Value of the metric
            metric_unit: Unit of measurement
            repository_name: Associated repository
            extra_metadata: Additional metadata

        Returns:
            ID of the stored metric
        """
        session = self.get_session()
        try:
            metric = SystemMetrics(
                metric_name=metric_name,
                metric_value=metric_value,
                metric_unit=metric_unit,
                repository_name=repository_name,
                extra_metadata=extra_metadata,
            )
            
            session.add(metric)
            session.commit()
            
            return metric.id
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to store metric: {e}")
            raise
        finally:
            session.close()
    
    def get_repository_analyses(
        self, 
        repository_name: str,
        analysis_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get repository analyses."""
        session = self.get_session()
        try:
            query = session.query(RepositoryAnalysis).filter(
                RepositoryAnalysis.repository_name == repository_name
            )
            
            if analysis_type:
                query = query.filter(RepositoryAnalysis.analysis_type == analysis_type)
            
            analyses = query.order_by(RepositoryAnalysis.analysis_time.desc()).limit(limit).all()
            
            return [
                {
                    "id": analysis.id,
                    "analysis_type": analysis.analysis_type,
                    "analysis_time": analysis.analysis_time.isoformat(),
                    "analysis_data": analysis.analysis_data,
                    "health_score": analysis.health_score,
                    "activity_level": analysis.activity_level,
                    "maturity": analysis.maturity,
                }
                for analysis in analyses
            ]
            
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get repository analyses: {e}")
            return []
        finally:
            session.close()
    
    def get_opportunities(
        self,
        repository_name: str,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get contribution opportunities."""
        session = self.get_session()
        try:
            query = session.query(ContributionOpportunity).filter(
                ContributionOpportunity.repository_name == repository_name
            )
            
            if status:
                query = query.filter(ContributionOpportunity.status == status)
            
            opportunities = query.order_by(ContributionOpportunity.score.desc()).limit(limit).all()
            
            return [
                {
                    "id": opp.id,
                    "type": opp.opportunity_type,
                    "title": opp.title,
                    "description": opp.description,
                    "score": opp.score,
                    "complexity": opp.complexity,
                    "estimated_effort": opp.estimated_effort,
                    "skills_required": opp.skills_required,
                    "issue_number": opp.issue_number,
                    "url": opp.url,
                    "status": opp.status,
                    "detection_time": opp.detection_time.isoformat(),
                }
                for opp in opportunities
            ]
            
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get opportunities: {e}")
            return []
        finally:
            session.close()
    
    def get_contribution_stats(self, repository_name: Optional[str] = None) -> Dict[str, Any]:
        """Get contribution statistics."""
        session = self.get_session()
        try:
            query = session.query(ContributionAttempt)
            
            if repository_name:
                query = query.filter(ContributionAttempt.repository_name == repository_name)
            
            attempts = query.all()
            
            total_attempts = len(attempts)
            merged_attempts = len([a for a in attempts if a.status == "merged"])
            closed_attempts = len([a for a in attempts if a.status == "closed"])
            
            return {
                "total_attempts": total_attempts,
                "merged_attempts": merged_attempts,
                "closed_attempts": closed_attempts,
                "success_rate": (merged_attempts / total_attempts * 100) if total_attempts > 0 else 0,
                "repositories_contributed": len(set(a.repository_name for a in attempts)),
            }
            
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get contribution stats: {e}")
            return {}
        finally:
            session.close()
    
    def close(self) -> None:
        """Close database connections."""
        self.engine.dispose()
        self.logger.info("Database connections closed")
