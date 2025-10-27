# JJ Bot Command Reference

## Quick Start
- `jj` - Show menu
- `jj status` - Check system status
- `jj start` - Start all services
- `jj stop` - Stop all services

## Service Management
| Command | Description | What it Actually Does |
|---------|-------------|----------------------|
| `jj start` | Start services | Starts API on port 8000, Dashboard on 5173 |
| `jj stop` | Stop services | Kills uvicorn and npm processes |
| `jj restart` | Restart services | Stop then start with 2 sec delay |
| `jj status` | System status | Shows running processes, API health, backups |

## Logging
| Command | Description | Location |
|---------|-------------|----------|
| `jj logs` | All logs | Tails all .log files |
| `jj api-log` | API logs only | ~/jj-bot/logs/api.log |
| `jj dash-log` | Dashboard logs | ~/jj-bot/logs/dashboard.log |

## Backup & Restore
| Command | Description | Details |
|---------|-------------|---------|
| `jj backup` | Create backup | Timestamped tar.gz with optional message |
| `jj restore` | List backups | Shows available backups to restore |
| `jj reset` | Full reset | Backup → Stop → Rebuild → Restart |

## Trading
| Command | Description | WARNING |
|---------|-------------|---------|
| `jj trade` | Simulator | Paper trading only |
| `jj live` | LIVE Trading | ⚠️ REAL MONEY - Requires confirmation |

## Testing & Config
| Command | Description | Tests |
|---------|-------------|-------|
| `jj test` | Test APIs | Checks all endpoints |
| `jj config` | Edit config | Opens config.json in nano |

## What Each Command REALLY Does:

### `jj reset` - Full System Reset
1. Creates backup in ~/jj-bot-backups/
2. Stops all services (pkill uvicorn, npm)
3. Runs `npm install` in dashboard
4. Runs `npm run build` 
5. Restarts API and Dashboard
**WARNING**: This rebuilds the dashboard which might take time

### `jj status` - Complete Status Check
- Checks if uvicorn process running
- Checks if npm dev server running  
- Tests API health via curl
- Shows backup count and latest
- Shows disk usage
- Shows last 3 API log lines

### `jj start` - Smart Start
- Only starts services not already running
- Waits 3 seconds for each service
- Shows URLs for access

### `jj stop` - Clean Stop
- Kills uvicorn (API)
- Kills npm/vite (Dashboard)
- Waits 2 seconds for clean shutdown
