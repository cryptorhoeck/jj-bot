# Current System Architecture

## Directory Structure
jj-bot/
├── dashboard/          # React frontend
├── glue/              # Backend components
│   ├── api/           # FastAPI server
│   ├── database/      # SQLite operations
│   └── simulation/    # Trade simulator
├── modules/           # Trading modules
│   ├── data_feed/     # Price fetcher
│   ├── strategy/      # Signal generator
│   └── risk/          # Risk manager
├── data/              # Data storage
├── logs/              # System logs
└── backups/           # Backup storage
## Key Files
- `glue/api/main.py` - Main API server
- `dashboard/jj-dashboard/src/App.jsx` - Main UI
- `modules/polished_system.py` - Trading system
- `backup_with_changelog.sh` - Backup utility

## Database
- Location: `jjbot.db`
- Type: SQLite
- Tables: trades, simulator_state

## Services & Ports
- Dashboard: http://localhost:5173
- API: http://127.0.0.1:8000
- Modules: Run via CLI
