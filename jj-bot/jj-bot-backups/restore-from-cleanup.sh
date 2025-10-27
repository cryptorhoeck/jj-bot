#!/bin/bash
# Restore script for cleanup backup

echo "🔄 Restoring from cleanup backup..."
BACKUP_FILE="/home/ren/jj-bot-backups/cleanup-backups/jj-bot-cleanup-backup-20250913_222525.tar.gz"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found!"
    exit 1
fi

cd ~
rm -rf jj-bot-temp 2>/dev/null
tar -xzf "$BACKUP_FILE"
mv jj-bot jj-bot-temp
mv jj-bot-temp jj-bot

echo "✅ Restored from $BACKUP_FILE"
cd ~/jj-bot && source .venv/bin/activate && ./check_status.sh
