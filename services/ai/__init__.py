"""
JJ-Bot AI Services
==================

Background services for AI-powered trading.

Services:
- InferenceService: Real-time AI analysis and predictions
- TrainingService: Model training orchestration (Phase 3)
- LearningPipeline: Continuous learning from trades (Phase 4)
"""

from .inference_service import AIInferenceService

__all__ = ['AIInferenceService']
