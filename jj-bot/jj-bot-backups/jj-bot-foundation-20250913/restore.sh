#!/bin/bash

# JJ-Bot Restore Script
# Auto-generated restore script for this backup

echo "============================================"
echo "🔄 JJ-Bot Backup Restore"
echo "============================================"
echo ""
echo "This will restore JJ-Bot from this backup."
echo "Target directory: ~/jj-bot"
echo ""
read -p "Are you sure you want to restore? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

BACKUP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_DIR="$HOME/jj-bot"

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

echo ""
echo "📋 Creating pre-restore backup..."
if [ -d "$TARGET_DIR" ]; then
    PRE_RESTORE_BACKUP="$HOME/jj-bot-pre-restore-$(date +%Y%m%d_%H%M%S).tar.gz"
    tar -czf "$PRE_RESTORE_BACKUP" -C "$HOME" jj-bot 2>/dev/null || echo "Could not create pre-restore backup"
    echo "Pre-restore backup saved to: $PRE_RESTORE_BACKUP"
fi

echo ""
echo "🔄 Restoring files..."

# Restore directories
for dir in glue dashboard dev-portal hands logs data ops; do
    if [ -d "$BACKUP_DIR/$dir" ]; then
        echo "  📁 Restoring $dir/..."
        rm -rf "$TARGET_DIR/$dir" 2>/dev/null
        cp -r "$BACKUP_DIR/$dir" "$TARGET_DIR/"
    fi
done

# Restore files
for file in config.json requirements.txt jj *.py *.sh; do
    if [ -f "$BACKUP_DIR/$file" ]; then
        echo "  📄 Restoring $file"
        cp "$BACKUP_DIR/$file" "$TARGET_DIR/"
    fi
done

# Restore database
if [ -f "$BACKUP_DIR/jj_trades.db" ]; then
    echo "  🗄️ Restoring database..."
    cp "$BACKUP_DIR/jj_trades.db" "$TARGET_DIR/"
fi

# Make scripts executable
chmod +x "$TARGET_DIR/jj" 2>/dev/null
chmod +x "$TARGET_DIR"/*.sh 2>/dev/null

echo ""
echo "✅ Restore complete!"
echo ""
echo "Next steps:"
echo "1. cd ~/jj-bot"
echo "2. source .venv/bin/activate (if virtual environment exists)"
echo "3. pip install -r requirements.txt (to restore Python packages)"
echo "4. cd dashboard/jj-dashboard && npm install (to restore Node packages)"
echo "5. jj reset (to restart the trading API)"
echo "6. cd dev-portal && ./start.sh (to start dev portal)"
echo ""
