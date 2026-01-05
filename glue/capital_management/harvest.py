"""
Harvest Manager - Profit Harvesting Logic

Checks positions for harvest triggers and manages the harvest process.

Harvest Rules:
- +20% gain: Sell 25% of position
- +50% gain: Sell 25% of position
- +100% gain: Sell 25% of position
- Remaining 25% rides forever ("free shares")
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .models import (
    HarvestPosition,
    HarvestAction,
    HarvestEntry,
    HarvestTrigger,
    get_positions_path,
    get_harvest_log_path,
)

logger = logging.getLogger(__name__)


class HarvestManager:
    """
    Manages profit harvesting for positions.

    Tracks positions and checks for harvest trigger conditions.
    """

    # Harvest thresholds
    THRESHOLDS = [
        (1.0, HarvestTrigger.HUNDRED, "harvested_100"),   # 100% gain
        (0.5, HarvestTrigger.FIFTY, "harvested_50"),       # 50% gain
        (0.2, HarvestTrigger.TWENTY, "harvested_20"),      # 20% gain
    ]

    HARVEST_SELL_PCT = 0.25  # 25% of position at each threshold

    def __init__(self):
        self.positions: Dict[str, HarvestPosition] = {}
        self.harvest_log: List[HarvestEntry] = []
        self._load_data()

    def _load_data(self):
        """Load positions and harvest log from storage"""
        # Load positions
        positions_path = get_positions_path()
        if positions_path.exists():
            try:
                with open(positions_path) as f:
                    data = json.load(f)
                    for pos_data in data.get("positions", []):
                        pos = HarvestPosition.from_dict(pos_data)
                        self.positions[pos.symbol] = pos
                logger.info(f"Loaded {len(self.positions)} harvest positions")
            except Exception as e:
                logger.error(f"Failed to load positions: {e}")

        # Load harvest log
        harvest_log_path = get_harvest_log_path()
        if harvest_log_path.exists():
            try:
                with open(harvest_log_path) as f:
                    data = json.load(f)
                    self.harvest_log = [
                        HarvestEntry.from_dict(entry)
                        for entry in data.get("entries", [])
                    ]
                logger.info(f"Loaded {len(self.harvest_log)} harvest log entries")
            except Exception as e:
                logger.error(f"Failed to load harvest log: {e}")

    def _save_positions(self):
        """Save positions to storage"""
        positions_path = get_positions_path()
        positions_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "positions": [pos.to_dict() for pos in self.positions.values()]
        }

        with open(positions_path, "w") as f:
            json.dump(data, f, indent=2)

    def _save_harvest_log(self):
        """Save harvest log to storage"""
        harvest_log_path = get_harvest_log_path()
        harvest_log_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "entries": [entry.to_dict() for entry in self.harvest_log]
        }

        with open(harvest_log_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_position(
        self,
        symbol: str,
        shares: float,
        cost_per_share: float,
        entry_source: str = "jj-bot",
        notes: str = "",
    ) -> HarvestPosition:
        """
        Add a new position to track for harvesting.

        Args:
            symbol: Trading symbol
            shares: Number of shares/units bought
            cost_per_share: Average cost per share
            entry_source: Signal source that triggered entry
            notes: Optional notes

        Returns:
            The created HarvestPosition
        """
        position = HarvestPosition(
            symbol=symbol,
            buy_date=datetime.now().strftime("%Y-%m-%d"),
            shares_bought=shares,
            cost_per_share=cost_per_share,
            shares_remaining=shares,
            entry_source=entry_source,
            notes=notes,
        )

        # If position already exists, update it (add to existing)
        if symbol in self.positions:
            existing = self.positions[symbol]
            # Weighted average cost
            total_shares = existing.shares_remaining + shares
            total_cost = (existing.shares_remaining * existing.cost_per_share +
                         shares * cost_per_share)
            existing.cost_per_share = total_cost / total_shares if total_shares > 0 else cost_per_share
            existing.shares_remaining = total_shares
            existing.shares_bought += shares
            position = existing
        else:
            self.positions[symbol] = position

        self._save_positions()
        logger.info(f"Added position: {symbol}, {shares} shares @ ${cost_per_share:.2f}")

        return position

    def check_harvest_trigger(
        self,
        symbol: str,
        current_price: float
    ) -> Optional[HarvestAction]:
        """
        Check if a position has hit a harvest trigger.

        Checks thresholds in descending order (100%, 50%, 20%)
        and returns the highest unexecuted trigger.

        Args:
            symbol: Trading symbol
            current_price: Current market price

        Returns:
            HarvestAction if trigger hit, None otherwise
        """
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]
        gain_pct = position.current_gain_pct(current_price)

        # Check thresholds in descending order
        for threshold, trigger, flag_name in self.THRESHOLDS:
            if gain_pct >= threshold and not getattr(position, flag_name):
                return HarvestAction(
                    position=position,
                    trigger=trigger,
                    sell_pct=self.HARVEST_SELL_PCT,
                    current_price=current_price,
                )

        return None

    def check_all_positions(
        self,
        prices: Dict[str, float]
    ) -> List[HarvestAction]:
        """
        Check all positions for harvest triggers.

        Args:
            prices: Dictionary of symbol -> current price

        Returns:
            List of HarvestActions to execute
        """
        actions = []

        for symbol, position in self.positions.items():
            if symbol in prices:
                action = self.check_harvest_trigger(symbol, prices[symbol])
                if action:
                    actions.append(action)

        return actions

    def execute_harvest(
        self,
        action: HarvestAction,
        running_total: float = 0.0,
    ) -> HarvestEntry:
        """
        Execute a harvest action and record the entry.

        Updates position state and logs the harvest.

        Args:
            action: The harvest action to execute
            running_total: Current harvest account balance

        Returns:
            The recorded HarvestEntry
        """
        position = action.position
        trigger = action.trigger

        # Calculate shares to sell
        shares_to_sell = action.shares_to_sell
        proceeds = action.proceeds

        # Update position
        position.shares_remaining -= shares_to_sell

        # Set harvest flag
        if trigger == HarvestTrigger.TWENTY:
            position.harvested_20 = True
        elif trigger == HarvestTrigger.FIFTY:
            position.harvested_50 = True
        elif trigger == HarvestTrigger.HUNDRED:
            position.harvested_100 = True

        # Calculate new running total
        new_running_total = running_total + proceeds

        # Create harvest entry
        entry = HarvestEntry(
            date=datetime.now().isoformat(),
            symbol=position.symbol,
            trigger=trigger.value,
            shares_sold=shares_to_sell,
            sale_price=action.current_price,
            proceeds=proceeds,
            running_total=new_running_total,
        )

        self.harvest_log.append(entry)

        # Save state
        self._save_positions()
        self._save_harvest_log()

        logger.info(
            f"Harvested {position.symbol}: {shares_to_sell:.4f} shares at "
            f"${action.current_price:.2f} ({trigger.value} trigger) = ${proceeds:.2f}"
        )

        return entry

    def get_position(self, symbol: str) -> Optional[HarvestPosition]:
        """Get a position by symbol"""
        return self.positions.get(symbol)

    def get_all_positions(self) -> List[HarvestPosition]:
        """Get all tracked positions"""
        return list(self.positions.values())

    def get_position_with_status(
        self,
        symbol: str,
        current_price: float
    ) -> Optional[Dict]:
        """
        Get position with current status and next harvest info.

        Args:
            symbol: Trading symbol
            current_price: Current market price

        Returns:
            Dictionary with position data and status
        """
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]
        gain_pct = position.current_gain_pct(current_price)
        unrealized_pnl = (current_price - position.cost_per_share) * position.shares_remaining

        # Determine next harvest threshold
        next_harvest = None
        for threshold, trigger, flag_name in self.THRESHOLDS:
            if not getattr(position, flag_name):
                next_harvest = {
                    "threshold": trigger.value,
                    "target_price": position.cost_per_share * (1 + threshold),
                    "progress_pct": min(100, (gain_pct / threshold) * 100) if threshold > 0 else 0,
                }

        # Count harvests completed
        harvests_done = sum([
            position.harvested_20,
            position.harvested_50,
            position.harvested_100,
        ])

        return {
            **position.to_dict(),
            "current_price": current_price,
            "gain_pct": round(gain_pct * 100, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "harvests_completed": harvests_done,
            "harvests_remaining": 3 - harvests_done,
            "next_harvest": next_harvest,
            "is_free_shares": harvests_done >= 3,  # All harvests done
        }

    def get_harvest_log(self, limit: int = 50) -> List[Dict]:
        """Get recent harvest log entries"""
        entries = self.harvest_log[-limit:]
        return [entry.to_dict() for entry in reversed(entries)]

    def remove_position(self, symbol: str) -> bool:
        """Remove a position from tracking"""
        if symbol in self.positions:
            del self.positions[symbol]
            self._save_positions()
            logger.info(f"Removed position: {symbol}")
            return True
        return False

    def get_summary(self) -> Dict:
        """Get summary of all positions and harvest activity"""
        total_cost_basis = sum(p.cost_basis for p in self.positions.values())
        total_harvested = sum(e.proceeds for e in self.harvest_log)

        return {
            "total_positions": len(self.positions),
            "total_cost_basis": round(total_cost_basis, 2),
            "total_harvested": round(total_harvested, 2),
            "harvest_count": len(self.harvest_log),
            "positions_with_pending_harvests": sum(
                1 for p in self.positions.values()
                if not (p.harvested_20 and p.harvested_50 and p.harvested_100)
            ),
            "free_share_positions": sum(
                1 for p in self.positions.values()
                if p.harvested_20 and p.harvested_50 and p.harvested_100
            ),
        }


# Global instance
harvest_manager = HarvestManager()
