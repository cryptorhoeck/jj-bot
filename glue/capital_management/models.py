"""
Data Models for Babylon + Buffett Capital Management

Defines position tracking, harvest entries, and deployment cycles.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import json
import os
from pathlib import Path


class HarvestTrigger(str, Enum):
    """Harvest trigger thresholds"""
    TWENTY = "20%"
    FIFTY = "50%"
    HUNDRED = "100%"


@dataclass
class HarvestPosition:
    """
    Position with harvest tracking.

    Extends standard position data with harvest flags to track
    which profit thresholds have been harvested.
    """
    symbol: str
    buy_date: str  # ISO format date
    shares_bought: float
    cost_per_share: float
    shares_remaining: float

    # Harvest tracking - which thresholds have been hit
    harvested_20: bool = False
    harvested_50: bool = False
    harvested_100: bool = False

    # Metadata
    entry_source: str = "jj-bot"  # Signal source that triggered entry
    notes: str = ""

    @property
    def cost_basis(self) -> float:
        """Total cost basis for remaining shares"""
        return self.shares_remaining * self.cost_per_share

    @property
    def original_cost_basis(self) -> float:
        """Original total cost basis"""
        return self.shares_bought * self.cost_per_share

    def current_gain_pct(self, current_price: float) -> float:
        """Calculate current gain percentage"""
        if self.cost_per_share <= 0:
            return 0.0
        return (current_price - self.cost_per_share) / self.cost_per_share

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage"""
        return {
            "symbol": self.symbol,
            "buy_date": self.buy_date,
            "shares_bought": self.shares_bought,
            "cost_per_share": self.cost_per_share,
            "shares_remaining": self.shares_remaining,
            "harvested_20": self.harvested_20,
            "harvested_50": self.harvested_50,
            "harvested_100": self.harvested_100,
            "entry_source": self.entry_source,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "HarvestPosition":
        """Create from dictionary"""
        return cls(
            symbol=data["symbol"],
            buy_date=data["buy_date"],
            shares_bought=data["shares_bought"],
            cost_per_share=data["cost_per_share"],
            shares_remaining=data["shares_remaining"],
            harvested_20=data.get("harvested_20", False),
            harvested_50=data.get("harvested_50", False),
            harvested_100=data.get("harvested_100", False),
            entry_source=data.get("entry_source", "jj-bot"),
            notes=data.get("notes", ""),
        )


@dataclass
class HarvestAction:
    """Represents a harvest action to be taken"""
    position: HarvestPosition
    trigger: HarvestTrigger
    sell_pct: float = 0.25  # 25% of position
    current_price: float = 0.0

    @property
    def shares_to_sell(self) -> float:
        """Number of shares to sell"""
        return self.position.shares_remaining * self.sell_pct

    @property
    def proceeds(self) -> float:
        """Expected proceeds from sale"""
        return self.shares_to_sell * self.current_price


@dataclass
class HarvestEntry:
    """Record of a completed harvest"""
    date: str  # ISO format datetime
    symbol: str
    trigger: str  # "20%", "50%", "100%"
    shares_sold: float
    sale_price: float
    proceeds: float
    running_total: float  # Harvest account balance after this entry

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage"""
        return {
            "date": self.date,
            "symbol": self.symbol,
            "trigger": self.trigger,
            "shares_sold": self.shares_sold,
            "sale_price": self.sale_price,
            "proceeds": self.proceeds,
            "running_total": self.running_total,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "HarvestEntry":
        """Create from dictionary"""
        return cls(
            date=data["date"],
            symbol=data["symbol"],
            trigger=data["trigger"],
            shares_sold=data["shares_sold"],
            sale_price=data["sale_price"],
            proceeds=data["proceeds"],
            running_total=data["running_total"],
        )


@dataclass
class DeploymentAlert:
    """Alert that deployment trigger has been met"""
    balance: float
    trigger_amount: float
    triggered_at: str  # ISO format datetime


@dataclass
class DeploymentCycle:
    """Record of a completed deployment cycle"""
    cycle_number: int
    date: str  # ISO format datetime
    harvest_balance: float

    # BTC deployment
    btc_amount: float = 500.0
    btc_price: float = 0.0
    btc_units: float = 0.0

    # Gold (MNT) deployment
    mnt_amount: float = 500.0
    mnt_price: float = 0.0
    mnt_units: float = 0.0

    # Status
    executed: bool = False
    notes: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage"""
        return {
            "cycle": self.cycle_number,
            "date": self.date,
            "harvest_balance": self.harvest_balance,
            "btc": {
                "amount": self.btc_amount,
                "price": self.btc_price,
                "units": self.btc_units,
            },
            "mnt": {
                "amount": self.mnt_amount,
                "price": self.mnt_price,
                "units": self.mnt_units,
            },
            "executed": self.executed,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "DeploymentCycle":
        """Create from dictionary"""
        btc = data.get("btc", {})
        mnt = data.get("mnt", {})
        return cls(
            cycle_number=data["cycle"],
            date=data["date"],
            harvest_balance=data["harvest_balance"],
            btc_amount=btc.get("amount", 500.0),
            btc_price=btc.get("price", 0.0),
            btc_units=btc.get("units", 0.0),
            mnt_amount=mnt.get("amount", 500.0),
            mnt_price=mnt.get("price", 0.0),
            mnt_units=mnt.get("units", 0.0),
            executed=data.get("executed", False),
            notes=data.get("notes", ""),
        )


@dataclass
class HarvestAccount:
    """
    Dedicated holding account for harvested profits.

    Tracks running balance toward deployment trigger.
    """
    balance: float = 0.0
    deployment_trigger: float = 1000.0

    # Cumulative totals
    total_deposited: float = 0.0
    total_deployed: float = 0.0
    deployment_cycles_completed: int = 0

    def deposit(self, amount: float, source_symbol: str, trigger: str) -> Optional[DeploymentAlert]:
        """
        Deposit harvest proceeds into the account.

        Returns DeploymentAlert if trigger is met.
        """
        self.balance += amount
        self.total_deposited += amount

        if self.balance >= self.deployment_trigger:
            return DeploymentAlert(
                balance=self.balance,
                trigger_amount=self.deployment_trigger,
                triggered_at=datetime.now().isoformat(),
            )
        return None

    def deploy(self, amount: float):
        """Record a deployment from the account"""
        self.balance -= amount
        self.total_deployed += amount
        self.deployment_cycles_completed += 1

    def reset(self):
        """Reset balance to zero after deployment"""
        self.balance = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage"""
        return {
            "balance": self.balance,
            "deployment_trigger": self.deployment_trigger,
            "total_deposited": self.total_deposited,
            "total_deployed": self.total_deployed,
            "deployment_cycles_completed": self.deployment_cycles_completed,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "HarvestAccount":
        """Create from dictionary"""
        return cls(
            balance=data.get("balance", 0.0),
            deployment_trigger=data.get("deployment_trigger", 1000.0),
            total_deposited=data.get("total_deposited", 0.0),
            total_deployed=data.get("total_deployed", 0.0),
            deployment_cycles_completed=data.get("deployment_cycles_completed", 0),
        )


# Storage paths
def get_data_dir() -> Path:
    """Get data directory for capital management files"""
    data_dir = Path(__file__).parent.parent.parent / "data" / "capital_management"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_positions_path() -> Path:
    """Get path to positions.json"""
    return get_data_dir() / "positions.json"


def get_harvest_log_path() -> Path:
    """Get path to harvest_log.json"""
    return get_data_dir() / "harvest_log.json"


def get_deployment_log_path() -> Path:
    """Get path to deployment_log.json"""
    return get_data_dir() / "deployment_log.json"


def get_account_path() -> Path:
    """Get path to harvest_account.json"""
    return get_data_dir() / "harvest_account.json"
