#!/bin/bash

# UPDATE TEMPLATE - Copy this for any changes
# Usage: ./update_template.sh

# ALWAYS START WITH A BACKUP
echo "📦 Creating backup before changes..."
./backup_with_changelog.sh "UPDATE DESCRIPTION HERE"

# YOUR UPDATE CODE HERE
echo "🔧 Applying updates..."

# Example:
# - Fix something in the API
# - Update dashboard component
# - Add new feature

# ALWAYS END WITH STATUS CHECK
echo ""
echo "✅ Update complete!"
./check_status.sh
