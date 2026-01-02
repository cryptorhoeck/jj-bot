#!/usr/bin/env python3
"""
RL Agent Training Script with Convergence Proof

This script trains the PPO agent and generates:
1. Training convergence metrics (returns, losses over time)
2. Performance comparison vs buy-and-hold baseline
3. Saved model checkpoints
4. Training results report

Usage:
    python scripts/train_rl_agent.py --episodes 500 --symbol BTC
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.rl.ppo_agent import PPOAgent, create_agent
from modules.rl.trading_env import TradingEnvironment, load_historical_data_sync

# Try to import matplotlib for plotting
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available, plots will be skipped")


class RLTrainer:
    """Comprehensive RL training with metrics and baselines"""

    def __init__(
        self,
        symbols: List[str] = None,
        initial_capital: float = 10000.0,
        models_dir: str = "./data/rl_models",
        results_dir: str = "./data/training_results"
    ):
        self.symbols = symbols or ["BTC/USD", "ETH/USD"]
        self.initial_capital = initial_capital
        self.models_dir = models_dir
        self.results_dir = results_dir

        os.makedirs(models_dir, exist_ok=True)
        os.makedirs(results_dir, exist_ok=True)

        # Training metrics
        self.episode_rewards: List[float] = []
        self.episode_lengths: List[int] = []
        self.policy_losses: List[float] = []
        self.value_losses: List[float] = []
        self.entropies: List[float] = []
        self.win_rates: List[float] = []
        self.sharpe_ratios: List[float] = []
        self.total_returns: List[float] = []

        # Buy-and-hold baseline
        self.buy_hold_returns: List[float] = []

    def calculate_buy_hold_return(self, env: TradingEnvironment) -> float:
        """Calculate buy-and-hold return for the same period"""
        try:
            # Get price data from environment
            if hasattr(env, 'price_history') and len(env.price_history) >= 2:
                start_price = env.price_history[0]
                end_price = env.price_history[-1]
                return (end_price - start_price) / start_price
            elif hasattr(env, 'current_price') and hasattr(env, 'initial_price'):
                return (env.current_price - env.initial_price) / env.initial_price
            else:
                return 0.0
        except Exception:
            return 0.0

    def train(
        self,
        num_episodes: int = 500,
        max_steps_per_episode: int = 1000,
        log_interval: int = 10,
        save_interval: int = 100,
        early_stop_threshold: float = None,
        use_synthetic_data: bool = False
    ) -> Dict[str, Any]:
        """
        Train the RL agent with comprehensive metrics.

        Args:
            num_episodes: Number of training episodes
            max_steps_per_episode: Max steps per episode
            log_interval: Print progress every N episodes
            save_interval: Save checkpoint every N episodes
            early_stop_threshold: Stop if avg reward exceeds this
            use_synthetic_data: Use synthetic data (no internet needed)

        Returns:
            Training results dictionary
        """
        print("=" * 60)
        print("RL AGENT TRAINING")
        print("=" * 60)
        print(f"Episodes:     {num_episodes}")
        print(f"Max Steps:    {max_steps_per_episode}")
        print(f"Symbols:      {', '.join(self.symbols)}")
        print(f"Capital:      ${self.initial_capital:,.2f}")
        print("=" * 60)

        # Create environment
        print("\nInitializing trading environment...")

        if use_synthetic_data:
            # Generate synthetic price data for training
            env = self._create_synthetic_env()
        else:
            # Try to load real data
            try:
                env = TradingEnvironment(
                    symbols=self.symbols,
                    initial_capital=self.initial_capital,
                    commission_rate=0.002,  # 0.2% realistic
                    slippage_rate=0.005,    # 0.5% realistic
                )
            except Exception as e:
                print(f"Failed to create environment with real data: {e}")
                print("Falling back to synthetic data...")
                env = self._create_synthetic_env()

        # Create agent
        state_dim = env.observation_space_size if hasattr(env, 'observation_space_size') else 50
        action_dim = env.action_space_size if hasattr(env, 'action_space_size') else 3

        print(f"\nCreating PPO agent...")
        print(f"  State dim:  {state_dim}")
        print(f"  Action dim: {action_dim}")

        agent = create_agent(
            agent_type="ppo",
            state_dim=state_dim,
            action_dim=action_dim,
            learning_rate=3e-4,
            gamma=0.99,
            gae_lambda=0.95,
            clip_epsilon=0.2,
            entropy_coef=0.05,
            n_epochs=10,
            batch_size=64
        )

        print(f"  Device:     {agent.device}")

        # Training loop
        print("\n" + "-" * 60)
        print("Starting training...")
        print("-" * 60)

        best_avg_reward = float('-inf')
        best_sharpe = float('-inf')
        rolling_rewards = []

        start_time = datetime.now()

        for episode in range(1, num_episodes + 1):
            # Reset environment
            state = env.reset()
            episode_reward = 0
            step = 0

            # Track episode metrics
            episode_trades = 0
            episode_wins = 0

            while step < max_steps_per_episode:
                # Select action
                action, log_prob, value = agent.select_action(state, training=True)

                # Take step
                next_state, reward, done, info = env.step(action)

                # Store experience
                agent.store_experience(
                    state=state,
                    action=action,
                    reward=reward,
                    next_state=next_state,
                    done=done,
                    log_prob=log_prob,
                    value=value
                )

                episode_reward += reward
                state = next_state
                step += 1

                # Track trades
                if info.get('trade_executed'):
                    episode_trades += 1
                    if info.get('trade_pnl', 0) > 0:
                        episode_wins += 1

                if done:
                    break

            # Update policy
            update_stats = agent.update()

            # Calculate metrics
            win_rate = episode_wins / max(episode_trades, 1)
            buy_hold_return = self.calculate_buy_hold_return(env)

            # Get environment metrics
            env_metrics = env.get_performance_metrics() if hasattr(env, 'get_performance_metrics') else {}
            total_return = env_metrics.get('total_return', episode_reward / self.initial_capital)
            sharpe = env_metrics.get('sharpe_ratio', 0)

            # Store metrics
            self.episode_rewards.append(episode_reward)
            self.episode_lengths.append(step)
            self.policy_losses.append(update_stats.get('policy_loss', 0))
            self.value_losses.append(update_stats.get('value_loss', 0))
            self.entropies.append(update_stats.get('entropy', 0))
            self.win_rates.append(win_rate)
            self.sharpe_ratios.append(sharpe)
            self.total_returns.append(total_return)
            self.buy_hold_returns.append(buy_hold_return)

            # Rolling average
            rolling_rewards.append(episode_reward)
            if len(rolling_rewards) > 100:
                rolling_rewards.pop(0)
            avg_reward = np.mean(rolling_rewards)

            # Track best performance
            if avg_reward > best_avg_reward:
                best_avg_reward = avg_reward
            if sharpe > best_sharpe:
                best_sharpe = sharpe

            # Log progress
            if episode % log_interval == 0:
                avg_win_rate = np.mean(self.win_rates[-log_interval:])
                avg_return = np.mean(self.total_returns[-log_interval:]) * 100
                avg_bh = np.mean(self.buy_hold_returns[-log_interval:]) * 100

                print(f"Episode {episode:4d}/{num_episodes} | "
                      f"Reward: {episode_reward:8.2f} | "
                      f"Avg: {avg_reward:8.2f} | "
                      f"Win: {avg_win_rate*100:5.1f}% | "
                      f"Return: {avg_return:+6.2f}% | "
                      f"B&H: {avg_bh:+6.2f}%")

            # Save checkpoint
            if episode % save_interval == 0:
                checkpoint_path = os.path.join(
                    self.models_dir,
                    f"ppo_checkpoint_ep{episode}.pt"
                )
                agent.save(checkpoint_path)
                print(f"  [Checkpoint saved: {checkpoint_path}]")

            # Early stopping
            if early_stop_threshold and avg_reward > early_stop_threshold:
                print(f"\nEarly stopping: avg reward {avg_reward:.2f} > {early_stop_threshold}")
                break

        # Training complete
        elapsed = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 60)
        print("TRAINING COMPLETE")
        print("=" * 60)
        print(f"Episodes:     {episode}")
        print(f"Duration:     {elapsed/60:.1f} minutes")
        print(f"Best Avg:     {best_avg_reward:.2f}")
        print(f"Best Sharpe:  {best_sharpe:.2f}")

        # Save final model
        final_model_path = os.path.join(self.models_dir, "ppo_final.pt")
        agent.save(final_model_path)
        print(f"Final model saved: {final_model_path}")

        # Generate results
        results = self._generate_results(agent, episode, elapsed)

        # Save results
        self._save_results(results)

        # Generate plots
        if MATPLOTLIB_AVAILABLE:
            self._generate_plots(results)

        return results

    def _create_synthetic_env(self) -> 'TradingEnvironment':
        """Create environment with synthetic data for testing"""
        print("Generating synthetic price data...")

        # Generate synthetic OHLCV data
        np.random.seed(42)
        num_candles = 5000
        initial_price = 50000.0

        prices = [initial_price]
        for _ in range(num_candles - 1):
            # Random walk with drift
            change = np.random.normal(0.0001, 0.02)  # Small positive drift, 2% volatility
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 100))  # Floor at $100

        prices = np.array(prices)

        # Create OHLCV array
        ohlcv = np.column_stack([
            np.arange(num_candles),  # timestamp
            prices * 0.999,  # open
            prices * 1.005,  # high
            prices * 0.995,  # low
            prices,          # close
            np.random.uniform(100, 1000, num_candles)  # volume
        ])

        # Create environment with synthetic data
        from modules.rl.trading_env import TradingEnvironment
        env = TradingEnvironment(
            symbols=["BTC/USD"],
            initial_capital=self.initial_capital,
            commission_rate=0.002,
            slippage_rate=0.005,
            use_synthetic=True
        )

        # Inject synthetic data
        if hasattr(env, '_inject_data'):
            env._inject_data({"BTC/USD": ohlcv})

        print(f"Created synthetic environment with {num_candles} candles")
        return env

    def _generate_results(self, agent: PPOAgent, episodes: int, elapsed: float) -> Dict:
        """Generate comprehensive results dictionary"""
        # Calculate statistics
        avg_reward = np.mean(self.episode_rewards)
        std_reward = np.std(self.episode_rewards)
        final_avg_reward = np.mean(self.episode_rewards[-100:]) if len(self.episode_rewards) >= 100 else avg_reward

        avg_return = np.mean(self.total_returns)
        avg_bh_return = np.mean(self.buy_hold_returns)
        outperformance = avg_return - avg_bh_return

        avg_win_rate = np.mean(self.win_rates)
        avg_sharpe = np.mean(self.sharpe_ratios[-100:]) if len(self.sharpe_ratios) >= 100 else np.mean(self.sharpe_ratios)

        # Convergence check
        if len(self.episode_rewards) >= 100:
            first_quarter = np.mean(self.episode_rewards[:len(self.episode_rewards)//4])
            last_quarter = np.mean(self.episode_rewards[-len(self.episode_rewards)//4:])
            converged = last_quarter > first_quarter * 1.1  # 10% improvement
        else:
            converged = False

        return {
            "training_info": {
                "episodes": episodes,
                "duration_seconds": elapsed,
                "symbols": self.symbols,
                "initial_capital": self.initial_capital,
                "timestamp": datetime.now().isoformat()
            },
            "performance": {
                "avg_episode_reward": float(avg_reward),
                "std_episode_reward": float(std_reward),
                "final_avg_reward": float(final_avg_reward),
                "avg_total_return": float(avg_return),
                "avg_win_rate": float(avg_win_rate),
                "avg_sharpe_ratio": float(avg_sharpe),
                "best_episode_reward": float(max(self.episode_rewards)),
                "worst_episode_reward": float(min(self.episode_rewards))
            },
            "vs_baseline": {
                "strategy_return": float(avg_return),
                "buy_hold_return": float(avg_bh_return),
                "outperformance": float(outperformance),
                "beats_baseline": outperformance > 0
            },
            "convergence": {
                "converged": converged,
                "final_policy_loss": float(self.policy_losses[-1]) if self.policy_losses else 0,
                "final_value_loss": float(self.value_losses[-1]) if self.value_losses else 0,
                "final_entropy": float(self.entropies[-1]) if self.entropies else 0
            },
            "metrics_history": {
                "episode_rewards": [float(x) for x in self.episode_rewards],
                "policy_losses": [float(x) for x in self.policy_losses],
                "value_losses": [float(x) for x in self.value_losses],
                "entropies": [float(x) for x in self.entropies],
                "win_rates": [float(x) for x in self.win_rates],
                "sharpe_ratios": [float(x) for x in self.sharpe_ratios],
                "total_returns": [float(x) for x in self.total_returns],
                "buy_hold_returns": [float(x) for x in self.buy_hold_returns]
            }
        }

    def _save_results(self, results: Dict):
        """Save training results to JSON"""
        results_path = os.path.join(
            self.results_dir,
            f"training_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        # Save with limited history for readability
        save_results = {k: v for k, v in results.items() if k != "metrics_history"}
        save_results["metrics_summary"] = {
            "episodes": len(results["metrics_history"]["episode_rewards"]),
            "final_100_avg_reward": np.mean(results["metrics_history"]["episode_rewards"][-100:]),
            "final_100_avg_return": np.mean(results["metrics_history"]["total_returns"][-100:])
        }

        with open(results_path, 'w') as f:
            json.dump(save_results, f, indent=2)

        print(f"Results saved: {results_path}")

        # Also save full metrics history
        full_results_path = results_path.replace('.json', '_full.json')
        with open(full_results_path, 'w') as f:
            json.dump(results, f)

        print(f"Full metrics saved: {full_results_path}")

    def _generate_plots(self, results: Dict):
        """Generate training plots"""
        history = results["metrics_history"]

        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle("RL Training Results", fontsize=14)

        # 1. Episode Rewards
        ax = axes[0, 0]
        ax.plot(history["episode_rewards"], alpha=0.3, label="Raw")
        # Rolling average
        window = min(50, len(history["episode_rewards"]) // 10)
        if window > 1:
            rolling = np.convolve(history["episode_rewards"], np.ones(window)/window, mode='valid')
            ax.plot(range(window-1, len(history["episode_rewards"])), rolling, label=f"{window}-ep avg")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Reward")
        ax.set_title("Episode Rewards")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 2. Policy Loss
        ax = axes[0, 1]
        ax.plot(history["policy_losses"])
        ax.set_xlabel("Episode")
        ax.set_ylabel("Loss")
        ax.set_title("Policy Loss")
        ax.grid(True, alpha=0.3)

        # 3. Value Loss
        ax = axes[0, 2]
        ax.plot(history["value_losses"])
        ax.set_xlabel("Episode")
        ax.set_ylabel("Loss")
        ax.set_title("Value Loss")
        ax.grid(True, alpha=0.3)

        # 4. Win Rate
        ax = axes[1, 0]
        ax.plot(history["win_rates"])
        ax.axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label="50%")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Win Rate")
        ax.set_title("Win Rate")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 5. Returns vs Buy & Hold
        ax = axes[1, 1]
        ax.plot(history["total_returns"], label="Strategy")
        ax.plot(history["buy_hold_returns"], label="Buy & Hold", alpha=0.7)
        ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        ax.set_xlabel("Episode")
        ax.set_ylabel("Return")
        ax.set_title("Strategy vs Buy & Hold")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 6. Entropy (exploration)
        ax = axes[1, 2]
        ax.plot(history["entropies"])
        ax.set_xlabel("Episode")
        ax.set_ylabel("Entropy")
        ax.set_title("Policy Entropy (Exploration)")
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        plot_path = os.path.join(
            self.results_dir,
            f"training_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        plt.savefig(plot_path, dpi=150)
        plt.close()

        print(f"Plot saved: {plot_path}")


def main():
    parser = argparse.ArgumentParser(description="Train RL agent with convergence metrics")
    parser.add_argument("--episodes", "-e", type=int, default=500, help="Number of episodes")
    parser.add_argument("--steps", "-s", type=int, default=1000, help="Max steps per episode")
    parser.add_argument("--symbols", nargs="+", default=["BTC/USD"], help="Trading symbols")
    parser.add_argument("--capital", type=float, default=10000, help="Initial capital")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data")
    parser.add_argument("--log-interval", type=int, default=10, help="Log every N episodes")
    parser.add_argument("--save-interval", type=int, default=100, help="Save every N episodes")

    args = parser.parse_args()

    trainer = RLTrainer(
        symbols=args.symbols,
        initial_capital=args.capital
    )

    results = trainer.train(
        num_episodes=args.episodes,
        max_steps_per_episode=args.steps,
        log_interval=args.log_interval,
        save_interval=args.save_interval,
        use_synthetic_data=args.synthetic
    )

    # Print summary
    print("\n" + "=" * 60)
    print("TRAINING SUMMARY")
    print("=" * 60)

    perf = results["performance"]
    baseline = results["vs_baseline"]
    conv = results["convergence"]

    print(f"\nPerformance:")
    print(f"  Average Reward:     {perf['avg_episode_reward']:.2f}")
    print(f"  Final Avg Reward:   {perf['final_avg_reward']:.2f}")
    print(f"  Average Win Rate:   {perf['avg_win_rate']*100:.1f}%")
    print(f"  Average Sharpe:     {perf['avg_sharpe_ratio']:.2f}")

    print(f"\nVs Buy & Hold:")
    print(f"  Strategy Return:    {baseline['strategy_return']*100:+.2f}%")
    print(f"  Buy & Hold Return:  {baseline['buy_hold_return']*100:+.2f}%")
    print(f"  Outperformance:     {baseline['outperformance']*100:+.2f}%")
    print(f"  Beats Baseline:     {'YES' if baseline['beats_baseline'] else 'NO'}")

    print(f"\nConvergence:")
    print(f"  Converged:          {'YES' if conv['converged'] else 'NO'}")
    print(f"  Final Policy Loss:  {conv['final_policy_loss']:.4f}")
    print(f"  Final Value Loss:   {conv['final_value_loss']:.4f}")

    print("=" * 60)


if __name__ == "__main__":
    main()
