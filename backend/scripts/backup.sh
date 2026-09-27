#!/bin/bash
# Backup PostgreSQL baze
# Pokreće se cron-om svaki dan u 3:00

set -e

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/posdb_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Backup start..."

PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
  -h "${POSTGRES_HOST:-db}" \
  -U "${POSTGRES_USER:-posuser}" \
  -d "${POSTGRES_DB:-posdb}" \
  | gzip > "$BACKUP_FILE"

echo "[$(date)] Kreiran: $BACKUP_FILE"
echo "[$(date)] Veličina: $(du -h $BACKUP_FILE | cut -f1)"

# Obriši stare bekape
find "$BACKUP_DIR" -name "posdb_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
echo "[$(date)] Stari bekapi stariji od ${RETENTION_DAYS} dana obrisani"

echo "[$(date)] Backup završen."