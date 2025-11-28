"""
JJ-Bot AI Module
================

Full AI System (Option C) - Multi-modal AI with continuous learning.

Components:
- llm_client: Claude API integration for market analysis and reasoning
- document_ingestion: PDF/research paper processing pipeline
- chart_vision: Chart image analysis (future)
- time_series_model: LSTM/Transformer for price prediction (future)
- rl_agent: Reinforcement learning agent (future)

Phase 1: LLM Integration (Current)
Phase 2: Document Ingestion Pipeline
Phase 3: Time Series ML Models
Phase 4: Reinforcement Learning Agent
"""

from .config import AIConfig

__all__ = ['AIConfig']
__version__ = '0.1.0'
