# Utility Scripts

## Admin Scripts

- `admin/delete_workouts.py` - Delete all synced workouts from Intervals.icu
- `admin/cleanup_events.py` - Clean up deleted calendar events from sync database

**Note:** These scripts are superseded by the CLI but kept for manual/advanced operations.


## Recommended Usage

Use the main CLI for all operations:

```bash
# Sync workouts to devices
python -m project_chiang_m_ai sync --block    # Replaces: test_coach_sync.py
python -m project_chiang_m_ai sync --week
python -m project_chiang_m_ai sync --today

# Delete synced workouts
python -m project_chiang_m_ai clean           # Replaces: delete_all_intervals_workouts.py
python -m project_chiang_m_ai clean -y        # Skip confirmation

# Check sync status
python -m project_chiang_m_ai status
python -m project_chiang_m_ai status --list   # List all synced workouts
```

## Running Admin Scripts Directly

If you need to run the admin scripts:

```bash
# Delete all workouts (interactive)
python scripts/admin/delete_workouts.py

# Clean up deleted events
python scripts/admin/cleanup_events.py
```
