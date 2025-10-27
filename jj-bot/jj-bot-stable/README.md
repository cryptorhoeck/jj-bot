# JJ-Bot Backup - 20250912_175941

## Backup Contents

### Core Systems
- **Trading API**: Complete glue/ directory with all endpoints
- **Dashboard**: React dashboard with all components
- **Dev Portal**: Phase 2 developer portal with all tools
- **Trading Logic**: All strategy files in hands/

### Configuration
- config.json with current trading parameters
- All Python scripts and utilities
- jj CLI command script

### Database
- jj_trades.db with all historical trades
- SQL dump for recovery

### Metadata
- List of all Python packages (pip_freeze.txt)
- Node.js dependencies (package.json files)
- Running processes at backup time
- System state information

## How to Restore

### Quick Restore
```bash
cd /home/ren/jj-bot-backups/jj-bot-complete-backup-20250912_175941
./restore.sh
```

### Manual Restore
1. Extract the backup to desired location
2. Copy files to ~/jj-bot/
3. Install Python dependencies: `pip install -r requirements.txt`
4. Install Node dependencies: `cd dashboard/jj-dashboard && npm install`
5. Start services: `jj reset`

## Backup Details
- Created: Fri 12 Sep 2025 05:59:45 PM ADT
- Size: 29M
- Location: /home/ren/jj-bot-backups/jj-bot-complete-backup-20250912_175941.tar.gz
