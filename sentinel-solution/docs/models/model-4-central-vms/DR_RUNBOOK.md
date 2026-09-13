# Model 4 Pilot DR Runbook

Status: **DESIGN TARGET** for multi-region failover. The executable pilot
procedure is SQLite backup/restore only; it does not claim replication, RPO,
or RTO.

## Pilot backup

1. Stop the backend or ensure no concurrent writer is active.
2. Use SQLite's online backup API: `sqlite3 sentinel.db ".backup 'sentinel-backup-YYYYMMDD.db'"`.
3. Store the backup outside the application tree with equivalent access controls.
4. Record operator, time and SHA-256 in the deployment log.

## Pilot restore drill

1. Restore only into an isolated copy; never overwrite the live pilot DB.
2. Start against `DATABASE_URL=sqlite:///./restore-check.db`.
3. Run the backend test suite and inspect `/health` plus an authenticated registry query.
4. Record success/failure and any data-loss window. Do not claim RPO/RTO until measured.

## Not implemented

PostgreSQL replication/failover, cross-zone/cross-region object-storage
replication, Kubernetes orchestration, Kafka recovery and automated backup
scheduling remain **NOT IMPLEMENTED** for this pilot.
