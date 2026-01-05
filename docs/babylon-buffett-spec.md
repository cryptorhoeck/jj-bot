# Babylon + Buffett: Profit Harvest System

> Capital Management Module for JJ-Bot Trading System

---

## Overview

This module integrates a systematic profit-harvesting strategy into JJ-Bot's Glue Layer. It combines wealth-building principles from *The Richest Man In Babylon* with Warren Buffett's patient, value-focused approach.

**Core Loop:**
```
JJ-Bot Entry Signals → Position Tracking → Profit Harvest → Accumulation → Hard Asset Deployment
```

---

## System Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Initial Capital | $10,000 | Deployed into satellite (active) positions |
| Deployment Trigger | $1,000 | 10% of initial capital |
| Hard Asset Split | 50/50 | BTC / MNT (Gold) |
| Platform | Wealthsimple | Crypto + Trade accounts |

---

## Phase 1: Profit Harvest Rules

When a position reaches the following gain thresholds, execute partial exits:

| Gain Threshold | Action | Destination |
|----------------|--------|-------------|
| +20% | Sell 25% of position | → Harvest Account |
| +50% | Sell 25% of position | → Harvest Account |
| +100% | Sell 25% of position | → Harvest Account |
| Remainder | 25% rides indefinitely | Stays invested ("free shares") |

### Logic Flow

```python
def check_harvest_trigger(position):
    gain_pct = (current_price - cost_basis) / cost_basis
    
    if gain_pct >= 1.0 and not position.harvested_100:
        return HarvestAction(sell_pct=0.25, trigger="100%")
    elif gain_pct >= 0.5 and not position.harvested_50:
        return HarvestAction(sell_pct=0.25, trigger="50%")
    elif gain_pct >= 0.2 and not position.harvested_20:
        return HarvestAction(sell_pct=0.25, trigger="20%")
    else:
        return None
```

---

## Phase 2: Accumulation

**Harvest Account:** A dedicated holding account for harvested profits.

- All harvest proceeds flow here
- No spending — accumulation only
- Tracks running balance toward deployment trigger

### Data Model

```python
class HarvestAccount:
    balance: float = 0.0
    deployment_trigger: float = 1000.0
    
    def deposit(self, amount: float, source_symbol: str, trigger: str):
        self.balance += amount
        self.log_entry(amount, source_symbol, trigger)
        
        if self.balance >= self.deployment_trigger:
            return DeploymentAlert(balance=self.balance)
        return None
```

---

## Phase 3: Deployment

When Harvest Account balance reaches **$1,000**, execute deployment cycle:

| Asset | Amount | Vehicle | Platform |
|-------|--------|---------|----------|
| Bitcoin | $500 | BTC | Wealthsimple Crypto |
| Gold | $500 | MNT (Royal Canadian Mint Gold Reserve) | Wealthsimple Trade |

After deployment:
- Harvest Account resets to $0
- Cycle increments
- Process repeats

### Deployment Record

```python
class DeploymentCycle:
    cycle_number: int
    date: datetime
    harvest_balance: float
    btc_amount: float = 500.0
    btc_price: float
    btc_units: float  # btc_amount / btc_price
    mnt_amount: float = 500.0
    mnt_price: float
    mnt_units: float  # mnt_amount / mnt_price
```

---

## Integration Points with JJ-Bot

### Glue Layer Extension

This module extends the existing Glue Layer (FastAPI + risk guards):

```
jj-bot/
├── glue/
│   ├── main.py              # FastAPI app
│   ├── risk_guards.py       # Existing risk management
│   ├── capital_management/  # NEW: Babylon module
│   │   ├── __init__.py
│   │   ├── harvest.py       # Harvest trigger logic
│   │   ├── accumulator.py   # Harvest account tracking
│   │   ├── deployer.py      # Deployment cycle logic
│   │   └── models.py        # Data models
│   └── ...
```

### API Endpoints (Proposed)

```python
# Position monitoring
GET  /positions                    # List all positions with harvest status
GET  /positions/{symbol}/harvest   # Check harvest triggers for position

# Harvest operations
POST /harvest                      # Execute harvest action
GET  /harvest/account              # Get harvest account balance

# Deployment
GET  /deployment/status            # Check if deployment trigger met
POST /deployment/execute           # Execute deployment cycle
GET  /deployment/history           # List completed cycles
```

### Event Hooks

```python
# Subscribe to JJ-Bot trade events
@glue.on_position_update
def check_harvest_triggers(position):
    action = check_harvest_trigger(position)
    if action:
        notify_harvest_opportunity(position, action)

@glue.on_harvest_deposit
def check_deployment_trigger(deposit):
    if harvest_account.balance >= deployment_trigger:
        notify_deployment_ready()
```

---

## Data Storage

### Position Tracking (positions.json)

```json
{
  "positions": [
    {
      "symbol": "AAPL",
      "buy_date": "2025-01-15",
      "shares_bought": 50,
      "cost_per_share": 180.00,
      "shares_remaining": 50,
      "harvested_20": false,
      "harvested_50": false,
      "harvested_100": false
    }
  ]
}
```

### Harvest Log (harvest_log.json)

```json
{
  "entries": [
    {
      "date": "2025-03-20",
      "symbol": "AAPL",
      "trigger": "20%",
      "shares_sold": 12,
      "sale_price": 216.00,
      "proceeds": 2592.00,
      "running_total": 2592.00
    }
  ]
}
```

### Deployment Log (deployment_log.json)

```json
{
  "cycles": [
    {
      "cycle": 1,
      "date": "2025-04-01",
      "harvest_balance": 1000.00,
      "btc": { "amount": 500, "price": 65000, "units": 0.00769 },
      "mnt": { "amount": 500, "price": 28.50, "units": 17.54 }
    }
  ]
}
```

---

## Review Cadence

| Frequency | Action |
|-----------|--------|
| Weekly | 5-min pulse check on position performance |
| Monthly | Cash flow review, verify contributions |
| Quarterly | Portfolio rebalance assessment, opportunity scan |
| Annually | Full strategy review, tax optimization |

---

## Automation Levels

The system can operate at three levels:

1. **Manual** — Tracking only; user executes all actions
2. **Semi-Auto** — System alerts user when triggers hit; user confirms
3. **Full Auto** — System executes harvests and logs; deployment stays manual (Wealthsimple)

**Recommended:** Semi-Auto for MVP, with deployment always manual.

---

## Dependencies

- JJ-Bot Glue Layer (FastAPI)
- Broker API connection (for price feeds / optional execution)
- Wealthsimple accounts (manual deployment)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-04 | Initial spec from Claude.ai session |

---

## References

- *The Richest Man In Babylon* — George S. Clason
- Warren Buffett's investment principles
- JJ Gorilla VWAP trading methodology
