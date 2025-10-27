#!/bin/bash

# JJ-Bot Backup Manager
# Handles backups, versioning, and restores with clear naming

BACKUP_ROOT="$HOME/jj-bot/backups"
PROJECT_ROOT="$HOME/jj-bot"
DATE_FORMAT=$(date +"%Y-%m-%d_%H-%M-%S")
DATE_SIMPLE=$(date +"%Y-%m-%d")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }

# Function to create a full system snapshot
create_snapshot() {
    local reason="$1"
    local snapshot_name="snapshot_${DATE_FORMAT}_${reason// /_}"
    local snapshot_dir="$BACKUP_ROOT/snapshots/$snapshot_name"
    
    print_info "Creating full system snapshot: $snapshot_name"
    
    mkdir -p "$snapshot_dir"
    
    # Backup all critical files
    cp -r glue/ "$snapshot_dir/" 2>/dev/null || true
    cp -r dashboard/ "$snapshot_dir/" 2>/dev/null || true
    cp -r hands/ "$snapshot_dir/" 2>/dev/null || true
    cp -r data/ "$snapshot_dir/" 2>/dev/null || true
    cp config.json "$snapshot_dir/" 2>/dev/null || true
    cp requirements.txt "$snapshot_dir/" 2>/dev/null || true
    cp jj "$snapshot_dir/" 2>/dev/null || true
    
    # Create snapshot info
    cat > "$snapshot_dir/SNAPSHOT_INFO.txt" << SNAP_EOF
JJ-Bot System Snapshot
Created: $(date)
Reason: $reason
Git Hash: $(git rev-parse HEAD 2>/dev/null || echo "Not a git repo")

Files included:
- Complete API backend (glue/)
- Complete dashboard (dashboard/)
- Trading logic (hands/)
- Configuration files
- Database files (data/)
- CLI scripts

To restore this snapshot:
  ./backup_manager.sh restore_snapshot $snapshot_name
SNAP_EOF
    
    print_success "Snapshot created: $snapshot_dir"
    echo "$snapshot_dir"
}

# Function to backup a specific file with versioning
backup_file() {
    local file_path="$1"
    local reason="$2"
    local file_name=$(basename "$file_path")
    local file_dir=$(dirname "$file_path")
    
    if [ ! -f "$file_path" ]; then
        print_error "File not found: $file_path"
        return 1
    fi
    
    # Determine backup category
    local category="misc"
    if [[ "$file_path" == *"glue/api"* ]]; then
        category="api"
    elif [[ "$file_path" == *"dashboard"* ]]; then
        category="dashboard"
    elif [[ "$file_path" == *"config"* ]]; then
        category="config"
    elif [[ "$file_path" == *"jj"* ]] || [[ "$file_path" == *"script"* ]]; then
        category="scripts"
    fi
    
    # Create versioned backup
    local backup_name="${file_name}_${DATE_FORMAT}_${reason// /_}"
    local backup_dir="$BACKUP_ROOT/files/$category"
    local version_dir="$BACKUP_ROOT/versions/$file_name"
    
    mkdir -p "$backup_dir"
    mkdir -p "$version_dir"
    
    # Copy file to both locations
    cp "$file_path" "$backup_dir/$backup_name"
    cp "$file_path" "$version_dir/v$(date +%s)_$backup_name"
    
    # Create changelog entry
    local changelog_file="$BACKUP_ROOT/changelogs/${file_name}_changelog.txt"
    cat >> "$changelog_file" << CHANGE_EOF

=== CHANGE LOG ENTRY ===
Date: $(date)
File: $file_path
Backup: $backup_name
Reason: $reason
Size: $(stat -f%z "$file_path" 2>/dev/null || stat -c%s "$file_path" 2>/dev/null || echo "unknown")
MD5: $(md5sum "$file_path" 2>/dev/null | cut -d' ' -f1 || echo "unavailable")

To restore this version:
  ./backup_manager.sh restore_file "$backup_dir/$backup_name" "$file_path"

CHANGE_EOF
    
    print_success "File backed up: $backup_name"
    print_info "Changelog updated: $changelog_file"
}

# Function to list all backups
list_backups() {
    print_info "JJ-Bot Backup Summary"
    echo "======================="
    
    echo ""
    echo "SNAPSHOTS:"
    if [ -d "$BACKUP_ROOT/snapshots" ]; then
        ls -la "$BACKUP_ROOT/snapshots" | grep "^d" | awk '{print "  " $9}' | grep -v "^\.$\|^\.\.$" || echo "  No snapshots found"
    fi
    
    echo ""
    echo "FILE BACKUPS BY CATEGORY:"
    for category in api dashboard config database scripts; do
        if [ -d "$BACKUP_ROOT/files/$category" ]; then
            local count=$(ls "$BACKUP_ROOT/files/$category" 2>/dev/null | wc -l)
            echo "  $category: $count files"
        fi
    done
    
    echo ""
    echo "RECENT ACTIVITY:"
    find "$BACKUP_ROOT" -name "*.txt" -type f -exec ls -la {} \; 2>/dev/null | sort -k6,8 | tail -5 | awk '{print "  " $6 " " $7 " " $8 " - " $9}'
}

# Function to restore a file
restore_file() {
    local backup_file="$1"
    local target_path="$2"
    
    if [ ! -f "$backup_file" ]; then
        print_error "Backup file not found: $backup_file"
        return 1
    fi
    
    # Create backup of current file before restore
    if [ -f "$target_path" ]; then
        backup_file "$target_path" "pre_restore_backup"
    fi
    
    # Restore the file
    cp "$backup_file" "$target_path"
    print_success "File restored: $target_path"
    print_warning "Previous version backed up before restore"
}

# Function to restore a full snapshot
restore_snapshot() {
    local snapshot_name="$1"
    local snapshot_dir="$BACKUP_ROOT/snapshots/$snapshot_name"
    
    if [ ! -d "$snapshot_dir" ]; then
        print_error "Snapshot not found: $snapshot_name"
        return 1
    fi
    
    print_warning "This will restore the entire system to snapshot: $snapshot_name"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" = "yes" ]; then
        # Create current state backup first
        create_snapshot "pre_restore_$(date +%H%M%S)"
        
        # Restore from snapshot
        cp -r "$snapshot_dir"/* "$PROJECT_ROOT/" 2>/dev/null || true
        
        print_success "System restored from snapshot: $snapshot_name"
        print_warning "Previous state saved as backup"
    else
        print_info "Restore cancelled"
    fi
}

# Function to show file history
show_history() {
    local file_name="$1"
    local changelog_file="$BACKUP_ROOT/changelogs/${file_name}_changelog.txt"
    
    if [ -f "$changelog_file" ]; then
        print_info "Change history for: $file_name"
        echo "=================================="
        cat "$changelog_file"
    else
        print_warning "No change history found for: $file_name"
    fi
}

# Main command handling
case "$1" in
    snapshot)
        create_snapshot "${2:-manual_snapshot}"
        ;;
    backup)
        if [ -z "$2" ]; then
            print_error "Usage: $0 backup <file_path> [reason]"
            exit 1
        fi
        backup_file "$2" "${3:-manual_backup}"
        ;;
    restore_file)
        if [ -z "$2" ] || [ -z "$3" ]; then
            print_error "Usage: $0 restore_file <backup_file> <target_path>"
            exit 1
        fi
        restore_file "$2" "$3"
        ;;
    restore_snapshot)
        if [ -z "$2" ]; then
            print_error "Usage: $0 restore_snapshot <snapshot_name>"
            exit 1
        fi
        restore_snapshot "$2"
        ;;
    list)
        list_backups
        ;;
    history)
        if [ -z "$2" ]; then
            print_error "Usage: $0 history <filename>"
            exit 1
        fi
        show_history "$2"
        ;;
    *)
        echo "JJ-Bot Backup Manager"
        echo "Usage: $0 {snapshot|backup|restore_file|restore_snapshot|list|history}"
        echo ""
        echo "Commands:"
        echo "  snapshot [reason]                    - Create full system snapshot"
        echo "  backup <file> [reason]              - Backup specific file with versioning"
        echo "  restore_file <backup> <target>      - Restore file from backup"
        echo "  restore_snapshot <snapshot_name>    - Restore entire system from snapshot"
        echo "  list                                - Show all backups"
        echo "  history <filename>                  - Show change history for file"
        echo ""
        echo "Examples:"
        echo "  $0 snapshot 'before_api_changes'"
        echo "  $0 backup glue/api/main.py 'fixed_trade_log_issue'"
        echo "  $0 list"
        echo "  $0 history main.py"
        ;;
esac
