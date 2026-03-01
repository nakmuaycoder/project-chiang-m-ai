"""
Test script for Coach Service

This script demonstrates the coach service in action.
It will sync workouts from Google Calendar to Intervals.icu.
"""

import sys

sys.path.insert(0, "src")

from llm_coach.services.coach import CoachService


def main():
    """Run the coach service sync."""

    print("🏋️  LLM Coach - Test Sync\n")
    print("This will:")
    print("1. Fetch upcoming events from Google Calendar")
    print("2. Filter for events with 'coach' in the summary")
    print("3. Parse workout JSON from event descriptions")
    print("4. Upload workouts to Intervals.icu")
    print("\n" + "=" * 70 + "\n")

    # Ask for sync mode
    print("Which workouts do you want to sync?")
    print("  1) Today's workouts only")
    print("  2) Next 28 days (recommended)")
    print()

    mode_choice = input("Enter choice (1 or 2): ").strip()

    if mode_choice == "1":
        sync_mode = "today"
        print("\n✓ Selected: Today's workouts only\n")
    elif mode_choice == "2":
        sync_mode = "all"
        print("\n✓ Selected: Next 28 days\n")
    else:
        print("❌ Invalid choice")
        return

    # Ask for confirmation
    response = input("Do you want to run this sync? (y/N): ").strip().lower()

    if response != "y":
        print("❌ Sync cancelled")
        return

    # Initialize coach service
    coach = CoachService()

    # Run sync with selected mode
    # Set dry_run=True to test without actually uploading
    results = coach.sync_from_calendar(
        max_results=150, sync_mode=sync_mode, dry_run=False
    )

    # Clean up deleted calendar events
    print("\n" + "=" * 70)
    print("🧹 CHECKING FOR DELETED EVENTS")
    print("=" * 70)
    coach.cleanup_deleted_events()

    # Print final result
    if results["success"] and results["failed"] == 0:
        print("\n✅ Sync completed successfully!")
        exit(0)
    elif results["uploaded"] > 0:
        print("\n⚠️  Sync completed with some errors")
        exit(1)
    else:
        print("\n❌ Sync failed")
        exit(1)


if __name__ == "__main__":
    main()
