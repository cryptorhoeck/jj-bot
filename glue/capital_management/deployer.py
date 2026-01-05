"""
Deployer - Deployment Cycle Management

Handles deployment of accumulated funds to hard assets (BTC and Gold).

Deployment Split:
- 50% to BTC (via Wealthsimple Crypto)
- 50% to MNT - Royal Canadian Mint Gold Reserve (via Wealthsimple Trade)
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from .models import (
    DeploymentCycle,
    DeploymentAlert,
    get_deployment_log_path,
)

logger = logging.getLogger(__name__)


class Deployer:
    """
    Manages deployment cycles for converting harvest proceeds to hard assets.

    Deployment is semi-automatic:
    - System tracks when deployment is ready
    - User confirms and executes on Wealthsimple
    - System records the deployment
    """

    # Deployment allocation
    BTC_ALLOCATION = 0.5  # 50% to BTC
    MNT_ALLOCATION = 0.5  # 50% to Gold (MNT)

    def __init__(self):
        self.deployment_log: List[DeploymentCycle] = []
        self.pending_deployment: Optional[DeploymentCycle] = None
        self._load_deployments()

    def _load_deployments(self):
        """Load deployment history from storage"""
        deployment_path = get_deployment_log_path()
        if deployment_path.exists():
            try:
                with open(deployment_path) as f:
                    data = json.load(f)
                    self.deployment_log = [
                        DeploymentCycle.from_dict(cycle)
                        for cycle in data.get("cycles", [])
                    ]
                    # Load pending deployment if exists
                    pending = data.get("pending")
                    if pending:
                        self.pending_deployment = DeploymentCycle.from_dict(pending)

                logger.info(f"Loaded {len(self.deployment_log)} deployment cycles")
            except Exception as e:
                logger.error(f"Failed to load deployments: {e}")

    def _save_deployments(self):
        """Save deployment history to storage"""
        deployment_path = get_deployment_log_path()
        deployment_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "cycles": [cycle.to_dict() for cycle in self.deployment_log],
            "pending": self.pending_deployment.to_dict() if self.pending_deployment else None,
        }

        with open(deployment_path, "w") as f:
            json.dump(data, f, indent=2)

    def create_deployment(
        self,
        harvest_balance: float,
        btc_price: Optional[float] = None,
        mnt_price: Optional[float] = None,
    ) -> DeploymentCycle:
        """
        Create a new deployment cycle.

        Args:
            harvest_balance: Amount to deploy from harvest account
            btc_price: Current BTC price (for calculating units)
            mnt_price: Current MNT price (for calculating units)

        Returns:
            The created DeploymentCycle (not yet executed)
        """
        cycle_number = len(self.deployment_log) + 1

        btc_amount = harvest_balance * self.BTC_ALLOCATION
        mnt_amount = harvest_balance * self.MNT_ALLOCATION

        cycle = DeploymentCycle(
            cycle_number=cycle_number,
            date=datetime.now().isoformat(),
            harvest_balance=harvest_balance,
            btc_amount=btc_amount,
            btc_price=btc_price or 0.0,
            btc_units=btc_amount / btc_price if btc_price and btc_price > 0 else 0.0,
            mnt_amount=mnt_amount,
            mnt_price=mnt_price or 0.0,
            mnt_units=mnt_amount / mnt_price if mnt_price and mnt_price > 0 else 0.0,
            executed=False,
        )

        self.pending_deployment = cycle
        self._save_deployments()

        logger.info(
            f"Created deployment cycle #{cycle_number}: "
            f"${btc_amount:.2f} BTC + ${mnt_amount:.2f} MNT"
        )

        return cycle

    def execute_deployment(
        self,
        btc_price: Optional[float] = None,
        mnt_price: Optional[float] = None,
        notes: str = "",
    ) -> Optional[DeploymentCycle]:
        """
        Mark pending deployment as executed.

        Called after user confirms execution on Wealthsimple.

        Args:
            btc_price: Actual execution price for BTC
            mnt_price: Actual execution price for MNT
            notes: Execution notes

        Returns:
            The executed DeploymentCycle, or None if no pending deployment
        """
        if not self.pending_deployment:
            logger.warning("No pending deployment to execute")
            return None

        cycle = self.pending_deployment

        # Update with actual prices if provided
        if btc_price:
            cycle.btc_price = btc_price
            cycle.btc_units = cycle.btc_amount / btc_price if btc_price > 0 else 0.0

        if mnt_price:
            cycle.mnt_price = mnt_price
            cycle.mnt_units = cycle.mnt_amount / mnt_price if mnt_price > 0 else 0.0

        cycle.executed = True
        cycle.date = datetime.now().isoformat()  # Update to execution time
        cycle.notes = notes

        # Move to log
        self.deployment_log.append(cycle)
        self.pending_deployment = None

        self._save_deployments()

        logger.info(
            f"Executed deployment cycle #{cycle.cycle_number}: "
            f"{cycle.btc_units:.6f} BTC @ ${cycle.btc_price:.2f}, "
            f"{cycle.mnt_units:.4f} MNT @ ${cycle.mnt_price:.2f}"
        )

        return cycle

    def cancel_pending(self) -> bool:
        """Cancel pending deployment"""
        if self.pending_deployment:
            logger.info(f"Cancelled pending deployment #{self.pending_deployment.cycle_number}")
            self.pending_deployment = None
            self._save_deployments()
            return True
        return False

    def get_pending(self) -> Optional[Dict]:
        """Get pending deployment details"""
        if not self.pending_deployment:
            return None
        return self.pending_deployment.to_dict()

    def get_deployment_history(self, limit: int = 20) -> List[Dict]:
        """Get deployment history"""
        cycles = self.deployment_log[-limit:]
        return [cycle.to_dict() for cycle in reversed(cycles)]

    def get_holdings(self) -> Dict:
        """
        Get cumulative hard asset holdings from all deployments.

        Returns:
            Dictionary with total BTC and MNT holdings
        """
        total_btc = sum(c.btc_units for c in self.deployment_log if c.executed)
        total_mnt = sum(c.mnt_units for c in self.deployment_log if c.executed)
        total_btc_cost = sum(c.btc_amount for c in self.deployment_log if c.executed)
        total_mnt_cost = sum(c.mnt_amount for c in self.deployment_log if c.executed)

        # Calculate average costs
        avg_btc_cost = total_btc_cost / total_btc if total_btc > 0 else 0.0
        avg_mnt_cost = total_mnt_cost / total_mnt if total_mnt > 0 else 0.0

        return {
            "btc": {
                "units": round(total_btc, 8),
                "total_cost": round(total_btc_cost, 2),
                "avg_cost_per_unit": round(avg_btc_cost, 2),
            },
            "mnt": {
                "units": round(total_mnt, 4),
                "total_cost": round(total_mnt_cost, 2),
                "avg_cost_per_unit": round(avg_mnt_cost, 2),
            },
            "total_deployed": round(total_btc_cost + total_mnt_cost, 2),
            "deployment_count": len([c for c in self.deployment_log if c.executed]),
        }

    def get_summary(self) -> Dict:
        """Get deployment summary"""
        holdings = self.get_holdings()

        return {
            "total_cycles": len(self.deployment_log),
            "pending_deployment": self.pending_deployment is not None,
            "holdings": holdings,
            "last_deployment": (
                self.deployment_log[-1].to_dict()
                if self.deployment_log else None
            ),
        }


# Global instance
deployer = Deployer()
