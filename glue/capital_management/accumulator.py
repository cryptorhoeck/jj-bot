"""
Accumulator - Harvest Account Management

Tracks harvest proceeds and monitors deployment trigger threshold.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from .models import (
    HarvestAccount,
    HarvestEntry,
    DeploymentAlert,
    get_account_path,
)

logger = logging.getLogger(__name__)


class Accumulator:
    """
    Manages the Harvest Account for accumulating profits.

    Tracks running balance and triggers deployment when threshold is met.
    """

    def __init__(self, deployment_trigger: float = 1000.0):
        self.account = HarvestAccount(deployment_trigger=deployment_trigger)
        self._load_account()

    def _load_account(self):
        """Load account state from storage"""
        account_path = get_account_path()
        if account_path.exists():
            try:
                with open(account_path) as f:
                    data = json.load(f)
                    self.account = HarvestAccount.from_dict(data)
                logger.info(
                    f"Loaded harvest account: ${self.account.balance:.2f} "
                    f"(trigger: ${self.account.deployment_trigger:.2f})"
                )
            except Exception as e:
                logger.error(f"Failed to load harvest account: {e}")

    def _save_account(self):
        """Save account state to storage"""
        account_path = get_account_path()
        account_path.parent.mkdir(parents=True, exist_ok=True)

        with open(account_path, "w") as f:
            json.dump(self.account.to_dict(), f, indent=2)

    def deposit(
        self,
        entry: HarvestEntry
    ) -> Optional[DeploymentAlert]:
        """
        Deposit harvest proceeds into the account.

        Args:
            entry: The harvest entry with proceeds

        Returns:
            DeploymentAlert if trigger is met, None otherwise
        """
        alert = self.account.deposit(
            amount=entry.proceeds,
            source_symbol=entry.symbol,
            trigger=entry.trigger,
        )

        self._save_account()

        logger.info(
            f"Deposited ${entry.proceeds:.2f} from {entry.symbol} harvest. "
            f"New balance: ${self.account.balance:.2f}"
        )

        if alert:
            logger.info(
                f"DEPLOYMENT TRIGGER MET! Balance: ${alert.balance:.2f} >= "
                f"${alert.trigger_amount:.2f}"
            )

        return alert

    def get_balance(self) -> float:
        """Get current account balance"""
        return self.account.balance

    def get_status(self) -> Dict:
        """
        Get detailed account status.

        Returns:
            Dictionary with balance, progress, and deployment info
        """
        balance = self.account.balance
        trigger = self.account.deployment_trigger
        progress_pct = (balance / trigger * 100) if trigger > 0 else 0

        return {
            "balance": round(balance, 2),
            "deployment_trigger": trigger,
            "progress_pct": round(min(100, progress_pct), 1),
            "amount_to_trigger": round(max(0, trigger - balance), 2),
            "deployment_ready": balance >= trigger,
            "total_deposited": round(self.account.total_deposited, 2),
            "total_deployed": round(self.account.total_deployed, 2),
            "cycles_completed": self.account.deployment_cycles_completed,
        }

    def mark_deployed(self, amount: float):
        """
        Mark funds as deployed.

        Called after deployment cycle is executed.

        Args:
            amount: Amount deployed
        """
        self.account.deploy(amount)
        self._save_account()

        logger.info(
            f"Marked ${amount:.2f} as deployed. "
            f"New balance: ${self.account.balance:.2f}"
        )

    def reset_balance(self):
        """Reset balance to zero after deployment"""
        self.account.reset()
        self._save_account()
        logger.info("Harvest account balance reset to $0.00")

    def set_deployment_trigger(self, amount: float):
        """
        Update the deployment trigger amount.

        Args:
            amount: New trigger amount
        """
        self.account.deployment_trigger = amount
        self._save_account()
        logger.info(f"Deployment trigger updated to ${amount:.2f}")

    def check_deployment_ready(self) -> Optional[DeploymentAlert]:
        """
        Check if deployment trigger is met.

        Returns:
            DeploymentAlert if ready, None otherwise
        """
        if self.account.balance >= self.account.deployment_trigger:
            return DeploymentAlert(
                balance=self.account.balance,
                trigger_amount=self.account.deployment_trigger,
                triggered_at=datetime.now().isoformat(),
            )
        return None


# Global instance
accumulator = Accumulator()
