# Utility Scripts

## Admin Scripts

- `admin/delete_workouts.py` - Delete all synced workouts from Intervals.icu
- `admin/cleanup_events.py` - Clean up deleted calendar events from sync database

**Note:** These scripts are superseded by the CLI but kept for manual/advanced operations.

## Legacy Scripts

- `legacy/test_coach_sync.py` - **DEPRECATED** - Use CLI instead

## Recommended Usage

Use the main CLI for all operations:

```bash
# Sync workouts to devices
python -m llm_coach sync --block    # Replaces: test_coach_sync.py
python -m llm_coach sync --week
python -m llm_coach sync --today

# Delete synced workouts
python -m llm_coach clean           # Replaces: delete_all_intervals_workouts.py
python -m llm_coach clean -y        # Skip confirmation

# Check sync status
python -m llm_coach status
python -m llm_coach status --list   # List all synced workouts
```

## Running Admin Scripts Directly

If you need to run the admin scripts:

```bash
# Delete all workouts (interactive)
python scripts/admin/delete_workouts.py

# Clean up deleted events
python scripts/admin/cleanup_events.py
```
