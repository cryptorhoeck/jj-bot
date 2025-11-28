"""
AI System Configuration
=======================

Centralized configuration for all AI components.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path


@dataclass
class LLMConfig:
    """Configuration for LLM (Claude) integration."""
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    max_tokens: int = 4096
    temperature: float = 0.3  # Lower for more consistent trading analysis

    # Rate limiting
    requests_per_minute: int = 50
    tokens_per_minute: int = 100000

    # Caching
    cache_responses: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes


@dataclass
class DocumentIngestionConfig:
    """Configuration for document processing pipeline."""
    supported_formats: List[str] = field(default_factory=lambda: ['.pdf', '.txt', '.md', '.csv'])
    chunk_size: int = 1000  # tokens per chunk
    chunk_overlap: int = 100

    # Storage paths
    raw_documents_path: Path = field(default_factory=lambda: Path("data/training_data/documents"))
    processed_path: Path = field(default_factory=lambda: Path("data/training_data/processed"))
    embeddings_path: Path = field(default_factory=lambda: Path("data/training_data/embeddings"))


@dataclass
class TimeSeriesConfig:
    """Configuration for time series ML models."""
    model_type: str = "lstm"  # lstm, transformer, or ensemble
    sequence_length: int = 60  # Number of time steps to look back
    prediction_horizon: int = 5  # Number of time steps to predict forward

    # Training
    batch_size: int = 32
    epochs: int = 100
    learning_rate: float = 0.001
    validation_split: float = 0.2

    # Model storage
    models_path: Path = field(default_factory=lambda: Path("data/models/time_series"))


@dataclass
class ReinforcementLearningConfig:
    """Configuration for RL trading agent."""
    algorithm: str = "ppo"  # ppo, dqn, a2c

    # Environment
    initial_balance: float = 10000.0
    transaction_fee: float = 0.001
    max_position_size: float = 0.5  # Max % of portfolio in single position

    # Training
    total_timesteps: int = 1000000
    learning_rate: float = 0.0003
    gamma: float = 0.99  # Discount factor

    # Model storage
    models_path: Path = field(default_factory=lambda: Path("data/models/rl_agents"))


@dataclass
class AIConfig:
    """Master configuration for the AI system."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    document_ingestion: DocumentIngestionConfig = field(default_factory=DocumentIngestionConfig)
    time_series: TimeSeriesConfig = field(default_factory=TimeSeriesConfig)
    reinforcement_learning: ReinforcementLearningConfig = field(default_factory=ReinforcementLearningConfig)

    # Global settings
    enable_logging: bool = True
    log_level: str = "INFO"

    # Feature flags for phased rollout
    enable_llm_analysis: bool = True
    enable_document_learning: bool = False  # Phase 2
    enable_chart_vision: bool = False  # Phase 3
    enable_time_series_ml: bool = False  # Phase 3
    enable_rl_agent: bool = False  # Phase 4

    @classmethod
    def from_env(cls) -> 'AIConfig':
        """Create config from environment variables."""
        config = cls()

        # Override from environment
        if os.getenv("AI_MODEL"):
            config.llm.model = os.getenv("AI_MODEL")
        if os.getenv("AI_TEMPERATURE"):
            config.llm.temperature = float(os.getenv("AI_TEMPERATURE"))
        if os.getenv("AI_LOG_LEVEL"):
            config.log_level = os.getenv("AI_LOG_LEVEL")

        return config

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if self.enable_llm_analysis and not self.llm.api_key:
            errors.append("ANTHROPIC_API_KEY not set but LLM analysis is enabled")

        if self.llm.temperature < 0 or self.llm.temperature > 1:
            errors.append(f"LLM temperature must be 0-1, got {self.llm.temperature}")

        return errors
