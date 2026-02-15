#!/bin/bash
# Daily SQLite backup script
# Keeps the last N days of backups (default: 14)
#
# Usage: ./backup-db.sh <db_path> <backup_dir> [retention_days]
# Example: ./backup-db.sh /home/deploy/chatty-foods/chatty_foods.db /home/deploy/backups/chatty-foods 14

set -euo pipefail

DB_PATH="$1"
BACKUP_DIR="$2"
RETENTION_DAYS="${3:-14}"

DATE=$(date +%Y-%m-%d)
APP_NAME=$(basename "$BACKUP_DIR")
BACKUP_FILE="$BACKUP_DIR/${APP_NAME}-${DATE}.db"

# Validate the source database exists
if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: Database not found at $DB_PATH" >&2
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Use SQLite's .backup command (safe for active databases)
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# Delete backups older than retention period
find "$BACKUP_DIR" -name "*.db" -type f -mtime +$RETENTION_DAYS -delete

echo "Backup complete: $BACKUP_FILE (keeping last $RETENTION_DAYS days)"
