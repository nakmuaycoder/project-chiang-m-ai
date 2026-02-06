"""
Coach Service

Orchestrates the workflow of syncing workouts from Google Calendar to Intervals.icu.
"""

import json
import uuid
from typing import Any, Dict, List

from llm_coach.clients.google_calendar import GoogleCalendarClient
from llm_coach.clients.intervalicu import IntervalicuClient
from llm_coach.models.workout import Workout
from llm_coach.services.workout_tracker import WorkoutSyncTracker


class CoachService:
    """
    Main service that coordinates workout synchronization between
    Google Calendar and Intervals.icu.
    """

    def __init__(self, enable_tracking: bool = True):
        """
        Initialize the coach service with required clients.

        Args:
            enable_tracking: Enable workout sync tracking (default: True)
        """
        self.calendar_client = GoogleCalendarClient()
        self.intervalicu_client = IntervalicuClient()
        self.tracker = WorkoutSyncTracker() if enable_tracking else None

    def sync_from_calendar(
        self,
        max_results: int = 100,  # Fetch more events to handle multiple daily sessions
        sync_mode: str = "all",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Sync workouts from Google Calendar to Intervals.icu.

        This method:
        1. Fetches upcoming events from Google Calendar (up to max_results)
        2. Filters for events with "coach" in the summary
        3. Filters to only events within the next 28 days (or today only)
        4. Parses the event description as workout JSON
        5. Uploads each workout to Intervals.icu

        Args:
            max_results: Maximum number of calendar events to fetch (default: 100)
            sync_mode: Filter mode - "today" for today's workouts only, "all"
            for next 28 days
            dry_run: If True, parse workouts but don't upload them

        Returns:
            Dict with sync results including counts and any errors
        """
        from datetime import datetime, timedelta, timezone

        print("=" * 70)
        print("🏋️  Starting workout sync from Google Calendar to Intervals.icu")
        print("=" * 70)
        print()

        # Fetch events from Google Calendar
        print(f"📅 Fetching up to {max_results} upcoming events...")
        events = self.calendar_client.list_upcoming_events(max_results=max_results)
        print(f"✅ Found {len(events)} calendar events")

        # Filter for coach events
        coach_events = [
            event for event in events if "coach" in event.get("summary", "").lower()
        ]

        print(f"   Found {len(coach_events)} coach events (before date filtering)")

        # Calculate date ranges
        now = datetime.now(timezone.utc)
        # now = datetime(2026, 2, 9, 0, 0, 0, tzinfo=timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        future_limit = today_start + timedelta(days=28)  # 28 days from today

        # Filter by date based on sync_mode
        filtered_events = []

        if sync_mode == "today":
            # Only today's workouts
            for event in coach_events:
                event_start = event.get("start", {})
                if "dateTime" in event_start:
                    from dateutil import parser

                    event_dt = parser.parse(event_start["dateTime"])
                    if today_start <= event_dt < today_end:
                        filtered_events.append(event)
                elif "date" in event_start:
                    event_date = datetime.strptime(
                        event_start["date"], "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc)
                    if event_date.date() == now.date():
                        filtered_events.append(event)

            print(f"🗓️  Filtered to today's workouts: {len(filtered_events)} events")
        else:
            # All workouts within next 28 days
            for event in coach_events:
                event_start = event.get("start", {})
                if "dateTime" in event_start:
                    from dateutil import parser

                    event_dt = parser.parse(event_start["dateTime"])
                    if today_start <= event_dt < future_limit:
                        filtered_events.append(event)
                elif "date" in event_start:
                    event_date = datetime.strptime(
                        event_start["date"], "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc)
                    if today_start.date() <= event_date.date() < future_limit.date():
                        filtered_events.append(event)

            print(f"🗓️  Filtered to next 28 days: {len(filtered_events)} events")

        coach_events = filtered_events

        # Show filtered events
        if coach_events:
            for event in coach_events:
                print(f"   ✓ {event['summary']}")
            print(f"\n🎯 Found {len(coach_events)} coach events to process")

        if not coach_events:
            print("⚠️  No coach events found in the selected timeframe")
            return {
                "success": True,
                "processed": 0,
                "uploaded": 0,
                "failed": 0,
                "errors": [],
            }

        # Process each coach event
        results = {
            "success": True,
            "processed": len(coach_events),
            "uploaded": 0,
            "failed": 0,
            "errors": [],
        }

        # Generate unique sync session ID
        sync_session_id = str(uuid.uuid4())[:8]

        # Track uploaded workouts to detect duplicates
        # Key: (name, date, type, description_hash)
        uploaded_signatures = set()

        for idx, event in enumerate(coach_events, 1):
            print(f"\n{'=' * 70}")
            print(f"Processing event {idx}/{len(coach_events)}: {event['summary']}")
            print(f"{'=' * 70}")

            try:
                workout = self._parse_workout_from_event(event)

                # Create workout signature for duplicate detection
                import hashlib

                # Hash the ENTIRE event description (JSON) for change detection
                event_description = event.get("description", "")
                description_hash = hashlib.md5(
                    event_description.encode("utf-8")
                ).hexdigest()[:8]

                workout_signature = (
                    workout.name,
                    workout.start_date_local[:10]
                    if workout.start_date_local
                    else "no-date",
                    workout.type,
                    description_hash,
                )

                # Check if this event was previously synced and if it has been updated
                if self.tracker:
                    event_id = event.get("id")
                    existing_mapping = self.tracker.history.find_by_calendar_id(
                        event_id
                    )

                    if existing_mapping:
                        # Primary detection: Compare workout content hash
                        if existing_mapping.workout_hash != description_hash:
                            print("🔄 Workout content has changed!")
                            print(f"   Old hash: {existing_mapping.workout_hash}")
                            print(f"   New hash: {description_hash}")

                            # Delete the old workout from Intervals.icu
                            if existing_mapping.intervalicu_id:
                                workout_id = existing_mapping.intervalicu_id
                                print(
                                    f"   🗑️  Deleting old workout (ID: {workout_id})..."
                                )
                                delete_result = self.intervalicu_client.delete_workout(
                                    existing_mapping.intervalicu_id
                                )
                                if delete_result.get("success"):
                                    print("   ✅ Deleted old workout")
                                else:
                                    error_message = delete_result.get("error")
                                    error_message = (
                                        "   ⚠️  Failed to delete old workout: {}"
                                    )
                                    print(error_message.format(error_message))

                            # Continue to upload new version
                        else:
                            # Content unchanged - skip
                            print(f"⏭️  Skipping unchanged workout: '{workout.name}'")
                            print("   Content hash matches - no changes detected")
                            results["processed"] -= 1
                            continue

                # Check for duplicate
                if workout_signature in uploaded_signatures:
                    print(f"⏭️  Skipping duplicate workout: '{workout.name}'")
                    print("   Already processed in this sync session")
                    results["processed"] -= 1
                    continue

                # Mark as seen
                uploaded_signatures.add(workout_signature)

                if dry_run:
                    print(f"🔍 DRY RUN: Would upload workout: {workout.name}")
                    print(f"   Type: {workout.type}")
                    print(f"   Duration: {workout.moving_time}s")
                    results["uploaded"] += 1
                else:
                    # Upload to Intervals.icu
                    upload_result = self.intervalicu_client.upload_workout(workout)

                    if upload_result.get("success"):
                        results["uploaded"] += 1
                        workout_id = upload_result.get("workout_id")

                        # Track the sync if tracking is enabled
                        if self.tracker:
                            self.tracker.record_sync(
                                calendar_event=event,
                                workout_name=workout.name,
                                workout_type=workout.type,
                                workout_hash=description_hash,
                                sync_session_id=sync_session_id,
                                intervalicu_id=workout_id,
                                status="uploaded",
                            )
                    else:
                        results["failed"] += 1
                        results["errors"].append(
                            {
                                "event": event["summary"],
                                "error": upload_result.get("error", "Upload failed"),
                            }
                        )

                        # Track failed sync
                        if self.tracker:
                            self.tracker.record_sync(
                                calendar_event=event,
                                workout_name=workout.name,
                                workout_type=workout.type,
                                workout_hash=description_hash,
                                sync_session_id=sync_session_id,
                                intervalicu_id=None,
                                status="failed",
                            )

            except Exception as e:
                print(f"❌ Error processing event '{event['summary']}': {e}")
                results["failed"] += 1
                results["success"] = False
                results["errors"].append({"event": event["summary"], "error": str(e)})

        # Print summary
        print(f"\n{'=' * 70}")
        print("📊 SYNC SUMMARY")
        print(f"{'=' * 70}")
        print(f"Total events processed: {results['processed']}")
        print(f"✅ Successfully uploaded: {results['uploaded']}")
        print(f"❌ Failed: {results['failed']}")

        if results["errors"]:
            print("\n⚠️  Errors encountered:")
            for error in results["errors"]:
                print(f"   - {error['event']}: {error['error']}")

        print(f"{'=' * 70}\n")
        print(f"{'=' * 70}\n")

        # Print tracker stats if enabled
        if self.tracker:
            self.tracker.print_stats()

        return results

    def _filter_coach_events(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter calendar events for those with 'coach' in the summary.

        Args:
            events: List of calendar event objects

        Returns:
            Filtered list of coach events
        """
        coach_events = []

        for event in events:
            summary = event.get("summary", "").lower()
            if "coach" in summary:
                coach_events.append(event)
                print(f"   ✓ Found coach event: {event['summary']}")

        return coach_events

    def _parse_workout_from_event(self, event: Dict[str, Any]) -> Workout:
        """
        Parse a workout from a calendar event's description.

        The event description should contain valid JSON that can be
        deserialized into a Workout object.

        Args:
            event: Calendar event object

        Returns:
            Parsed Workout instance

        Raises:
            ValueError: If description is missing or invalid JSON
            Exception: If Workout instantiation fails
        """
        description = event.get("description", "").strip()

        if not description:
            raise ValueError(f"Event '{event['summary']}' has no description")

        print("📝 Parsing workout from event description...")

        try:
            # Decode HTML entities (Google Calendar may escape quotes as &quot;)
            import html

            description = html.unescape(description)

            # Parse JSON from event description
            payload = json.loads(description)

            # If start_date_local not provided, use event start time
            if "start_date_local" not in payload or not payload["start_date_local"]:
                event_start = event.get("start", {})
                if "dateTime" in event_start:
                    payload["start_date_local"] = event_start["dateTime"]
                elif "date" in event_start:
                    # All-day event, use date with default time
                    payload["start_date_local"] = f"{event_start['date']}T00:00:00"

            # Create Workout instance
            workout = Workout(**payload)

            print(f"✅ Successfully parsed workout: {workout.name}")
            print(f"   Type: {workout.type}")
            print(
                f"   Duration: {workout.moving_time}s ({workout.moving_time // 60}min)"
            )
            print(f"   Blocks: {len(workout.steps)}")

            return workout

        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in event description: {e}\n"
                f"Description: {description[:100]}..."
            )
        except Exception as e:
            raise Exception(
                f"Failed to create Workout from event data: {e}\n"
                f"Payload: {payload if 'payload' in locals() else 'N/A'}"
            )


if __name__ == "__main__":
    """
    CLI entry point for manual sync testing.

    Usage:
        python -m llm_coach.services.coach
    """
    print("🏋️  LLM Coach - Calendar to Intervals.icu Sync\n")

    coach_service = CoachService()

    # Run sync (use dry_run=True to test without uploading)
    results = coach_service.sync_from_calendar(max_results=28, dry_run=False)

    # Exit with appropriate code
    exit(0 if results["success"] and results["failed"] == 0 else 1)
