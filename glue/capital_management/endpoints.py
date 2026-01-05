"""
API Endpoints for Babylon + Buffett Capital Management

Provides REST API for:
- Position tracking and harvest monitoring
- Harvest execution
- Harvest account status
- Deployment cycles
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from .harvest import harvest_manager
from .accumulator import accumulator
from .deployer import deployer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/capital", tags=["Capital Management"])


# ==================== Request/Response Models ====================

class AddPositionRequest(BaseModel):
    """Request to add a position for harvest tracking"""
    symbol: str
    shares: float
    cost_per_share: float
    entry_source: str = "manual"
    notes: str = ""


class ExecuteHarvestRequest(BaseModel):
    """Request to execute a harvest"""
    symbol: str
    current_price: float


class CreateDeploymentRequest(BaseModel):
    """Request to create a deployment cycle"""
    btc_price: Optional[float] = None
    mnt_price: Optional[float] = None


class ExecuteDeploymentRequest(BaseModel):
    """Request to execute pending deployment"""
    btc_price: Optional[float] = None
    mnt_price: Optional[float] = None
    notes: str = ""


class SetTriggerRequest(BaseModel):
    """Request to update deployment trigger"""
    amount: float


# ==================== Position Endpoints ====================

@router.get("/positions")
async def list_positions():
    """
    List all positions with harvest status.

    Returns positions tracked for profit harvesting with their
    current harvest state (which thresholds have been hit).
    """
    positions = harvest_manager.get_all_positions()
    return {
        "positions": [p.to_dict() for p in positions],
        "count": len(positions),
        "summary": harvest_manager.get_summary(),
    }


@router.get("/positions/{symbol}")
async def get_position(symbol: str, current_price: Optional[float] = None):
    """
    Get position details with optional current price for status.

    If current_price is provided, includes gain %, unrealized P&L,
    and next harvest threshold info.
    """
    if current_price:
        status = harvest_manager.get_position_with_status(symbol, current_price)
        if not status:
            raise HTTPException(status_code=404, detail=f"Position not found: {symbol}")
        return status

    position = harvest_manager.get_position(symbol)
    if not position:
        raise HTTPException(status_code=404, detail=f"Position not found: {symbol}")

    return position.to_dict()


@router.post("/positions")
async def add_position(request: AddPositionRequest):
    """
    Add a new position for harvest tracking.

    If position already exists, adds to it (averages cost basis).
    """
    position = harvest_manager.add_position(
        symbol=request.symbol,
        shares=request.shares,
        cost_per_share=request.cost_per_share,
        entry_source=request.entry_source,
        notes=request.notes,
    )

    return {
        "status": "added",
        "position": position.to_dict(),
    }


@router.delete("/positions/{symbol}")
async def remove_position(symbol: str):
    """Remove a position from harvest tracking"""
    if harvest_manager.remove_position(symbol):
        return {"status": "removed", "symbol": symbol}
    raise HTTPException(status_code=404, detail=f"Position not found: {symbol}")


# ==================== Harvest Endpoints ====================

@router.get("/positions/{symbol}/harvest")
async def check_harvest_trigger(symbol: str, current_price: float):
    """
    Check if a position has hit a harvest trigger.

    Returns harvest action details if trigger is met.
    """
    action = harvest_manager.check_harvest_trigger(symbol, current_price)

    if not action:
        position = harvest_manager.get_position(symbol)
        if not position:
            raise HTTPException(status_code=404, detail=f"Position not found: {symbol}")

        return {
            "symbol": symbol,
            "harvest_triggered": False,
            "current_price": current_price,
            "gain_pct": round(position.current_gain_pct(current_price) * 100, 2),
            "message": "No harvest threshold met",
        }

    return {
        "symbol": symbol,
        "harvest_triggered": True,
        "trigger": action.trigger.value,
        "current_price": current_price,
        "shares_to_sell": round(action.shares_to_sell, 6),
        "expected_proceeds": round(action.proceeds, 2),
        "gain_pct": round(action.position.current_gain_pct(current_price) * 100, 2),
    }


@router.post("/harvest")
async def execute_harvest(request: ExecuteHarvestRequest):
    """
    Execute a harvest action.

    Sells 25% of position at the current threshold and
    deposits proceeds into harvest account.
    """
    # Check for harvest trigger
    action = harvest_manager.check_harvest_trigger(request.symbol, request.current_price)

    if not action:
        raise HTTPException(
            status_code=400,
            detail="No harvest threshold met for this position at current price",
        )

    # Get current harvest account balance for running total
    current_balance = accumulator.get_balance()

    # Execute harvest
    entry = harvest_manager.execute_harvest(action, running_total=current_balance)

    # Deposit to harvest account
    alert = accumulator.deposit(entry)

    response = {
        "status": "harvested",
        "entry": entry.to_dict(),
        "harvest_account_balance": accumulator.get_balance(),
        "deployment_ready": alert is not None,
    }

    if alert:
        response["deployment_alert"] = {
            "message": f"Deployment trigger met! Balance: ${alert.balance:.2f}",
            "balance": alert.balance,
            "trigger": alert.trigger_amount,
        }

    return response


@router.get("/harvest/account")
async def get_harvest_account():
    """
    Get harvest account status.

    Shows current balance, progress toward deployment trigger,
    and cumulative statistics.
    """
    return accumulator.get_status()


@router.get("/harvest/log")
async def get_harvest_log(limit: int = 50):
    """Get harvest history log"""
    return {
        "entries": harvest_manager.get_harvest_log(limit),
        "account": accumulator.get_status(),
    }


@router.put("/harvest/trigger")
async def set_deployment_trigger(request: SetTriggerRequest):
    """Update the deployment trigger amount"""
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Trigger amount must be positive")

    accumulator.set_deployment_trigger(request.amount)

    return {
        "status": "updated",
        "new_trigger": request.amount,
        "account": accumulator.get_status(),
    }


# ==================== Deployment Endpoints ====================

@router.get("/deployment/status")
async def get_deployment_status():
    """
    Check if deployment trigger is met.

    Returns deployment readiness and pending deployment if any.
    """
    alert = accumulator.check_deployment_ready()
    pending = deployer.get_pending()

    return {
        "deployment_ready": alert is not None,
        "harvest_balance": accumulator.get_balance(),
        "trigger_amount": accumulator.account.deployment_trigger,
        "pending_deployment": pending,
        "alert": {
            "balance": alert.balance,
            "trigger": alert.trigger_amount,
            "triggered_at": alert.triggered_at,
        } if alert else None,
    }


@router.post("/deployment/create")
async def create_deployment(request: CreateDeploymentRequest = Body(default=CreateDeploymentRequest())):
    """
    Create a new deployment cycle.

    Creates a pending deployment that must be confirmed after
    manual execution on Wealthsimple.
    """
    balance = accumulator.get_balance()
    trigger = accumulator.account.deployment_trigger

    if balance < trigger:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance: ${balance:.2f} < ${trigger:.2f} trigger",
        )

    # Check for existing pending
    if deployer.pending_deployment:
        raise HTTPException(
            status_code=400,
            detail="Pending deployment already exists. Execute or cancel it first.",
        )

    cycle = deployer.create_deployment(
        harvest_balance=balance,
        btc_price=request.btc_price,
        mnt_price=request.mnt_price,
    )

    return {
        "status": "created",
        "cycle": cycle.to_dict(),
        "instructions": {
            "btc": f"Buy ${cycle.btc_amount:.2f} of BTC on Wealthsimple Crypto",
            "mnt": f"Buy ${cycle.mnt_amount:.2f} of MNT on Wealthsimple Trade",
        },
        "next_step": "POST /api/capital/deployment/execute after completing purchases",
    }


@router.post("/deployment/execute")
async def execute_deployment(request: ExecuteDeploymentRequest = Body(default=ExecuteDeploymentRequest())):
    """
    Mark pending deployment as executed.

    Call this after completing the purchases on Wealthsimple.
    Provide actual execution prices if different from creation time.
    """
    cycle = deployer.execute_deployment(
        btc_price=request.btc_price,
        mnt_price=request.mnt_price,
        notes=request.notes,
    )

    if not cycle:
        raise HTTPException(
            status_code=400,
            detail="No pending deployment to execute",
        )

    # Mark funds as deployed in accumulator
    accumulator.mark_deployed(cycle.harvest_balance)
    accumulator.reset_balance()

    return {
        "status": "executed",
        "cycle": cycle.to_dict(),
        "harvest_account_balance": accumulator.get_balance(),
        "holdings": deployer.get_holdings(),
    }


@router.delete("/deployment/pending")
async def cancel_pending_deployment():
    """Cancel pending deployment"""
    if deployer.cancel_pending():
        return {"status": "cancelled"}
    raise HTTPException(status_code=404, detail="No pending deployment to cancel")


@router.get("/deployment/history")
async def get_deployment_history(limit: int = 20):
    """Get deployment cycle history"""
    return {
        "cycles": deployer.get_deployment_history(limit),
        "summary": deployer.get_summary(),
    }


@router.get("/deployment/holdings")
async def get_holdings():
    """
    Get cumulative hard asset holdings.

    Shows total BTC and MNT accumulated through deployments.
    """
    return deployer.get_holdings()


# ==================== Dashboard Summary ====================

@router.get("/summary")
async def get_capital_summary():
    """
    Get complete capital management summary.

    Combines position, harvest, and deployment data for dashboard.
    """
    return {
        "positions": harvest_manager.get_summary(),
        "harvest_account": accumulator.get_status(),
        "deployments": deployer.get_summary(),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/dashboard")
async def get_dashboard_data():
    """
    Get all data needed for capital management dashboard.

    Comprehensive endpoint for rendering the full dashboard.
    """
    positions = harvest_manager.get_all_positions()

    return {
        "summary": {
            "total_positions": len(positions),
            "harvest_balance": accumulator.get_balance(),
            "deployment_trigger": accumulator.account.deployment_trigger,
            "deployment_ready": accumulator.get_balance() >= accumulator.account.deployment_trigger,
            "total_deployed": deployer.get_holdings()["total_deployed"],
            "deployment_cycles": len(deployer.deployment_log),
        },
        "positions": [p.to_dict() for p in positions],
        "harvest_account": accumulator.get_status(),
        "pending_deployment": deployer.get_pending(),
        "holdings": deployer.get_holdings(),
        "recent_harvests": harvest_manager.get_harvest_log(10),
        "recent_deployments": deployer.get_deployment_history(5),
        "timestamp": datetime.now().isoformat(),
    }
