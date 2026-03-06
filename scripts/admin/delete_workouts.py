"""
Delete all synced workouts from Intervals.icu

This script:
1. Reads the sync history from data/workout_sync_history.json
2. Deletes all tracked workouts from Intervals.icu
3. Does NOT delete calendar events (they remain untouched)
4. Optionally cleans the database (with backup option)
"""

import sys

sys.path.insert(0, "src")

from project_chiang_m_ai.clients.intervalicu import IntervalicuClient
from project_chiang_m_ai.services.workout_tracker import WorkoutSyncTracker

print("🗑️  Delete All Synced Workouts from Intervals.icu")
print("=" * 70)
print()
print("⚠️  WARNING: This will delete workouts from Intervals.icu")
print("   Calendar events will NOT be deleted")
print()

# Load tracker
tracker = WorkoutSyncTracker()

if not tracker.history.mappings:
    print("📭 No workouts found in sync history")
    print("   Nothing to delete")
    sys.exit(0)

# Show what will be deleted
print(f"Found {len(tracker.history.mappings)} synced workouts")
print()
print("Workouts to delete:")
for i, mapping in enumerate(tracker.history.mappings, 1):
    print(f"  {i}. {mapping.intervalicu_name} (ID: {mapping.intervalicu_id})")
print()

# Confirm
response = (
    input("Delete ALL these workouts from Intervals.icu? (yes/NO): ").strip().lower()
)
if response != "yes":
    print("❌ Cancelled - no workouts deleted")
    sys.exit(0)

print()
print("=" * 70)
print("🗑️  DELETING WORKOUTS")
print("=" * 70)
print()

deleted_count = 0
failed_count = 0
errors = []

for i, mapping in enumerate(tracker.history.mappings, 1):
    workout_id = mapping.intervalicu_id

    if workout_id is None:
        print(
            f"{i}/{len(tracker.history.mappings)} - "
            f"Skipping (no Intervals.icu ID): {mapping.intervalicu_name}"
        )
        continue

    print(
        f"{i}/{len(tracker.history.mappings)} - "
        f"Deleting: {mapping.intervalicu_name} (ID: {workout_id})"
    )

    result = IntervalicuClient.delete_workout(workout_id)

    if result["success"]:
        deleted_count += 1
        # Update mapping status
        mapping.status = "deleted"
    else:
        failed_count += 1
        errors.append(
            {
                "workout": mapping.intervalicu_name,
                "id": workout_id,
                "error": result["error"],
            }
        )

# Save updated history
tracker._save_history()

print()
print("=" * 70)
print("📊 DELETION SUMMARY")
print("=" * 70)
print(f"Total workouts: {len(tracker.history.mappings)}")
print(f"✅ Deleted from Intervals.icu: {deleted_count}")
print(f"❌ Failed: {failed_count}")

if errors:
    print()
    print("⚠️  Errors:")
    for error in errors:
        print(f"   - {error['workout']} (ID: {error['id']}): {error['error']}")

print()
print("=" * 70)
print("✅ Deletion from Intervals.icu complete!")
print()

# Ask if user wants to clean the database
print("🧹 DATABASE CLEANUP")
print("=" * 70)
print()
print("Options:")
print("  1) Keep database (workouts marked as 'deleted')")
print("  2) Clean database (remove all workout records)")
print("  3) Clean and backup database first")
print()

cleanup_choice = input("Enter choice (1/2/3) [1]: ").strip() or "1"

if cleanup_choice == "2":
    # Clean without backup
    response = (
        input(
            "\n⚠️  This will DELETE all records from database. Are you sure? (yes/NO): "
        )
        .strip()
        .lower()
    )
    if response == "yes":
        tracker.history.mappings = []
        tracker.history.last_sync = None
        tracker._save_history()
        print("✅ Database cleaned! All records removed.")
    else:
        print("❌ Cancelled - database kept as is")

elif cleanup_choice == "3":
    # Clean with backup
    import shutil
    from datetime import datetime
    from pathlib import Path

    # Create backup
    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"workout_sync_history_backup_{timestamp}.json"

    shutil.copy(tracker.db_path, backup_file)
    print(f"\n💾 Backup created: {backup_file}")

    # Clean database
    tracker.history.mappings = []
    tracker.history.last_sync = None
    tracker._save_history()
    print("✅ Database cleaned! All records removed.")
    print(f"   Backup saved to: {backup_file}")

else:
    # Keep database as is
    print("\n📝 Database kept - workouts marked as 'deleted'")

print()
print("=" * 70)
print("📝 FINAL SUMMARY")
print("=" * 70)
print("   - Calendar events: UNTOUCHED ✅")
print("   - Intervals.icu workouts: DELETED ✅")
if cleanup_choice in ["2", "3"]:
    print("   - Database: CLEANED ✅")
    if cleanup_choice == "3":
        print(f"   - Backup: {backup_file} ✅")
else:
    print("   - Database: Updated (marked as deleted) ✅")
print("=" * 70)
