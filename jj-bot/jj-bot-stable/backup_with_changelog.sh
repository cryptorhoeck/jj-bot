#!/bin/bash

# Enhanced backup with changelog
# Usage: ./backup_with_changelog.sh "Description of changes"

DESCRIPTION="${1:-Manual backup}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=~/jj-bot-backups
MAX_BACKUPS=50

echo "📦 Creating backup with changelog..."

# Create backup
cd ~
BACKUP_NAME="jj-bot-backup-$TIMESTAMP"
tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" jj-bot 2>/dev/null

# Add to changelog
echo "" >> ~/jj-bot/CHANGELOG.md
echo "## [$TIMESTAMP] - $(date +%Y-%m-%d\ %H:%M:%S)" >> ~/jj-bot/CHANGELOG.md
echo "### Changes" >> ~/jj-bot/CHANGELOG.md
echo "- $DESCRIPTION" >> ~/jj-bot/CHANGELOG.md
echo "" >> ~/jj-bot/CHANGELOG.md

# Cleanup old backups (keep latest 50)
cd $BACKUP_DIR
ls -t *.tar.gz 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f 2>/dev/null || true

echo "✅ Backup created: $BACKUP_NAME.tar.gz"
echo "✅ Changelog updated"
echo "📊 Total backups: $(ls -1 *.tar.gz 2>/dev/null | wc -l)"
