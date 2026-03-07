"""
Detect and clean up deleted calendar events

This script:
1. Loads sync history from database
2. Fetches current calendar events
3. Finds events that are in DB but NOT in calendar (deleted)
4. Deletes those workouts from Intervals.icu
5. Removes them from the database
"""

import sys

sys.path.insert(0, "src")

from project_chiang_m_ai.clients.google_calendar import GoogleCalendarClient
from project_chiang_m_ai.clients.intervalicu import IntervalicuClient
from project_chiang_m_ai.services.workout_tracker import WorkoutSyncTracker

print("🗑️  Detect and Clean Up Deleted Calendar Events")
print("=" * 70)
print()

# Load tracker
tracker = WorkoutSyncTracker()

if not tracker.history.mappings:
    print("📭 No synced workouts in database")
    sys.exit(0)

# Load calendar events
print("📅 Fetching calendar events...")
calendar = GoogleCalendarClient()
events = calendar.list_upcoming_events(max_results=100)

# Create set of current calendar event IDs
current_event_ids = {event.id for event in events}

print(f"✅ Found {len(events)} calendar events")
print(f"💾 Found {len(tracker.history.mappings)} synced workouts in database")
print()

# Find deleted events (in DB but not in calendar)
deleted_events = []
for mapping in tracker.history.mappings:
    if mapping.calendar_event_id not in current_event_ids:
        deleted_events.append(mapping)

print("=" * 70)
print("📊 ANALYSIS")
print("=" * 70)
print()

if not deleted_events:
    print("✅ No deleted events detected!")
    print("   All synced workouts still exist in calendar")
    sys.exit(0)

print(f"⚠️  Found {len(deleted_events)} deleted calendar event(s):\\n")
for idx, mapping in enumerate(deleted_events, 1):
    print(f"  {idx}. {mapping.calendar_event_summary}")
    print(f"     Calendar ID: {mapping.calendar_event_id[:20]}...")
    print(f"     Intervals.icu ID: {mapping.intervalicu_id}")
    print(f"     Synced: {mapping.synced_at}")
    print()

print("=" * 70)
print()

# Ask for confirmation
response = input(
    "Delete these workouts from Intervals.icu and database? (yes/NO): "
).strip()

if response.lower() != "yes":
    print("\n❌ Cancelled - no changes made")
    sys.exit(0)

print()
print("=" * 70)
print("🗑️  DELETING WORKOUTS")
print("=" * 70)
print()

intervalicu = IntervalicuClient()
deleted_count = 0
failed_count = 0
errors = []

for idx, mapping in enumerate(deleted_events, 1):
    print(
        f"{idx}/{len(deleted_events)} - {mapping.calendar_event_summary} "
        f"(ID: {mapping.intervalicu_id})"
    )

    # Delete from Intervals.icu if ID exists
    if mapping.intervalicu_id:
        delete_result = intervalicu.delete_workout(mapping.intervalicu_id)

        if delete_result.get("success"):
            print("   ✅ Deleted from Intervals.icu")
            deleted_count += 1
        else:
            error_msg = delete_result.get("error", "Unknown error")
            print(f"   ⚠️  Failed to delete from Intervals.icu: {error_msg}")
            failed_count += 1
            errors.append(f"{mapping.calendar_event_summary}: {error_msg}")
    else:
        print("   ⏭️  No Intervals.icu ID - skipping")

    # Remove from database
    tracker.history.mappings.remove(mapping)
    print("   ✅ Removed from database")
    print()

# Save updated database
tracker._save_history()

print("=" * 70)
print("📊 CLEANUP SUMMARY")
print("=" * 70)
print(f"Total deleted events: {len(deleted_events)}")
print(f"✅ Deleted from Intervals.icu: {deleted_count}")
print(f"❌ Failed: {failed_count}")

if errors:
    print()
    print("⚠️  Errors:")
    for error in errors:
        print(f"   - {error}")

print()
print("=" * 70)
print("✅ Cleanup complete!")
print("=" * 70)
print("   - Calendar events: Deleted (by you)")
print("   - Intervals.icu workouts: DELETED ✅")
print("   - Database records: REMOVED ✅")
print("=" * 70)
