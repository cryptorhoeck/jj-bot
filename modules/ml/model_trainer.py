"""
ML Model Trainer

Train and manage machine learning models for price prediction
"""

import numpy as np
import pandas as pd
import pickle
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ scikit-learn not available. Install with: pip install scikit-learn")

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("⚠️ XGBoost not available. Install with: pip install xgboost")

from .feature_engineering import FeatureEngineer


class ModelTrainer:
    """Train and evaluate ML models for price prediction"""

    def __init__(self, models_dir: str = "./data/ml_models"):
        """
        Initialize model trainer

        Args:
            models_dir: Directory to save/load trained models
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.feature_engineer = FeatureEngineer()
        self.model = None
        self.model_type = None
        self.feature_names = None
        self.training_metrics = {}

    def prepare_training_data(
        self,
        candles: List[Dict],
        test_size: float = 0.2,
        normalize: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare training data from candles

        Args:
            candles: List of OHLCV candles
            test_size: Proportion of data to use for testing
            normalize: Whether to normalize features

        Returns:
            X_train, X_test, y_train, y_test
        """
        # Extract features and labels
        result = self.feature_engineer.extract_all_features(candles, include_labels=True)

        if not result['success']:
            raise ValueError(f"Feature extraction failed: {result.get('error', 'Unknown error')}")

        features = result['features']
        labels = result['labels']
        self.feature_names = result['feature_names']

        # Remove rows with NaN values
        df = pd.DataFrame(features, columns=self.feature_names)
        df['label'] = labels
        df = df.dropna()

        X = df[self.feature_names].values
        y = df['label'].values

        # Normalize features if requested
        if normalize:
            norm_result = self.feature_engineer.normalize_features(X, method='standardize')
            X = norm_result['normalized_features']

        # Split into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        return X_train, X_test, y_train, y_test

    def train_random_forest(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        n_estimators: int = 100,
        max_depth: Optional[int] = 10,
        min_samples_split: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Train a Random Forest classifier

        Args:
            X_train: Training features
            y_train: Training labels
            n_estimators: Number of trees
            max_depth: Maximum depth of trees
            min_samples_split: Minimum samples to split a node
            **kwargs: Additional parameters for RandomForestClassifier

        Returns:
            Training results dictionary
        """
        if not SKLEARN_AVAILABLE:
            return {
                'success': False,
                'error': 'scikit-learn not available'
            }

        print(f"🌲 Training Random Forest with {n_estimators} trees...")

        # Train model
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=42,
            n_jobs=-1,
            **kwargs
        )

        self.model.fit(X_train, y_train)
        self.model_type = 'random_forest'

        # Cross-validation
        cv_scores = cross_val_score(self.model, X_train, y_train, cv=5)

        return {
            'success': True,
            'model_type': 'random_forest',
            'n_estimators': n_estimators,
            'max_depth': max_depth,
            'cv_mean_accuracy': float(cv_scores.mean()),
            'cv_std_accuracy': float(cv_scores.std()),
            'training_samples': len(X_train)
        }

    def train_xgboost(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        n_estimators: int = 100,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Train an XGBoost classifier

        Args:
            X_train: Training features
            y_train: Training labels
            n_estimators: Number of boosting rounds
            max_depth: Maximum depth of trees
            learning_rate: Learning rate
            **kwargs: Additional parameters for XGBClassifier

        Returns:
            Training results dictionary
        """
        if not XGBOOST_AVAILABLE:
            return {
                'success': False,
                'error': 'XGBoost not available'
            }

        print(f"🚀 Training XGBoost with {n_estimators} estimators...")

        # Train model
        self.model = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=42,
            n_jobs=-1,
            **kwargs
        )

        self.model.fit(X_train, y_train)
        self.model_type = 'xgboost'

        return {
            'success': True,
            'model_type': 'xgboost',
            'n_estimators': n_estimators,
            'max_depth': max_depth,
            'learning_rate': learning_rate,
            'training_samples': len(X_train)
        }

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, Any]:
        """
        Evaluate model on test data

        Args:
            X_test: Test features
            y_test: Test labels

        Returns:
            Evaluation metrics dictionary
        """
        if self.model is None:
            return {
                'success': False,
                'error': 'No model trained'
            }

        # Make predictions
        y_pred = self.model.predict(X_test)

        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)

        # Handle multi-class metrics
        average = 'weighted'  # Use weighted average for multi-class
        precision = precision_score(y_test, y_pred, average=average, zero_division=0)
        recall = recall_score(y_test, y_pred, average=average, zero_division=0)
        f1 = f1_score(y_test, y_pred, average=average, zero_division=0)

        # Classification report
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

        # Feature importance (if available)
        feature_importance = None
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            feature_importance = [
                {
                    'feature': self.feature_names[i] if self.feature_names else f'feature_{i}',
                    'importance': float(importances[i])
                }
                for i in range(len(importances))
            ]
            # Sort by importance
            feature_importance.sort(key=lambda x: x['importance'], reverse=True)

        self.training_metrics = {
            'success': True,
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'test_samples': len(X_test),
            'classification_report': report,
            'feature_importance': feature_importance[:20] if feature_importance else None  # Top 20
        }

        print(f"✅ Model Evaluation:")
        print(f"   Accuracy:  {accuracy:.4f}")
        print(f"   Precision: {precision:.4f}")
        print(f"   Recall:    {recall:.4f}")
        print(f"   F1-Score:  {f1:.4f}")

        return self.training_metrics

    def save_model(
        self,
        model_name: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Save trained model to disk

        Args:
            model_name: Name for the saved model
            metadata: Additional metadata to save

        Returns:
            Save result dictionary
        """
        if self.model is None:
            return {
                'success': False,
                'error': 'No model to save'
            }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_file = self.models_dir / f"{model_name}_{timestamp}.pkl"
        metadata_file = self.models_dir / f"{model_name}_{timestamp}_metadata.json"

        try:
            # Save model
            with open(model_file, 'wb') as f:
                pickle.dump(self.model, f)

            # Save metadata
            meta = {
                'model_type': self.model_type,
                'model_name': model_name,
                'timestamp': timestamp,
                'feature_names': self.feature_names,
                'training_metrics': self.training_metrics,
                'custom_metadata': metadata or {}
            }

            with open(metadata_file, 'w') as f:
                json.dump(meta, f, indent=2)

            print(f"💾 Model saved: {model_file}")

            return {
                'success': True,
                'model_file': str(model_file),
                'metadata_file': str(metadata_file)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def load_model(
        self,
        model_path: str
    ) -> Dict[str, Any]:
        """
        Load a trained model from disk

        Args:
            model_path: Path to the model file

        Returns:
            Load result dictionary
        """
        try:
            # Load model
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)

            # Try to load metadata
            metadata_path = str(model_path).replace('.pkl', '_metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)

                self.model_type = metadata.get('model_type')
                self.feature_names = metadata.get('feature_names')
                self.training_metrics = metadata.get('training_metrics', {})

            print(f"📂 Model loaded: {model_path}")

            return {
                'success': True,
                'model_path': model_path,
                'model_type': self.model_type
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def predict(
        self,
        candles: List[Dict],
        return_probabilities: bool = False
    ) -> Dict[str, Any]:
        """
        Make predictions on new data

        Args:
            candles: List of OHLCV candles
            return_probabilities: Whether to return class probabilities

        Returns:
            Prediction results dictionary
        """
        if self.model is None:
            return {
                'success': False,
                'error': 'No model loaded'
            }

        # Extract features
        result = self.feature_engineer.extract_all_features(candles, include_labels=False)

        if not result['success']:
            return {
                'success': False,
                'error': f"Feature extraction failed: {result.get('error', 'Unknown error')}"
            }

        features = result['features']

        # Normalize features
        norm_result = self.feature_engineer.normalize_features(features, method='standardize')
        X = norm_result['normalized_features']

        # Make predictions
        predictions = self.model.predict(X)

        response = {
            'success': True,
            'predictions': predictions.tolist(),
            'num_predictions': len(predictions)
        }

        # Add probabilities if requested
        if return_probabilities and hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(X)
            response['probabilities'] = probabilities.tolist()
            response['classes'] = self.model.classes_.tolist()

        return response

    def get_latest_prediction(
        self,
        candles: List[Dict],
        return_probability: bool = True
    ) -> Dict[str, Any]:
        """
        Get prediction for the most recent candle

        Args:
            candles: List of OHLCV candles (need historical context)
            return_probability: Whether to return prediction confidence

        Returns:
            Prediction dictionary with latest prediction
        """
        result = self.predict(candles, return_probabilities=return_probability)

        if not result['success']:
            return result

        # Get the last prediction
        prediction = result['predictions'][-1]

        response = {
            'success': True,
            'prediction': prediction,
            'prediction_label': ['down', 'neutral', 'up'][prediction]
        }

        # Add confidence if probabilities available
        if return_probability and 'probabilities' in result:
            probs = result['probabilities'][-1]
            response['confidence'] = max(probs)
            response['probabilities'] = {
                'down': probs[0],
                'neutral': probs[1],
                'up': probs[2]
            }

        return response


# Global model trainer instance
model_trainer = ModelTrainer()


# Convenience function
def train_model(
    candles: List[Dict],
    model_type: str = 'random_forest',
    **kwargs
) -> Dict[str, Any]:
    """
    Train a model with default parameters

    Args:
        candles: Training data (OHLCV candles)
        model_type: 'random_forest' or 'xgboost'
        **kwargs: Additional model parameters

    Returns:
        Training and evaluation results
    """
    trainer = ModelTrainer()

    # Prepare data
    X_train, X_test, y_train, y_test = trainer.prepare_training_data(candles)

    # Train model
    if model_type == 'random_forest':
        train_result = trainer.train_random_forest(X_train, y_train, **kwargs)
    elif model_type == 'xgboost':
        train_result = trainer.train_xgboost(X_train, y_train, **kwargs)
    else:
        return {
            'success': False,
            'error': f"Unknown model type: {model_type}"
        }

    if not train_result['success']:
        return train_result

    # Evaluate model
    eval_result = trainer.evaluate(X_test, y_test)

    return {
        'success': True,
        'training': train_result,
        'evaluation': eval_result,
        'trainer': trainer
    }
