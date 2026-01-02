"""
Experience Replay Buffer for Reinforcement Learning

Stores past experiences and enables mixing old/new data during training.
This helps prevent catastrophic forgetting by re-exposing the model to
past experiences while learning new ones.

Key Features:
- Prioritized Experience Replay (optional)
- Trajectory storage for PPO compatibility
- Memory-efficient numpy storage
- Configurable buffer size
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import deque
import random
import logging

logger = logging.getLogger(__name__)


@dataclass
class Experience:
    """Single experience tuple"""
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool
    log_prob: float = 0.0
    value: float = 0.0
    advantage: float = 0.0
    return_to_go: float = 0.0


@dataclass
class Trajectory:
    """Complete episode trajectory for PPO"""
    states: np.ndarray
    actions: np.ndarray
    rewards: np.ndarray
    log_probs: np.ndarray
    values: np.ndarray
    advantages: np.ndarray
    returns: np.ndarray
    dones: np.ndarray

    # Metadata
    episode_reward: float = 0.0
    episode_length: int = 0
    regime: str = "unknown"  # Market regime when trajectory was collected
    timestamp: float = 0.0

    def __len__(self):
        return len(self.states)


class ExperienceReplayBuffer:
    """
    Experience Replay Buffer for preventing catastrophic forgetting.

    Stores complete trajectories (for PPO) rather than individual transitions.
    Supports regime-aware storage to maintain balance across market conditions.
    """

    def __init__(
        self,
        max_trajectories: int = 1000,
        max_experiences: int = 100000,
        prioritized: bool = False,
        alpha: float = 0.6,  # Priority exponent
        beta: float = 0.4,   # Importance sampling weight
        regime_balance: bool = True,  # Balance storage across regimes
    ):
        """
        Initialize replay buffer.

        Args:
            max_trajectories: Maximum number of trajectories to store
            max_experiences: Maximum total experiences (soft limit)
            prioritized: Use prioritized experience replay
            alpha: Priority exponent (0 = uniform, 1 = full priority)
            beta: Importance sampling weight
            regime_balance: Try to balance storage across market regimes
        """
        self.max_trajectories = max_trajectories
        self.max_experiences = max_experiences
        self.prioritized = prioritized
        self.alpha = alpha
        self.beta = beta
        self.regime_balance = regime_balance

        # Storage
        self.trajectories: deque = deque(maxlen=max_trajectories)
        self.priorities: deque = deque(maxlen=max_trajectories)

        # Regime-specific storage for balanced sampling
        self.regime_trajectories: Dict[str, List[int]] = {
            "bull": [],
            "bear": [],
            "sideways": [],
            "high_volatility": [],
            "unknown": []
        }

        # Statistics
        self.total_experiences = 0
        self.total_trajectories_added = 0

    def add_trajectory(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        log_probs: np.ndarray,
        values: np.ndarray,
        advantages: np.ndarray,
        returns: np.ndarray,
        dones: np.ndarray,
        episode_reward: float = 0.0,
        regime: str = "unknown",
        priority: float = 1.0,
    ):
        """Add a complete trajectory to the buffer"""
        import time

        trajectory = Trajectory(
            states=states.copy(),
            actions=actions.copy(),
            rewards=rewards.copy(),
            log_probs=log_probs.copy(),
            values=values.copy(),
            advantages=advantages.copy(),
            returns=returns.copy(),
            dones=dones.copy(),
            episode_reward=episode_reward,
            episode_length=len(states),
            regime=regime,
            timestamp=time.time(),
        )

        # Add to main storage
        self.trajectories.append(trajectory)
        self.priorities.append(priority)

        # Track regime
        traj_idx = len(self.trajectories) - 1
        if regime in self.regime_trajectories:
            self.regime_trajectories[regime].append(traj_idx)
        else:
            self.regime_trajectories["unknown"].append(traj_idx)

        # Update statistics
        self.total_experiences += len(states)
        self.total_trajectories_added += 1

        # Clean up old regime indices
        self._cleanup_regime_indices()

        logger.debug(f"Added trajectory: {len(states)} steps, regime={regime}, reward={episode_reward:.2f}")

    def _cleanup_regime_indices(self):
        """Remove invalid indices from regime tracking"""
        max_idx = len(self.trajectories)
        for regime in self.regime_trajectories:
            self.regime_trajectories[regime] = [
                idx for idx in self.regime_trajectories[regime]
                if idx < max_idx
            ]

    def sample_trajectories(
        self,
        n: int,
        regime: Optional[str] = None,
        mix_ratio: float = 0.5,
    ) -> List[Trajectory]:
        """
        Sample trajectories from the buffer.

        Args:
            n: Number of trajectories to sample
            regime: If specified, prioritize this regime
            mix_ratio: Ratio of regime-specific vs random sampling

        Returns:
            List of Trajectory objects
        """
        if len(self.trajectories) == 0:
            return []

        n = min(n, len(self.trajectories))

        if self.prioritized:
            return self._prioritized_sample(n)
        elif regime and self.regime_balance:
            return self._regime_balanced_sample(n, regime, mix_ratio)
        else:
            return self._uniform_sample(n)

    def _uniform_sample(self, n: int) -> List[Trajectory]:
        """Uniform random sampling"""
        indices = random.sample(range(len(self.trajectories)), n)
        return [self.trajectories[i] for i in indices]

    def _prioritized_sample(self, n: int) -> List[Trajectory]:
        """Prioritized experience replay sampling"""
        priorities = np.array(list(self.priorities))
        probs = priorities ** self.alpha
        probs /= probs.sum()

        indices = np.random.choice(len(self.trajectories), size=n, p=probs, replace=False)
        return [self.trajectories[i] for i in indices]

    def _regime_balanced_sample(
        self,
        n: int,
        target_regime: str,
        mix_ratio: float
    ) -> List[Trajectory]:
        """
        Sample with regime balancing.

        Args:
            n: Total trajectories to sample
            target_regime: Current market regime
            mix_ratio: Ratio of target regime vs other regimes
        """
        sampled = []

        # Get indices for target regime
        target_indices = self.regime_trajectories.get(target_regime, [])
        valid_target = [i for i in target_indices if i < len(self.trajectories)]

        # Number from target regime
        n_target = min(int(n * mix_ratio), len(valid_target))
        if n_target > 0:
            target_sample = random.sample(valid_target, n_target)
            sampled.extend([self.trajectories[i] for i in target_sample])

        # Fill rest with random sampling from all regimes
        n_random = n - len(sampled)
        if n_random > 0:
            all_indices = list(range(len(self.trajectories)))
            available = [i for i in all_indices if i not in target_sample] if n_target > 0 else all_indices
            if len(available) > 0:
                random_sample = random.sample(available, min(n_random, len(available)))
                sampled.extend([self.trajectories[i] for i in random_sample])

        return sampled

    def get_mixed_batch(
        self,
        new_trajectory: Trajectory,
        replay_ratio: float = 0.3,
        n_replay: int = 5,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Create a mixed batch of new experience + replay experiences.

        Args:
            new_trajectory: Fresh trajectory from current episode
            replay_ratio: Fraction of batch from replay buffer
            n_replay: Number of replay trajectories to mix in

        Returns:
            Tuple of (states, actions, rewards, log_probs, values, advantages, returns)
        """
        # Start with new trajectory
        all_states = [new_trajectory.states]
        all_actions = [new_trajectory.actions]
        all_rewards = [new_trajectory.rewards]
        all_log_probs = [new_trajectory.log_probs]
        all_values = [new_trajectory.values]
        all_advantages = [new_trajectory.advantages]
        all_returns = [new_trajectory.returns]

        # Add replay trajectories if available
        if len(self.trajectories) > 0:
            replay_trajs = self.sample_trajectories(
                n=n_replay,
                regime=new_trajectory.regime,
                mix_ratio=0.5
            )

            for traj in replay_trajs:
                all_states.append(traj.states)
                all_actions.append(traj.actions)
                all_rewards.append(traj.rewards)
                all_log_probs.append(traj.log_probs)
                all_values.append(traj.values)
                all_advantages.append(traj.advantages)
                all_returns.append(traj.returns)

        # Concatenate all
        states = np.concatenate(all_states, axis=0)
        actions = np.concatenate(all_actions, axis=0)
        rewards = np.concatenate(all_rewards, axis=0)
        log_probs = np.concatenate(all_log_probs, axis=0)
        values = np.concatenate(all_values, axis=0)
        advantages = np.concatenate(all_advantages, axis=0)
        returns = np.concatenate(all_returns, axis=0)

        # Shuffle the combined batch
        indices = np.random.permutation(len(states))

        return (
            states[indices],
            actions[indices],
            rewards[indices],
            log_probs[indices],
            values[indices],
            advantages[indices],
            returns[indices],
        )

    def update_priorities(self, indices: List[int], priorities: List[float]):
        """Update priorities for prioritized replay"""
        for idx, priority in zip(indices, priorities):
            if 0 <= idx < len(self.priorities):
                self.priorities[idx] = priority

    def get_regime_distribution(self) -> Dict[str, int]:
        """Get distribution of trajectories across regimes"""
        self._cleanup_regime_indices()
        return {
            regime: len(indices)
            for regime, indices in self.regime_trajectories.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get buffer statistics"""
        return {
            "total_trajectories": len(self.trajectories),
            "total_experiences": self.total_experiences,
            "trajectories_added": self.total_trajectories_added,
            "regime_distribution": self.get_regime_distribution(),
            "buffer_utilization": len(self.trajectories) / self.max_trajectories,
        }

    def clear(self):
        """Clear the buffer"""
        self.trajectories.clear()
        self.priorities.clear()
        for regime in self.regime_trajectories:
            self.regime_trajectories[regime] = []
        self.total_experiences = 0
        logger.info("Experience replay buffer cleared")

    def save(self, path: str):
        """Save buffer to disk"""
        import pickle

        data = {
            "trajectories": list(self.trajectories),
            "priorities": list(self.priorities),
            "regime_trajectories": self.regime_trajectories,
            "total_experiences": self.total_experiences,
            "total_trajectories_added": self.total_trajectories_added,
        }

        with open(path, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"Saved replay buffer to {path} ({len(self.trajectories)} trajectories)")

    def load(self, path: str) -> bool:
        """Load buffer from disk"""
        import pickle

        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)

            self.trajectories = deque(data["trajectories"], maxlen=self.max_trajectories)
            self.priorities = deque(data["priorities"], maxlen=self.max_trajectories)
            self.regime_trajectories = data["regime_trajectories"]
            self.total_experiences = data["total_experiences"]
            self.total_trajectories_added = data["total_trajectories_added"]

            logger.info(f"Loaded replay buffer from {path} ({len(self.trajectories)} trajectories)")
            return True
        except Exception as e:
            logger.warning(f"Failed to load replay buffer: {e}")
            return False


# Convenience function to create buffer
def create_replay_buffer(
    max_trajectories: int = 1000,
    prioritized: bool = False,
) -> ExperienceReplayBuffer:
    """Create an experience replay buffer"""
    return ExperienceReplayBuffer(
        max_trajectories=max_trajectories,
        prioritized=prioritized,
    )
