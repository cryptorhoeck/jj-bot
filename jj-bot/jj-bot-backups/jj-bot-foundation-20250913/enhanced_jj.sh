#!/bin/bash

# Enhanced JJ script with automatic backup integration
BACKUP_MANAGER="$HOME/jj-bot/backup_manager.sh"

# Function to create automatic backup before critical operations
auto_backup() {
    local operation="$1"
    if [ -f "$BACKUP_MANAGER" ]; then
        "$BACKUP_MANAGER" snapshot "auto_before_$operation"
    fi
}

# Original JJ functionality with backup integration
case "$1" in
    reset)
        echo "Creating automatic backup before reset..."
        auto_backup "reset"
        # Call original reset functionality here
        ;;
    *)
        # Call original JJ script
        exec ./jj.backup.original "$@"
        ;;
esac
