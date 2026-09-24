# Runbook: SQLite Database Recovery

## Symptom
SQLite reports `database disk image is malformed` or integrity check errors.

## Action Steps
1. Immediate backup of current DB:
   ```bash
   cp db/invst.db db/invst.db.corrupt.$(date +%Y%m%d)
   ```
2. Export DB dump and rebuild:
   ```bash
   sqlite3 db/invst.db ".recover" | sqlite3 db/invst_recovered.db
   mv db/invst_recovered.db db/invst.db
   ```
3. Verify integrity:
   ```bash
   sqlite3 db/invst.db "PRAGMA integrity_check;"
   ```
4. Re-apply schema migration if needed:
   ```bash
   python db/migrate.py
   ```
