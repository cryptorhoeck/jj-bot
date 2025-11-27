#!/usr/bin/env python3
"""
Standalone Training Script for JJ-Bot Pro

This script runs RL training in a separate process so the main API stays responsive.
Progress is saved to data/training_metrics.json which the dashboard can poll.

Usage:
    python train_model.py --episodes 100
    python train_model.py --episodes 500 --resume
"""

import os
import sys
import json
import argparse
import logging
import signal
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "logs" / "training.log", mode="a")
    ]
)
logger = logging.getLogger("train_model")

# Global flag for graceful shutdown
_shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global _shutdown_requested
    logger.info("Shutdown signal received, finishing current episode...")
    _shutdown_requested = True


def get_training_status_path() -> Path:
    """Path to training status file (for API to poll)"""
    return PROJECT_ROOT / "data" / "training_status.json"


def get_training_metrics_path() -> Path:
    """Path to training metrics file"""
    return PROJECT_ROOT / "data" / "training_metrics.json"


def get_config_path() -> Path:
    """Path to bot config file"""
    return PROJECT_ROOT / "config" / "bot_config.json"


def load_config() -> dict:
    """Load bot configuration"""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    """Save bot configuration"""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def load_training_metrics() -> dict:
    """Load existing training metrics"""
    metrics_path = get_training_metrics_path()
    default_metrics = {
        "episode_count": 0,
        "total_win_rate": 0.0,
        "total_profit_factor": 0.0,
        "total_reward": 0.0,
        "total_trades": 0
    }

    if metrics_path.exists():
        try:
            with open(metrics_path) as f:
                loaded = json.load(f)
                for key in default_metrics:
                    if key not in loaded:
                        loaded[key] = default_metrics[key]
                return loaded
        except Exception as e:
            logger.warning(f"Failed to load training metrics: {e}")

    return default_metrics


def save_training_metrics(metrics: dict):
    """Save training metrics"""
    metrics_path = get_training_metrics_path()
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)


def update_training_status(status: dict):
    """Update training status file for API to poll"""
    status_path = get_training_status_path()
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status["last_updated"] = datetime.now().isoformat()
    with open(status_path, "w") as f:
        json.dump(status, f, indent=2)


def calculate_trading_iq(metrics: dict) -> tuple:
    """Calculate Trading IQ from metrics"""
    if metrics["episode_count"] == 0:
        return 0, "Untrained"

    avg_win_rate = metrics["total_win_rate"] / metrics["episode_count"]
    avg_profit_factor = metrics["total_profit_factor"] / metrics["episode_count"]
    avg_reward = metrics["total_reward"] / metrics["episode_count"]

    # Score calculation
    win_rate_score = min(40, (avg_win_rate / 0.5) * 40)
    profit_factor_score = min(30, (avg_profit_factor / 3.0) * 30)
    reward_normalized = max(0, min(100, avg_reward + 100)) / 100
    reward_score = reward_normalized * 30

    iq = int(win_rate_score + profit_factor_score + reward_score)

    if iq < 20:
        level = "Novice"
    elif iq < 40:
        level = "Beginner"
    elif iq < 60:
        level = "Intermediate"
    elif iq < 75:
        level = "Advanced"
    elif iq < 90:
        level = "Expert"
    else:
        level = "Master"

    return iq, level


def run_training(episodes: int, resume: bool = True):
    """Run the training loop"""
    global _shutdown_requested

    logger.info("=" * 50)
    logger.info("JJ-Bot Pro Training Starting...")
    logger.info(f"Episodes: {episodes}")
    logger.info(f"Resume: {resume}")
    logger.info("=" * 50)

    # Update status: starting
    update_training_status({
        "is_training": True,
        "status": "initializing",
        "current_episode": 0,
        "total_episodes": episodes,
        "progress_pct": 0,
        "pid": os.getpid()
    })

    try:
        # Import RL modules
        from modules.rl import TradingEnvironment, create_agent

        config = load_config()
        model_path = config.get("rl_model_path", "models/ppo_agent.pt")

        # Create environment and agent
        logger.info("Initializing RL environment...")
        env = TradingEnvironment(
            initial_balance=config.get("initial_capital", 10000),
            max_position_size=config.get("max_position_pct", 0.1)
        )

        agent = create_agent(
            "ppo",
            state_dim=env.observation_space_dim,
            action_dim=env.action_space_dim
        )

        # Load existing model if resuming
        if resume and os.path.exists(model_path):
            agent.load(model_path)
            logger.info(f"Loaded existing model from {model_path}")
        else:
            logger.info("Starting with fresh model")

        # Load existing metrics if resuming
        if resume:
            training_metrics = load_training_metrics()
            logger.info(f"Resuming from episode {training_metrics['episode_count']}")
        else:
            training_metrics = {
                "episode_count": 0,
                "total_win_rate": 0.0,
                "total_profit_factor": 0.0,
                "total_reward": 0.0,
                "total_trades": 0
            }

        start_time = datetime.now()
        completed_episodes = 0

        # Training loop
        for episode in range(episodes):
            if _shutdown_requested:
                logger.info(f"Shutdown requested at episode {episode}")
                break

            # Train one episode
            metrics = agent.train_episode(env)
            completed_episodes = episode + 1

            # Update cumulative metrics
            win_rate = metrics.get('win_rate', 0)
            profit_factor = metrics.get('profit_factor', 1.0)

            training_metrics["episode_count"] += 1
            training_metrics["total_win_rate"] += win_rate
            training_metrics["total_profit_factor"] += profit_factor
            training_metrics["total_reward"] += metrics.get('episode_reward', 0)
            training_metrics["total_trades"] += metrics.get('total_trades', 0)

            # Calculate IQ
            iq, level = calculate_trading_iq(training_metrics)

            # Calculate averages
            avg_win_rate = (training_metrics["total_win_rate"] / training_metrics["episode_count"]) * 100
            avg_profit_factor = training_metrics["total_profit_factor"] / training_metrics["episode_count"]
            avg_reward = training_metrics["total_reward"] / training_metrics["episode_count"]

            # Update status file every episode (for dashboard to poll)
            update_training_status({
                "is_training": True,
                "status": "training",
                "current_episode": completed_episodes,
                "total_episodes": episodes,
                "progress_pct": (completed_episodes / episodes) * 100,
                "last_reward": metrics.get('episode_reward', 0),
                "last_pnl": metrics.get('total_pnl', 0),
                "last_win_rate": win_rate * 100,
                "trading_iq": iq,
                "expertise_level": level,
                "avg_win_rate": avg_win_rate,
                "avg_profit_factor": avg_profit_factor,
                "avg_reward": avg_reward,
                "total_simulated_trades": training_metrics["total_trades"],
                "total_episodes_trained": training_metrics["episode_count"],
                "pid": os.getpid(),
                "start_time": start_time.isoformat()
            })

            # Log progress every 10 episodes
            if episode % 10 == 0:
                logger.info(
                    f"Episode {episode}/{episodes} | "
                    f"Reward: {metrics.get('episode_reward', 0):.2f} | "
                    f"P&L: ${metrics.get('total_pnl', 0):.2f} | "
                    f"Win Rate: {metrics.get('win_rate', 0):.1%} | "
                    f"IQ: {iq}"
                )
                # Save metrics periodically
                save_training_metrics(training_metrics)

            # Save model periodically
            if episode % 50 == 0 and episode > 0:
                os.makedirs(os.path.dirname(model_path), exist_ok=True)
                agent.save(model_path)
                logger.info(f"Model checkpoint saved at episode {episode}")

        # Final save
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        agent.save(model_path)
        save_training_metrics(training_metrics)

        # Update config with final IQ
        iq, level = calculate_trading_iq(training_metrics)
        config["trading_iq"] = iq
        config["expertise_level"] = level
        config["mode"] = "paper"  # Switch back to paper mode
        save_config(config)

        runtime = datetime.now() - start_time

        # Final status
        update_training_status({
            "is_training": False,
            "status": "completed",
            "current_episode": completed_episodes,
            "total_episodes": episodes,
            "progress_pct": 100,
            "trading_iq": iq,
            "expertise_level": level,
            "avg_win_rate": avg_win_rate,
            "avg_profit_factor": avg_profit_factor,
            "total_simulated_trades": training_metrics["total_trades"],
            "total_episodes_trained": training_metrics["episode_count"],
            "runtime_seconds": runtime.total_seconds(),
            "model_path": model_path
        })

        logger.info("=" * 50)
        logger.info("TRAINING COMPLETE")
        logger.info("=" * 50)
        logger.info(f"Runtime: {runtime}")
        logger.info(f"Episodes: {completed_episodes}/{episodes}")
        logger.info(f"Total Simulated Trades: {training_metrics['total_trades']:,}")
        logger.info(f"Avg Win Rate: {avg_win_rate:.1f}%")
        logger.info(f"Avg Profit Factor: {avg_profit_factor:.2f}")
        logger.info(f"Trading IQ: {iq} ({level})")
        logger.info(f"Model saved to: {model_path}")
        logger.info("=" * 50)

        return True

    except Exception as e:
        logger.exception(f"Training error: {e}")
        update_training_status({
            "is_training": False,
            "status": "error",
            "error": str(e)
        })
        return False


def main():
    parser = argparse.ArgumentParser(description="Train JJ-Bot Pro RL model")
    parser.add_argument("--episodes", type=int, default=100, help="Number of training episodes")
    parser.add_argument("--resume", action="store_true", default=True, help="Resume from existing model/metrics")
    parser.add_argument("--fresh", action="store_true", help="Start fresh (ignore existing model/metrics)")

    args = parser.parse_args()

    # Create logs directory
    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)
    (PROJECT_ROOT / "data").mkdir(exist_ok=True)
    (PROJECT_ROOT / "models").mkdir(exist_ok=True)

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run training
    resume = not args.fresh
    success = run_training(args.episodes, resume=resume)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
