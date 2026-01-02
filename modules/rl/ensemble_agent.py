"""
Ensemble Agent for Trading

Manages multiple expert PPO agents, each specialized for a different market regime.
Combines:
- Multiple expert models (one per regime)
- Experience Replay (prevents forgetting within each expert)
- EWC (protects important weights in each expert)
- Regime detection (selects appropriate expert)

This architecture prevents catastrophic forgetting by:
1. Not overwriting knowledge - different experts for different regimes
2. Experience replay - each expert revisits past experiences
3. EWC - each expert protects its important learned weights
"""

import numpy as np
import torch
import os
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

from .ppo_agent import PPOAgent, create_agent
from .regime_detector import RegimeDetector, MarketRegime, RegimeAnalysis
from .experience_replay import ExperienceReplayBuffer, Trajectory

logger = logging.getLogger(__name__)


@dataclass
class EnsembleConfig:
    """Configuration for ensemble agent"""
    # Network architecture
    state_dim: int = 50
    action_dim: int = 3
    hidden_dims: List[int] = field(default_factory=lambda: [256, 128, 64])

    # PPO hyperparameters
    learning_rate: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    entropy_coef: float = 0.05
    value_coef: float = 0.5
    n_epochs: int = 10
    batch_size: int = 64

    # EWC settings
    use_ewc: bool = True
    ewc_lambda: float = 1000.0

    # Experience replay settings
    use_replay: bool = True
    replay_buffer_size: int = 1000
    replay_ratio: float = 0.3  # Mix 30% replay data with 70% new data
    n_replay_trajectories: int = 5

    # Regime settings
    regimes: List[str] = field(default_factory=lambda: ["bull", "bear", "sideways", "high_volatility"])
    fallback_regime: str = "sideways"  # Use sideways expert for unknown regimes

    # Training settings
    min_episodes_per_regime: int = 10  # Minimum episodes before consolidating EWC


class EnsembleAgent:
    """
    Ensemble of specialized PPO agents for different market regimes.

    Each expert is trained primarily on its own regime but maintains
    knowledge of other regimes through experience replay and EWC.
    """

    def __init__(
        self,
        config: Optional[EnsembleConfig] = None,
        device: str = "auto",
    ):
        """
        Initialize ensemble agent.

        Args:
            config: Ensemble configuration
            device: Device for training ('auto', 'cpu', or 'cuda')
        """
        self.config = config or EnsembleConfig()

        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        logger.info(f"Ensemble Agent using device: {self.device}")

        # Create expert agents for each regime
        self.experts: Dict[str, PPOAgent] = {}
        for regime in self.config.regimes:
            self.experts[regime] = self._create_expert(regime)

        # Regime detector
        self.regime_detector = RegimeDetector()

        # Experience replay buffers (one per regime)
        self.replay_buffers: Dict[str, ExperienceReplayBuffer] = {}
        if self.config.use_replay:
            for regime in self.config.regimes:
                self.replay_buffers[regime] = ExperienceReplayBuffer(
                    max_trajectories=self.config.replay_buffer_size,
                    regime_balance=True,
                )

        # Training statistics
        self.training_stats = {
            "episodes_per_regime": defaultdict(int),
            "total_episodes": 0,
            "regime_rewards": defaultdict(list),
            "ewc_consolidations": defaultdict(int),
        }

        # Current episode state
        self.current_regime: Optional[str] = None
        self.episode_experiences: List[Dict] = []

    def _create_expert(self, regime: str) -> PPOAgent:
        """Create a PPO agent for a specific regime"""
        agent = PPOAgent(
            state_dim=self.config.state_dim,
            action_dim=self.config.action_dim,
            learning_rate=self.config.learning_rate,
            gamma=self.config.gamma,
            gae_lambda=self.config.gae_lambda,
            clip_epsilon=self.config.clip_epsilon,
            entropy_coef=self.config.entropy_coef,
            value_coef=self.config.value_coef,
            n_epochs=self.config.n_epochs,
            batch_size=self.config.batch_size,
            hidden_dims=self.config.hidden_dims,
            device=str(self.device),
            use_ewc=self.config.use_ewc,
            ewc_lambda=self.config.ewc_lambda,
        )
        agent.set_regime(regime)
        logger.info(f"Created expert for regime: {regime}")
        return agent

    def detect_regime(
        self,
        prices: np.ndarray,
        high: Optional[np.ndarray] = None,
        low: Optional[np.ndarray] = None,
    ) -> RegimeAnalysis:
        """
        Detect current market regime from price data.

        Args:
            prices: Close prices
            high: High prices (optional)
            low: Low prices (optional)

        Returns:
            RegimeAnalysis with detected regime
        """
        return self.regime_detector.detect(prices, high, low)

    def select_action(
        self,
        state: np.ndarray,
        prices: np.ndarray,
        training: bool = True,
        temperature: float = 0.5,
    ) -> Tuple[int, float, float, str]:
        """
        Select action using the appropriate expert for current regime.

        Args:
            state: Current observation
            prices: Recent prices for regime detection
            training: Training mode flag
            temperature: Inference temperature

        Returns:
            Tuple of (action, log_prob, value, regime)
        """
        # Detect regime
        analysis = self.detect_regime(prices)
        regime = analysis.regime.value

        # Handle unknown regime
        if regime not in self.experts:
            regime = self.config.fallback_regime
            logger.debug(f"Unknown regime, using fallback: {regime}")

        self.current_regime = regime

        # Get action from appropriate expert
        expert = self.experts[regime]
        action, log_prob, value = expert.select_action(state, training, temperature)

        return action, log_prob, value, regime

    def store_experience(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        log_prob: float,
        value: float,
        regime: Optional[str] = None,
    ):
        """
        Store experience for current episode.

        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Episode done flag
            log_prob: Action log probability
            value: State value estimate
            regime: Market regime (uses current if not specified)
        """
        regime = regime or self.current_regime or self.config.fallback_regime

        # Store in appropriate expert's buffer
        if regime in self.experts:
            self.experts[regime].store_experience(
                state, action, reward, next_state, done, log_prob, value
            )

        # Also store for replay buffer
        self.episode_experiences.append({
            "state": state.copy(),
            "action": action,
            "reward": reward,
            "next_state": next_state.copy(),
            "done": done,
            "log_prob": log_prob,
            "value": value,
            "regime": regime,
        })

    def update(self, regime: Optional[str] = None) -> Dict[str, float]:
        """
        Update the appropriate expert.

        Args:
            regime: Regime to update (uses current if not specified)

        Returns:
            Training statistics
        """
        regime = regime or self.current_regime or self.config.fallback_regime

        if regime not in self.experts:
            logger.warning(f"Unknown regime for update: {regime}")
            return {}

        expert = self.experts[regime]

        # Perform PPO update
        stats = expert.update()

        return stats

    def end_episode(
        self,
        episode_reward: float,
        regime: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        End current episode, store trajectory in replay buffer.

        Args:
            episode_reward: Total episode reward
            regime: Episode regime (uses current if not specified)

        Returns:
            Episode summary statistics
        """
        regime = regime or self.current_regime or self.config.fallback_regime

        # Update statistics
        self.training_stats["episodes_per_regime"][regime] += 1
        self.training_stats["total_episodes"] += 1
        self.training_stats["regime_rewards"][regime].append(episode_reward)

        # Store trajectory in replay buffer
        if self.config.use_replay and len(self.episode_experiences) > 0:
            self._store_trajectory_in_replay(regime, episode_reward)

        # Check if we should consolidate EWC for this regime
        episodes = self.training_stats["episodes_per_regime"][regime]
        if (self.config.use_ewc and
            episodes > 0 and
            episodes % self.config.min_episodes_per_regime == 0):
            self._consolidate_regime(regime)

        # Clear episode experiences
        self.episode_experiences = []

        return {
            "regime": regime,
            "episode_reward": episode_reward,
            "episodes_in_regime": self.training_stats["episodes_per_regime"][regime],
            "total_episodes": self.training_stats["total_episodes"],
        }

    def _store_trajectory_in_replay(self, regime: str, episode_reward: float):
        """Store current episode as a trajectory in replay buffer"""
        if regime not in self.replay_buffers:
            return

        if len(self.episode_experiences) == 0:
            return

        # Convert experiences to trajectory format
        states = np.array([e["state"] for e in self.episode_experiences])
        actions = np.array([e["action"] for e in self.episode_experiences])
        rewards = np.array([e["reward"] for e in self.episode_experiences])
        log_probs = np.array([e["log_prob"] for e in self.episode_experiences])
        values = np.array([e["value"] for e in self.episode_experiences])
        dones = np.array([e["done"] for e in self.episode_experiences])

        # Compute advantages and returns (simplified)
        advantages = np.zeros_like(rewards)
        returns = np.zeros_like(rewards)

        # Simple advantage estimation (GAE would be better but this works)
        running_return = 0
        for t in reversed(range(len(rewards))):
            running_return = rewards[t] + self.config.gamma * running_return * (1 - dones[t])
            returns[t] = running_return
            advantages[t] = returns[t] - values[t]

        # Normalize advantages
        if len(advantages) > 1:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # Add to replay buffer
        self.replay_buffers[regime].add_trajectory(
            states=states,
            actions=actions,
            rewards=rewards,
            log_probs=log_probs,
            values=values,
            advantages=advantages,
            returns=returns,
            dones=dones,
            episode_reward=episode_reward,
            regime=regime,
            priority=abs(episode_reward) + 0.1,  # Higher priority for bigger returns
        )

    def _consolidate_regime(self, regime: str):
        """Consolidate learning for a regime using EWC"""
        if regime not in self.experts:
            return

        expert = self.experts[regime]

        if not expert.use_ewc or expert.ewc is None:
            return

        # Gather recent experiences for Fisher computation
        if regime in self.replay_buffers:
            buffer = self.replay_buffers[regime]
            trajectories = buffer.sample_trajectories(
                n=min(10, len(buffer.trajectories)),
                regime=regime,
            )

            if trajectories:
                all_states = np.concatenate([t.states for t in trajectories])
                all_actions = np.concatenate([t.actions for t in trajectories])

                expert.consolidate_learning(all_states, all_actions, regime)
                self.training_stats["ewc_consolidations"][regime] += 1

                logger.info(f"Consolidated EWC for regime '{regime}' "
                           f"(consolidation #{self.training_stats['ewc_consolidations'][regime]})")

    def train_episode(
        self,
        env,
        max_steps: int = 10000,
        regime_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Train for one episode.

        Args:
            env: Trading environment
            max_steps: Maximum steps per episode
            regime_override: Force a specific regime (for curriculum training)

        Returns:
            Episode metrics
        """
        state = env.reset()
        total_reward = 0
        step = 0

        # Get initial prices for regime detection
        prices = env.get_price_history() if hasattr(env, 'get_price_history') else np.array([100.0] * 100)

        while step < max_steps:
            # Select action
            if regime_override:
                # Use specified regime
                regime = regime_override
                self.current_regime = regime
                expert = self.experts.get(regime, self.experts[self.config.fallback_regime])
                action, log_prob, value = expert.select_action(state, training=True)
            else:
                # Auto-detect regime
                action, log_prob, value, regime = self.select_action(
                    state, prices, training=True
                )

            # Take step
            next_state, reward, done, info = env.step(action)

            # Store experience
            self.store_experience(
                state, action, reward, next_state, done, log_prob, value, regime
            )

            total_reward += reward
            state = next_state
            step += 1

            # Update prices for regime detection
            if hasattr(env, 'get_price_history'):
                prices = env.get_price_history()

            if done:
                break

        # Update appropriate expert
        update_stats = self.update(self.current_regime)

        # End episode and store replay
        episode_stats = self.end_episode(total_reward, self.current_regime)

        # Get environment metrics
        if hasattr(env, 'get_performance_metrics'):
            metrics = env.get_performance_metrics()
        else:
            metrics = {}

        return {
            **update_stats,
            **episode_stats,
            "episode_reward": total_reward,
            "episode_length": step,
            **metrics,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get ensemble training statistics"""
        stats = {
            "total_episodes": self.training_stats["total_episodes"],
            "episodes_per_regime": dict(self.training_stats["episodes_per_regime"]),
            "ewc_consolidations": dict(self.training_stats["ewc_consolidations"]),
        }

        # Add replay buffer stats
        if self.config.use_replay:
            replay_stats = {}
            for regime, buffer in self.replay_buffers.items():
                replay_stats[regime] = buffer.get_stats()
            stats["replay_buffers"] = replay_stats

        # Add average rewards per regime
        avg_rewards = {}
        for regime, rewards in self.training_stats["regime_rewards"].items():
            if rewards:
                avg_rewards[regime] = np.mean(rewards[-100:])  # Last 100 episodes
        stats["avg_rewards_per_regime"] = avg_rewards

        # Add EWC info per expert
        ewc_info = {}
        for regime, expert in self.experts.items():
            ewc_info[regime] = expert.get_ewc_info()
        stats["ewc_info"] = ewc_info

        return stats

    def save(self, path: str):
        """
        Save ensemble state.

        Args:
            path: Base path for saving (will create directory)
        """
        os.makedirs(path, exist_ok=True)

        # Save each expert
        for regime, expert in self.experts.items():
            expert_path = os.path.join(path, f"expert_{regime}.pt")
            expert.save(expert_path)

        # Save replay buffers
        if self.config.use_replay:
            for regime, buffer in self.replay_buffers.items():
                buffer_path = os.path.join(path, f"replay_{regime}.pkl")
                buffer.save(buffer_path)

        # Save config and stats
        config_path = os.path.join(path, "ensemble_config.json")
        with open(config_path, 'w') as f:
            config_dict = {
                "state_dim": self.config.state_dim,
                "action_dim": self.config.action_dim,
                "hidden_dims": self.config.hidden_dims,
                "learning_rate": self.config.learning_rate,
                "gamma": self.config.gamma,
                "use_ewc": self.config.use_ewc,
                "ewc_lambda": self.config.ewc_lambda,
                "use_replay": self.config.use_replay,
                "regimes": self.config.regimes,
            }
            json.dump(config_dict, f, indent=2)

        stats_path = os.path.join(path, "training_stats.json")
        with open(stats_path, 'w') as f:
            # Convert defaultdicts to regular dicts
            stats_to_save = {
                "episodes_per_regime": dict(self.training_stats["episodes_per_regime"]),
                "total_episodes": self.training_stats["total_episodes"],
                "ewc_consolidations": dict(self.training_stats["ewc_consolidations"]),
            }
            json.dump(stats_to_save, f, indent=2)

        logger.info(f"Saved ensemble to {path} ({len(self.experts)} experts)")

    def load(self, path: str) -> bool:
        """
        Load ensemble state.

        Args:
            path: Path to saved ensemble directory

        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(path):
            logger.warning(f"Ensemble path not found: {path}")
            return False

        try:
            # Load each expert
            for regime in self.config.regimes:
                expert_path = os.path.join(path, f"expert_{regime}.pt")
                if os.path.exists(expert_path):
                    self.experts[regime].load(expert_path)
                else:
                    logger.warning(f"Expert not found for regime {regime}")

            # Load replay buffers
            if self.config.use_replay:
                for regime in self.config.regimes:
                    buffer_path = os.path.join(path, f"replay_{regime}.pkl")
                    if regime in self.replay_buffers and os.path.exists(buffer_path):
                        self.replay_buffers[regime].load(buffer_path)

            # Load stats
            stats_path = os.path.join(path, "training_stats.json")
            if os.path.exists(stats_path):
                with open(stats_path, 'r') as f:
                    stats = json.load(f)
                    self.training_stats["episodes_per_regime"] = defaultdict(int, stats.get("episodes_per_regime", {}))
                    self.training_stats["total_episodes"] = stats.get("total_episodes", 0)
                    self.training_stats["ewc_consolidations"] = defaultdict(int, stats.get("ewc_consolidations", {}))

            logger.info(f"Loaded ensemble from {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load ensemble: {e}")
            return False


# Factory function
def create_ensemble_agent(
    state_dim: int,
    action_dim: int,
    use_ewc: bool = True,
    use_replay: bool = True,
    **kwargs
) -> EnsembleAgent:
    """
    Create an ensemble agent with default configuration.

    Args:
        state_dim: State observation dimension
        action_dim: Number of actions
        use_ewc: Enable EWC for catastrophic forgetting prevention
        use_replay: Enable experience replay
        **kwargs: Additional config parameters

    Returns:
        Configured EnsembleAgent
    """
    config = EnsembleConfig(
        state_dim=state_dim,
        action_dim=action_dim,
        use_ewc=use_ewc,
        use_replay=use_replay,
        **kwargs,
    )
    return EnsembleAgent(config)
