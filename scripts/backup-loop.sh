#!/bin/sh
# 定时执行 MongoDB -> JSON 备份（默认每 24 小时，启动时先执行一次）
set -eu

INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
cd /app

echo "[backup-loop] 启动，间隔 ${INTERVAL}s"
while true; do
  echo "[backup-loop] $(date '+%Y-%m-%d %H:%M:%S') 开始备份"
  python scripts/scheduled_backup.py || echo "[backup-loop] 本次备份失败，将在下个周期重试"
  echo "[backup-loop] 等待 ${INTERVAL}s"
  sleep "$INTERVAL"
done
