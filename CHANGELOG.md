# Changelog

All notable changes to JJ-Bot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2025-12-06

### Major Release - Complete System Overhaul

This release represents a major overhaul of the JJ-Bot trading system with significant improvements to the RL training system, API security, real-time communication, and overall code quality.

### Added

#### Security & Authentication
- **API Key Authentication** - Optional API key authentication system for securing endpoints
  - Auto-generates secure API keys on first run
  - Configurable via `config/api_config.json`
  - Can be enabled/disabled at runtime via `/api/auth/enable`

#### Real-time Communication
- **WebSocket Event Publishing** - Trade events now broadcast to connected clients
  - Trade open/close events published via `event_bus`
  - Price feed status notifications
  - Real-time dashboard updates

#### Trading Intelligence
- **Price Feed Health Monitoring** - Detects stale price data and pauses trading
  - 5-minute staleness threshold
  - Automatic trading pause when feed is stale
  - Auto-resume when feed recovers
  - Keeps existing positions open (doesn't auto-close)

#### Training System
- **Cumulative P&L Tracker** - Track compounding performance during training
  - Shows what equity would be if trades were compounded
  - Simulated equity display in training UI
- **Real Kraken Historical Data** - Training uses actual market data
  - Smart pagination to fetch full history periods
  - Configurable timeframe and history length
  - Cache invalidation when settings change
- **24 Trading Strategies** - Full strategy selector implementation
  - Trend following, momentum, mean reversion strategies
  - Volatility and breakout strategies
  - Funding rate and sentiment-based strategies

### Changed

#### RL Training Improvements
- **100x Reward Scaling** - Increased from 1.0 to 100.0 for effective learning
- **Fixed GAE Bootstrap** - Corrected Generalized Advantage Estimation calculation
- **5x Harder IQ Scoring** - Requires 50,000+ episodes for full credit
  - Based on 10,000 hour rule for trading mastery
  - Human expert benchmark: 5 years, ~10,000 trades
  - AI must demonstrate 5x human expert level

#### Risk Management
- **Drawdown Includes Unrealized P&L** - More accurate risk assessment
- **Position Restoration** - Properly calculates P&L on restart
  - Uses config values for stop/take profit (not hardcoded)
  - Restores unrealized P&L based on last known prices

#### API & Security
- **CORS Restricted to Localhost** - No longer allows all origins
  - Only localhost:5173, 127.0.0.1:5173, etc.
- **REST API Rate Limiting** - Configurable polling interval
  - Default 30 seconds between REST price fetches
  - Reduces API load and avoids rate limits

#### Code Quality
- **RL Model Confidence** - Uses actual model output instead of hardcoded 0.6
  - Converts log_prob to probability for confidence score
  - Range bounded to [0.5, 0.95]
- **Prominent Warnings** - Clear messaging for important states
  - Sandbox mode warning on startup
  - Live trading warning
  - Demo mode fallback warning
  - Price feed stale warning

### Fixed

#### Critical Bugs
- **Hardcoded confidence=0.6** - Now uses actual RL model confidence
- **Drawdown calculation** - Now includes unrealized P&L
- **GAE bootstrap bug** - Was using current state value instead of next state
- **Cache invalidation** - Training now properly reloads data when settings change

#### High Priority Bugs
- **API_URL undefined** - Fixed to use API_BASE in frontend
- **Wrong endpoint** - Fixed `/api/positions/open` to `/api/pro/positions`
- **Wrong field name** - Fixed `data.open_positions` to `data.positions`
- **Silent exception handling** - Added proper logging to catch blocks
- **Division by zero** - Added protections in 5+ locations

#### Medium Priority Bugs
- **Bare except clauses** - Replaced with specific exception types
- **Print statements** - Converted to logger calls
- **Hardcoded hyperparameters** - Moved to BotConfig
- **Position restoration** - Now works correctly on restart

### Security

- API authentication framework (optional, disabled by default)
- CORS restricted to localhost origins only
- Prominent warnings for sandbox/live mode

---

## [2.3.0] - Previous Release

### Added
- Basic trading bot functionality
- RL training with PPO agent
- Dashboard with React frontend
- Kraken exchange integration

### Note
This changelog was created retroactively. Version 2.3.0 represents the state before the major 3.0.0 overhaul.

---

## Version History Summary

| Version | Date | Description |
|---------|------|-------------|
| 3.0.0 | 2025-12-06 | Major overhaul: Security, RL improvements, bug fixes |
| 2.3.0 | Previous | Initial tracked version |

---

## Upgrade Notes

### Upgrading to 3.0.0

1. **Config Changes**: New config options added to `bot_config.json`:
   - `rest_api_interval_seconds` (default: 30)
   - RL hyperparameters now in config

2. **New Files**:
   - `config/api_config.json` - API authentication settings
   - `VERSION` - Version file
   - `CHANGELOG.md` - This file

3. **Breaking Changes**:
   - CORS now restricted to localhost (update if accessing from other hosts)
   - RL reward scaling changed (may affect trained models)

4. **Recommended Actions**:
   - Re-train RL model with new reward scaling for best results
   - Review sandbox/live mode settings before trading
