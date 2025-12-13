"""
Proximal Policy Optimization (PPO) Agent for Trading
Learns optimal trading policy from market interactions
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque
import logging
import os
import json
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class Experience:
    """Single step experience"""
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool
    log_prob: float
    value: float


class ActorCritic(nn.Module):
    """
    Actor-Critic Network for PPO

    Architecture:
    - Shared feature extractor
    - Separate actor (policy) and critic (value) heads
    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hidden_dims: List[int] = [256, 128, 64],
        activation: str = "relu"
    ):
        super().__init__()

        self.state_dim = state_dim
        self.action_dim = action_dim

        # Activation function
        activations = {
            "relu": nn.ReLU,
            "tanh": nn.Tanh,
            "leaky_relu": nn.LeakyReLU,
            "elu": nn.ELU,
        }
        act_fn = activations.get(activation, nn.ReLU)

        # Shared feature extractor
        layers = []
        prev_dim = state_dim
        for hidden_dim in hidden_dims[:-1]:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                act_fn(),
                nn.Dropout(0.1),
            ])
            prev_dim = hidden_dim

        self.shared = nn.Sequential(*layers)

        # Actor head (policy)
        self.actor = nn.Sequential(
            nn.Linear(prev_dim, hidden_dims[-1]),
            act_fn(),
            nn.Linear(hidden_dims[-1], action_dim),
            nn.Softmax(dim=-1)
        )

        # Critic head (value function)
        self.critic = nn.Sequential(
            nn.Linear(prev_dim, hidden_dims[-1]),
            act_fn(),
            nn.Linear(hidden_dims[-1], 1)
        )

        # Initialize weights
        self.apply(self._init_weights)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            nn.init.orthogonal_(module.weight, gain=np.sqrt(2))
            nn.init.constant_(module.bias, 0.0)

    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Forward pass returning action probabilities and state value"""
        features = self.shared(state)
        action_probs = self.actor(features)
        state_value = self.critic(features)
        return action_probs, state_value

    def get_action(self, state: torch.Tensor) -> Tuple[int, float, float]:
        """Sample action from policy"""
        action_probs, state_value = self.forward(state)
        dist = Categorical(action_probs)
        action = dist.sample()
        log_prob = dist.log_prob(action)
        return action.item(), log_prob.item(), state_value.item()

    def evaluate(
        self,
        states: torch.Tensor,
        actions: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Evaluate actions for PPO update"""
        action_probs, state_values = self.forward(states)
        dist = Categorical(action_probs)

        log_probs = dist.log_prob(actions)
        entropy = dist.entropy()

        return log_probs, state_values.squeeze(-1), entropy


class PPOAgent:
    """
    Proximal Policy Optimization Agent

    Features:
    - Clipped surrogate objective
    - Generalized Advantage Estimation (GAE)
    - Entropy bonus for exploration
    - Gradient clipping
    - Learning rate scheduling
    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        entropy_coef: float = 0.05,  # Higher entropy for better exploration
        value_coef: float = 0.5,
        max_grad_norm: float = 0.5,
        n_epochs: int = 10,
        batch_size: int = 64,
        hidden_dims: List[int] = [256, 128, 64],
        device: str = "auto"
    ):
        # Set device
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        logger.info(f"PPO Agent using device: {self.device}")

        # Hyperparameters
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.entropy_coef = entropy_coef
        self.value_coef = value_coef
        self.max_grad_norm = max_grad_norm
        self.n_epochs = n_epochs
        self.batch_size = batch_size

        # Networks
        self.policy = ActorCritic(state_dim, action_dim, hidden_dims).to(self.device)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=learning_rate)
        # Gentler LR decay: reduce by 1% every 5000 episodes (maintains ~60% LR after 50k episodes)
        self.scheduler = optim.lr_scheduler.StepLR(self.optimizer, step_size=5000, gamma=0.99)

        # Experience buffer
        self.buffer: List[Experience] = []

        # Training stats
        self.training_stats = {
            "policy_loss": [],
            "value_loss": [],
            "entropy": [],
            "total_loss": [],
            "rewards": [],
            "episode_lengths": [],
        }
        self.episode_count = 0

    def select_action(self, state: np.ndarray, training: bool = True) -> Tuple[int, float, float]:
        """Select action given current state"""
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)

        with torch.no_grad():
            if training:
                action, log_prob, value = self.policy.get_action(state_tensor)
            else:
                # Greedy action for evaluation
                action_probs, value = self.policy(state_tensor)
                action = torch.argmax(action_probs, dim=-1).item()
                log_prob = torch.log(action_probs[0, action]).item()
                value = value.item()

        return action, log_prob, value

    def store_experience(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        log_prob: float,
        value: float
    ):
        """Store experience in buffer"""
        self.buffer.append(Experience(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done,
            log_prob=log_prob,
            value=value
        ))

    def compute_gae(self, rewards: List[float], values: List[float], dones: List[bool]) -> Tuple[np.ndarray, np.ndarray]:
        """Compute Generalized Advantage Estimation"""
        advantages = np.zeros(len(rewards), dtype=np.float32)
        returns = np.zeros(len(rewards), dtype=np.float32)

        gae = 0
        # Bootstrap from next state value (not current state)
        # For the last step, use 0 if done, otherwise need next state value
        # Since we don't have next_state value here, we estimate with last value
        next_value = 0 if dones[-1] else values[-1]

        for t in reversed(range(len(rewards))):
            # Calculate TD error: r + γV(s') - V(s)
            delta = rewards[t] + self.gamma * next_value * (1 - dones[t]) - values[t]
            gae = delta + self.gamma * self.gae_lambda * (1 - dones[t]) * gae
            advantages[t] = gae
            returns[t] = gae + values[t]

            # For next iteration, the "next_value" is current value
            next_value = values[t]

        return advantages, returns

    def update(self) -> Dict[str, float]:
        """Perform PPO update on collected experiences"""
        if len(self.buffer) < self.batch_size:
            return {}

        # Extract experiences
        states = np.array([e.state for e in self.buffer])
        actions = np.array([e.action for e in self.buffer])
        rewards = [e.reward for e in self.buffer]
        dones = [e.done for e in self.buffer]
        old_log_probs = np.array([e.log_prob for e in self.buffer])
        values = [e.value for e in self.buffer]

        # Compute advantages
        advantages, returns = self.compute_gae(rewards, values, dones)

        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # Convert to tensors
        states_tensor = torch.FloatTensor(states).to(self.device)
        actions_tensor = torch.LongTensor(actions).to(self.device)
        old_log_probs_tensor = torch.FloatTensor(old_log_probs).to(self.device)
        advantages_tensor = torch.FloatTensor(advantages).to(self.device)
        returns_tensor = torch.FloatTensor(returns).to(self.device)

        # PPO update epochs
        total_policy_loss = 0
        total_value_loss = 0
        total_entropy = 0
        total_clip_fraction = 0
        total_grad_norm = 0

        n_samples = len(self.buffer)
        indices = np.arange(n_samples)

        for _ in range(self.n_epochs):
            np.random.shuffle(indices)

            for start in range(0, n_samples, self.batch_size):
                end = start + self.batch_size
                batch_indices = indices[start:end]

                # Get batch
                batch_states = states_tensor[batch_indices]
                batch_actions = actions_tensor[batch_indices]
                batch_old_log_probs = old_log_probs_tensor[batch_indices]
                batch_advantages = advantages_tensor[batch_indices]
                batch_returns = returns_tensor[batch_indices]

                # Evaluate current policy
                new_log_probs, state_values, entropy = self.policy.evaluate(
                    batch_states, batch_actions
                )

                # Policy loss (clipped surrogate)
                ratio = torch.exp(new_log_probs - batch_old_log_probs)
                surr1 = ratio * batch_advantages
                surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * batch_advantages
                policy_loss = -torch.min(surr1, surr2).mean()

                # Track how often clipping occurs (helpful for tuning clip_epsilon)
                clip_fraction = torch.mean(((ratio - 1.0).abs() > self.clip_epsilon).float()).item()

                # Value loss
                value_loss = nn.functional.mse_loss(state_values, batch_returns)

                # Entropy bonus
                entropy_loss = -entropy.mean()

                # Total loss
                loss = (
                    policy_loss +
                    self.value_coef * value_loss +
                    self.entropy_coef * entropy_loss
                )

                # Backward pass
                self.optimizer.zero_grad()
                loss.backward()

                # Compute gradient norm before clipping (for monitoring)
                grad_norm = sum(p.grad.data.norm(2).item() ** 2 for p in self.policy.parameters() if p.grad is not None) ** 0.5

                nn.utils.clip_grad_norm_(self.policy.parameters(), self.max_grad_norm)
                self.optimizer.step()

                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                total_entropy += entropy.mean().item()
                total_clip_fraction += clip_fraction
                total_grad_norm += grad_norm

        # Update learning rate
        self.scheduler.step()

        # Clear buffer
        self.buffer = []

        # Calculate averages
        n_updates = self.n_epochs * (n_samples // self.batch_size)
        stats = {
            "policy_loss": total_policy_loss / n_updates,
            "value_loss": total_value_loss / n_updates,
            "entropy": total_entropy / n_updates,
            "learning_rate": self.optimizer.param_groups[0]["lr"],
            "clip_fraction": total_clip_fraction / n_updates,
            "gradient_norm": total_grad_norm / n_updates,
        }

        # Store stats
        self.training_stats["policy_loss"].append(stats["policy_loss"])
        self.training_stats["value_loss"].append(stats["value_loss"])
        self.training_stats["entropy"].append(stats["entropy"])

        return stats

    def train_episode(self, env, max_steps: int = 10000) -> Dict[str, float]:
        """Train for one episode"""
        state = env.reset()
        total_reward = 0
        step = 0

        while step < max_steps:
            # Select action
            action, log_prob, value = self.select_action(state)

            # Take step
            next_state, reward, done, info = env.step(action)

            # Store experience
            self.store_experience(state, action, reward, next_state, done, log_prob, value)

            total_reward += reward
            state = next_state
            step += 1

            if done:
                break

        # Update policy
        update_stats = self.update()

        # Get episode metrics
        metrics = env.get_performance_metrics()

        self.episode_count += 1
        self.training_stats["rewards"].append(total_reward)
        self.training_stats["episode_lengths"].append(step)

        return {
            **update_stats,
            "episode_reward": total_reward,
            "episode_length": step,
            **metrics
        }

    def save(self, path: str):
        """Save model and training state"""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)

        torch.save({
            "policy_state_dict": self.policy.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "scheduler_state_dict": self.scheduler.state_dict(),
            "episode_count": self.episode_count,
            "training_stats": self.training_stats,
        }, path)

        logger.info(f"Model saved to {path}")

    def load(self, path: str):
        """Load model and training state"""
        # PyTorch 2.6+ requires weights_only=False for backward compatibility
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)

        self.policy.load_state_dict(checkpoint["policy_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
        self.episode_count = checkpoint.get("episode_count", 0)
        self.training_stats = checkpoint.get("training_stats", self.training_stats)

        logger.info(f"Model loaded from {path}")


class A2CAgent(PPOAgent):
    """
    Advantage Actor-Critic (A2C) Agent

    Simpler variant without clipping, uses standard policy gradient
    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        entropy_coef: float = 0.05,  # Higher entropy for better exploration
        value_coef: float = 0.5,
        max_grad_norm: float = 0.5,
        hidden_dims: List[int] = [256, 128, 64],
        device: str = "auto"
    ):
        super().__init__(
            state_dim=state_dim,
            action_dim=action_dim,
            learning_rate=learning_rate,
            gamma=gamma,
            gae_lambda=1.0,  # No GAE, use simple advantage
            clip_epsilon=1.0,  # No clipping
            entropy_coef=entropy_coef,
            value_coef=value_coef,
            max_grad_norm=max_grad_norm,
            n_epochs=1,  # Single update
            batch_size=len(self.buffer) if self.buffer else 64,
            hidden_dims=hidden_dims,
            device=device
        )

    def update(self) -> Dict[str, float]:
        """A2C update (no clipping, single pass)"""
        if len(self.buffer) == 0:
            return {}

        # Extract experiences
        states = np.array([e.state for e in self.buffer])
        actions = np.array([e.action for e in self.buffer])
        rewards = [e.reward for e in self.buffer]
        dones = [e.done for e in self.buffer]
        values = [e.value for e in self.buffer]

        # Compute returns and advantages
        advantages, returns = self.compute_gae(rewards, values, dones)
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # Convert to tensors
        states_tensor = torch.FloatTensor(states).to(self.device)
        actions_tensor = torch.LongTensor(actions).to(self.device)
        advantages_tensor = torch.FloatTensor(advantages).to(self.device)
        returns_tensor = torch.FloatTensor(returns).to(self.device)

        # Forward pass
        log_probs, state_values, entropy = self.policy.evaluate(states_tensor, actions_tensor)

        # Policy loss (standard policy gradient)
        policy_loss = -(log_probs * advantages_tensor).mean()

        # Value loss
        value_loss = nn.functional.mse_loss(state_values, returns_tensor)

        # Entropy bonus
        entropy_loss = -entropy.mean()

        # Total loss
        loss = policy_loss + self.value_coef * value_loss + self.entropy_coef * entropy_loss

        # Backward pass
        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.policy.parameters(), self.max_grad_norm)
        self.optimizer.step()

        # Clear buffer
        self.buffer = []

        return {
            "policy_loss": policy_loss.item(),
            "value_loss": value_loss.item(),
            "entropy": entropy.mean().item(),
        }


# Factory function
def create_agent(
    agent_type: str,
    state_dim: int,
    action_dim: int,
    **kwargs
) -> PPOAgent:
    """Create RL agent by type"""
    agents = {
        "ppo": PPOAgent,
        "a2c": A2CAgent,
    }

    agent_class = agents.get(agent_type.lower(), PPOAgent)
    return agent_class(state_dim, action_dim, **kwargs)
