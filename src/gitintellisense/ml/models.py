"""
Machine learning models for contribution success prediction and opportunity scoring.

This module provides advanced ML capabilities for:
- Predicting contribution success probability
- Scoring and ranking opportunities
- Learning from historical contribution data
- Optimizing recommendation algorithms
"""

import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib

from ..utils.config import Config, get_config
from ..utils.logging import get_logger
from ..utils.database import DatabaseManager


class ContributionSuccessPredictor:
    """
    Machine learning model for predicting contribution success probability.
    
    Uses historical contribution data to predict the likelihood of
    successful PR acceptance based on repository and contributor features.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize contribution success predictor."""
        self.config = config or get_config()
        self.logger = get_logger("ml_predictor")
        self.db = DatabaseManager(config)
        
        # Model components
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        self.scaler = StandardScaler()
        self.text_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.label_encoders = {}
        
        # Model metadata
        self.is_trained = False
        self.feature_names = []
        self.model_version = "1.0.0"
        self.last_training_date = None
        
        # Model storage path
        self.model_path = Path(self.config.data_dir) / "models"
        self.model_path.mkdir(exist_ok=True)
    
    def prepare_training_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare training data from historical contributions."""
        self.logger.info("Preparing training data for contribution success prediction")
        
        try:
            # Get historical contribution data
            contributions = self.db.get_contribution_attempts(limit=10000)
            analyses = self.db.get_repository_analyses(limit=10000)
            opportunities = self.db.get_opportunities(limit=10000)
            
            # Create training dataset
            training_data = []
            
            for contrib in contributions:
                # Find corresponding analysis and opportunity
                repo_analysis = next(
                    (a for a in analyses if a["repository"] == contrib["repository"]), 
                    None
                )
                opportunity = next(
                    (o for o in opportunities if o["id"] == contrib.get("opportunity_id")), 
                    None
                )
                
                if repo_analysis and opportunity:
                    # Create feature vector
                    features = self._extract_features(contrib, repo_analysis, opportunity)
                    
                    # Create target variable (1 for success, 0 for failure)
                    target = 1 if contrib["status"] in ["merged", "accepted"] else 0
                    
                    training_data.append({**features, "success": target})
            
            if not training_data:
                raise ValueError("No training data available")
            
            df = pd.DataFrame(training_data)
            
            # Separate features and target
            feature_columns = [col for col in df.columns if col != "success"]
            X = df[feature_columns]
            y = df["success"]
            
            self.feature_names = feature_columns
            
            return X, y
            
        except Exception as e:
            self.logger.error(f"Failed to prepare training data: {e}")
            raise
    
    def train_model(self, retrain: bool = False) -> Dict[str, Any]:
        """Train the contribution success prediction model."""
        self.logger.info("Training contribution success prediction model")
        
        try:
            # Check if model exists and is recent
            if not retrain and self._load_existing_model():
                return {"status": "loaded_existing", "model_version": self.model_version}
            
            # Prepare training data
            X, y = self.prepare_training_data()
            
            if len(X) < 50:
                self.logger.warning("Insufficient training data, using synthetic data augmentation")
                X, y = self._augment_training_data(X, y)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Preprocess features
            X_train_processed = self._preprocess_features(X_train, fit=True)
            X_test_processed = self._preprocess_features(X_test, fit=False)
            
            # Train model
            self.model.fit(X_train_processed, y_train)
            
            # Evaluate model
            y_pred = self.model.predict(X_test_processed)
            metrics = {
                "accuracy": accuracy_score(y_test, y_pred),
                "precision": precision_score(y_test, y_pred, average='weighted'),
                "recall": recall_score(y_test, y_pred, average='weighted'),
                "f1_score": f1_score(y_test, y_pred, average='weighted'),
            }
            
            # Cross-validation
            cv_scores = cross_val_score(self.model, X_train_processed, y_train, cv=5)
            metrics["cv_mean"] = cv_scores.mean()
            metrics["cv_std"] = cv_scores.std()
            
            # Update model metadata
            self.is_trained = True
            self.last_training_date = datetime.now()
            
            # Save model
            self._save_model()
            
            self.logger.info(f"Model training completed. Accuracy: {metrics['accuracy']:.3f}")
            
            return {
                "status": "trained",
                "metrics": metrics,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "model_version": self.model_version,
            }
            
        except Exception as e:
            self.logger.error(f"Model training failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def predict_success_probability(
        self, 
        repository: str,
        opportunity: Dict[str, Any],
        contributor_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Predict success probability for a contribution."""
        if not self.is_trained:
            if not self._load_existing_model():
                return {"error": "Model not trained"}
        
        try:
            # Get repository analysis
            analyses = self.db.get_repository_analyses(repository=repository, limit=1)
            if not analyses:
                return {"error": "Repository analysis not found"}
            
            repo_analysis = analyses[0]
            
            # Create synthetic contribution data
            contrib_data = {
                "repository": repository,
                "opportunity_id": opportunity.get("id"),
                "status": "pending",  # Placeholder
                "created_at": datetime.now().isoformat(),
            }
            
            # Extract features
            features = self._extract_features(contrib_data, repo_analysis, opportunity, contributor_profile)
            
            # Create feature vector
            feature_df = pd.DataFrame([features])
            feature_df = feature_df.reindex(columns=self.feature_names, fill_value=0)
            
            # Preprocess features
            features_processed = self._preprocess_features(feature_df, fit=False)
            
            # Predict probability
            probability = self.model.predict_proba(features_processed)[0][1]  # Probability of success
            
            # Get feature importance
            feature_importance = dict(zip(
                self.feature_names,
                self.model.feature_importances_
            ))
            
            return {
                "success_probability": float(probability),
                "confidence": "high" if abs(probability - 0.5) > 0.3 else "medium",
                "feature_importance": feature_importance,
                "model_version": self.model_version,
            }
            
        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            return {"error": str(e)}
    
    def _extract_features(
        self, 
        contribution: Dict[str, Any],
        repo_analysis: Dict[str, Any],
        opportunity: Dict[str, Any],
        contributor_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract features for ML model."""
        features = {}
        
        # Repository features
        features["repo_health_score"] = repo_analysis.get("health_score", 0)
        features["repo_good_first_issues"] = repo_analysis.get("good_first_issues", 0)
        features["repo_has_guidelines"] = int(repo_analysis.get("has_guidelines", False))
        
        # Activity level encoding
        activity_levels = {"low": 1, "moderate": 2, "active": 3, "very_active": 4}
        features["repo_activity_level"] = activity_levels.get(
            repo_analysis.get("activity_level", "low"), 1
        )
        
        # Difficulty encoding
        difficulty_levels = {"easy": 1, "medium": 2, "hard": 3}
        features["repo_difficulty"] = difficulty_levels.get(
            repo_analysis.get("contribution_difficulty", "medium"), 2
        )
        
        # Opportunity features
        features["opp_score"] = opportunity.get("score", 0)
        features["opp_complexity_easy"] = int(opportunity.get("complexity") == "easy")
        features["opp_complexity_medium"] = int(opportunity.get("complexity") == "medium")
        features["opp_complexity_hard"] = int(opportunity.get("complexity") == "hard")
        
        # Opportunity type features
        opp_type = opportunity.get("type", "unknown")
        features["opp_type_bug"] = int("bug" in opp_type.lower())
        features["opp_type_doc"] = int("doc" in opp_type.lower())
        features["opp_type_test"] = int("test" in opp_type.lower())
        features["opp_type_feature"] = int("feature" in opp_type.lower())
        
        # Skills required
        skills = opportunity.get("skills_required", [])
        features["skills_count"] = len(skills)
        features["has_beginner_skills"] = int(any(
            skill.lower() in ["documentation", "testing", "bug_fix"] 
            for skill in skills
        ))
        
        # Contributor features (if available)
        if contributor_profile:
            features["contributor_experience"] = contributor_profile.get("experience_years", 0)
            features["contributor_contributions"] = contributor_profile.get("total_contributions", 0)
            features["contributor_success_rate"] = contributor_profile.get("success_rate", 0.5)
        else:
            # Default values for new contributors
            features["contributor_experience"] = 0
            features["contributor_contributions"] = 0
            features["contributor_success_rate"] = 0.5
        
        # Temporal features
        created_at = contribution.get("created_at", datetime.now().isoformat())
        if isinstance(created_at, str):
            created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        else:
            created_date = created_at
        
        features["day_of_week"] = created_date.weekday()
        features["hour_of_day"] = created_date.hour
        features["is_weekend"] = int(created_date.weekday() >= 5)
        
        return features

    def _preprocess_features(self, X: pd.DataFrame, fit: bool = False) -> np.ndarray:
        """Preprocess features for model input."""
        # Handle missing values
        X_filled = X.fillna(0)

        # Scale numerical features
        if fit:
            X_scaled = self.scaler.fit_transform(X_filled)
        else:
            X_scaled = self.scaler.transform(X_filled)

        return X_scaled

    def _augment_training_data(self, X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
        """Augment training data with synthetic samples."""
        # Simple data augmentation by adding noise to existing samples
        augmented_X = []
        augmented_y = []

        for _ in range(100):  # Generate 100 synthetic samples
            # Randomly select a base sample
            idx = np.random.randint(0, len(X))
            base_sample = X.iloc[idx].copy()

            # Add small random noise
            for col in base_sample.index:
                if base_sample[col] != 0:  # Only add noise to non-zero values
                    noise = np.random.normal(0, 0.1 * abs(base_sample[col]))
                    base_sample[col] += noise

            augmented_X.append(base_sample)
            augmented_y.append(y.iloc[idx])

        # Combine original and augmented data
        X_combined = pd.concat([X] + augmented_X, ignore_index=True)
        y_combined = pd.concat([y, pd.Series(augmented_y)], ignore_index=True)

        return X_combined, y_combined

    def _save_model(self) -> None:
        """Save trained model to disk."""
        try:
            model_data = {
                "model": self.model,
                "scaler": self.scaler,
                "text_vectorizer": self.text_vectorizer,
                "label_encoders": self.label_encoders,
                "feature_names": self.feature_names,
                "model_version": self.model_version,
                "last_training_date": self.last_training_date.isoformat(),
                "is_trained": self.is_trained,
            }

            model_file = self.model_path / "contribution_success_model.pkl"
            joblib.dump(model_data, model_file)

            self.logger.info(f"Model saved to {model_file}")

        except Exception as e:
            self.logger.error(f"Failed to save model: {e}")

    def _load_existing_model(self) -> bool:
        """Load existing model from disk."""
        try:
            model_file = self.model_path / "contribution_success_model.pkl"

            if not model_file.exists():
                return False

            model_data = joblib.load(model_file)

            self.model = model_data["model"]
            self.scaler = model_data["scaler"]
            self.text_vectorizer = model_data["text_vectorizer"]
            self.label_encoders = model_data["label_encoders"]
            self.feature_names = model_data["feature_names"]
            self.model_version = model_data["model_version"]
            self.last_training_date = datetime.fromisoformat(model_data["last_training_date"])
            self.is_trained = model_data["is_trained"]

            # Check if model is recent (less than 30 days old)
            if (datetime.now() - self.last_training_date).days > 30:
                self.logger.info("Model is outdated, retraining recommended")
                return False

            self.logger.info(f"Loaded existing model (version {self.model_version})")
            return True

        except Exception as e:
            self.logger.warning(f"Failed to load existing model: {e}")
            return False


class OpportunityScorer:
    """
    Machine learning model for scoring and ranking contribution opportunities.

    Uses repository metrics, opportunity characteristics, and historical
    success data to score opportunities for optimal recommendation.
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize opportunity scorer."""
        self.config = config or get_config()
        self.logger = get_logger("ml_scorer")
        self.db = DatabaseManager(config)

        # Model components
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=6,
            random_state=42
        )
        self.scaler = StandardScaler()

        # Model metadata
        self.is_trained = False
        self.feature_names = []
        self.model_version = "1.0.0"

        # Model storage path
        self.model_path = Path(self.config.data_dir) / "models"
        self.model_path.mkdir(exist_ok=True)

    def train_scoring_model(self) -> Dict[str, Any]:
        """Train the opportunity scoring model."""
        self.logger.info("Training opportunity scoring model")

        try:
            # Prepare training data
            X, y = self._prepare_scoring_data()

            if len(X) < 30:
                self.logger.warning("Insufficient data for scoring model")
                return {"status": "insufficient_data"}

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Preprocess features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Train model
            self.model.fit(X_train_scaled, y_train)

            # Evaluate model
            train_score = self.model.score(X_train_scaled, y_train)
            test_score = self.model.score(X_test_scaled, y_test)

            self.is_trained = True
            self.feature_names = X.columns.tolist()

            # Save model
            self._save_scoring_model()

            return {
                "status": "trained",
                "train_score": train_score,
                "test_score": test_score,
                "training_samples": len(X_train),
            }

        except Exception as e:
            self.logger.error(f"Scoring model training failed: {e}")
            return {"status": "failed", "error": str(e)}

    def score_opportunity(self, opportunity: Dict[str, Any]) -> float:
        """Score a single opportunity."""
        if not self.is_trained:
            if not self._load_scoring_model():
                # Use rule-based scoring as fallback
                return self._rule_based_score(opportunity)

        try:
            # Extract features
            features = self._extract_scoring_features(opportunity)
            feature_df = pd.DataFrame([features])
            feature_df = feature_df.reindex(columns=self.feature_names, fill_value=0)

            # Scale features
            features_scaled = self.scaler.transform(feature_df)

            # Predict score
            score = self.model.predict(features_scaled)[0]

            # Normalize score to 0-100 range
            return max(0, min(100, score))

        except Exception as e:
            self.logger.warning(f"ML scoring failed, using rule-based fallback: {e}")
            return self._rule_based_score(opportunity)

    def rank_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank opportunities by predicted score."""
        scored_opportunities = []

        for opp in opportunities:
            score = self.score_opportunity(opp)
            opp_with_score = opp.copy()
            opp_with_score["ml_score"] = score
            scored_opportunities.append(opp_with_score)

        # Sort by score (descending)
        scored_opportunities.sort(key=lambda x: x["ml_score"], reverse=True)

        return scored_opportunities

    def _prepare_scoring_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare training data for scoring model."""
        opportunities = self.db.get_opportunities(limit=5000)
        contributions = self.db.get_contribution_attempts(limit=5000)

        training_data = []

        for opp in opportunities:
            # Find contributions for this opportunity
            opp_contributions = [
                c for c in contributions
                if c.get("opportunity_id") == opp["id"]
            ]

            # Calculate success metrics
            if opp_contributions:
                success_rate = len([c for c in opp_contributions if c["status"] in ["merged", "accepted"]]) / len(opp_contributions)
                avg_time_to_merge = 7  # Placeholder
            else:
                success_rate = 0.5  # Default
                avg_time_to_merge = 14  # Default

            # Calculate composite score
            composite_score = (
                opp.get("score", 50) * 0.4 +
                success_rate * 100 * 0.4 +
                max(0, 21 - avg_time_to_merge) * 2 * 0.2  # Faster merge = higher score
            )

            features = self._extract_scoring_features(opp)
            training_data.append({**features, "target_score": composite_score})

        df = pd.DataFrame(training_data)
        feature_columns = [col for col in df.columns if col != "target_score"]

        return df[feature_columns], df["target_score"]

    def _extract_scoring_features(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features for opportunity scoring."""
        features = {}

        # Basic opportunity features
        features["base_score"] = opportunity.get("score", 0)
        features["complexity_score"] = {"easy": 3, "medium": 2, "hard": 1}.get(
            opportunity.get("complexity", "medium"), 2
        )

        # Type features
        opp_type = opportunity.get("type", "").lower()
        features["is_bug_fix"] = int("bug" in opp_type)
        features["is_documentation"] = int("doc" in opp_type)
        features["is_testing"] = int("test" in opp_type)
        features["is_feature"] = int("feature" in opp_type)

        # Skills features
        skills = opportunity.get("skills_required", [])
        features["skills_count"] = len(skills)
        features["has_beginner_skills"] = int(any(
            skill.lower() in ["documentation", "testing", "bug_fix"]
            for skill in skills
        ))

        # Text features
        title_length = len(opportunity.get("title", ""))
        desc_length = len(opportunity.get("description", ""))
        features["title_length"] = title_length
        features["description_length"] = desc_length
        features["has_good_description"] = int(desc_length > 50)

        # Issue number feature
        features["has_issue_number"] = int(opportunity.get("issue_number") is not None)

        return features

    def _rule_based_score(self, opportunity: Dict[str, Any]) -> float:
        """Fallback rule-based scoring."""
        base_score = opportunity.get("score", 50)

        # Complexity bonus
        complexity_bonus = {"easy": 20, "medium": 10, "hard": 0}.get(
            opportunity.get("complexity", "medium"), 10
        )

        # Type bonus
        opp_type = opportunity.get("type", "").lower()
        type_bonus = 0
        if "bug" in opp_type:
            type_bonus = 15
        elif "doc" in opp_type:
            type_bonus = 10
        elif "test" in opp_type:
            type_bonus = 12

        # Description bonus
        desc_length = len(opportunity.get("description", ""))
        desc_bonus = min(10, desc_length // 20)

        total_score = base_score + complexity_bonus + type_bonus + desc_bonus
        return max(0, min(100, total_score))

    def _save_scoring_model(self) -> None:
        """Save scoring model to disk."""
        try:
            model_data = {
                "model": self.model,
                "scaler": self.scaler,
                "feature_names": self.feature_names,
                "model_version": self.model_version,
                "is_trained": self.is_trained,
            }

            model_file = self.model_path / "opportunity_scoring_model.pkl"
            joblib.dump(model_data, model_file)

        except Exception as e:
            self.logger.error(f"Failed to save scoring model: {e}")

    def _load_scoring_model(self) -> bool:
        """Load scoring model from disk."""
        try:
            model_file = self.model_path / "opportunity_scoring_model.pkl"

            if not model_file.exists():
                return False

            model_data = joblib.load(model_file)

            self.model = model_data["model"]
            self.scaler = model_data["scaler"]
            self.feature_names = model_data["feature_names"]
            self.model_version = model_data["model_version"]
            self.is_trained = model_data["is_trained"]

            return True

        except Exception as e:
            self.logger.warning(f"Failed to load scoring model: {e}")
            return False
