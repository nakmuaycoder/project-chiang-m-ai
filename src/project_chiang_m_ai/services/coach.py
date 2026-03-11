"""
Coach Service

Orchestrates the workflow of syncing workouts from Google Calendar to Intervals.icu.
"""

import hashlib
import html
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from project_chiang_m_ai.clients.google_calendar import GoogleCalendarClient
from project_chiang_m_ai.clients.intervalicu import IntervalicuClient
from project_chiang_m_ai.factory import get_llm_client
from project_chiang_m_ai.interfaces.calendar import CalendarEvent
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.models.workout import Workout, WorkoutUnion
from project_chiang_m_ai.services.workout_tracker import WorkoutSyncTracker


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

        # Initialize LLM Client dynamically using factory
        self.llm_client = get_llm_client()

        self.tracker = WorkoutSyncTracker() if enable_tracking else None

    def sync_from_calendar(
        self,
        max_results: int = 100,  # Fetch more events to handle multiple daily sessions
        sync_mode: str = "all",
        days: int = 28,  # Default fallback if days aren't calculated
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
            days: The window of days to sync from today
            dry_run: If True, parse workouts but don't upload them

        Returns:
            Dict with sync results including counts and any errors
        """
        logger.info("=" * 70)
        logger.info("🏋️  Starting workout sync from Google Calendar to Intervals.icu")
        logger.info("=" * 70)
        logger.info("")

        # Fetch events from Google Calendar
        logger.info(f"📅 Fetching up to {max_results} upcoming events...")
        events = self.calendar_client.list_upcoming_events(max_results=max_results)
        logger.info(f"✅ Found {len(events)} calendar events")

        # Filter for coach events
        coach_events = [event for event in events if "coach" in event.summary.lower()]

        logger.info(
            f"   Found {len(coach_events)} coach events (before date filtering)"
        )

        # Calculate date ranges
        now = datetime.now(timezone.utc)
        # now = datetime(2026, 2, 9, 0, 0, 0, tzinfo=timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        future_limit = today_start + timedelta(days=days)

        # Filter by date based on sync_mode
        filtered_events = []

        if sync_mode == "today":
            # Only today's workouts
            for event in coach_events:
                # event.start is a datetime object
                event_dt = event.start
                if today_start <= event_dt < today_end:
                    filtered_events.append(event)

            logger.info(
                f"🗓️  Filtered to today's workouts: {len(filtered_events)} events"
            )
        else:
            # All workouts within next 28 days
            for event in coach_events:
                # event.start is a datetime object
                event_dt = event.start
                if today_start <= event_dt < future_limit:
                    filtered_events.append(event)

            logger.info(
                f"🗓️  Filtered to next {days} days: {len(filtered_events)} events"
            )

        coach_events = filtered_events

        # Show filtered events
        if coach_events:
            for event in coach_events:
                logger.info(f"   ✓ {event.summary}")
            logger.info(f"\n🎯 Found {len(coach_events)} coach events to process")

        if not coach_events:
            logger.warning("⚠️  No coach events found in the selected timeframe")
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
            logger.info(f"\n{'=' * 70}")
            logger.info(f"Processing event {idx}/{len(coach_events)}: {event.summary}")
            logger.info(f"{'=' * 70}")

            try:
                workout = self._parse_workout_from_event(event)

                # Create workout signature for duplicate detection
                # Hash the ENTIRE event description (JSON) for change detection
                event_description = event.description or ""
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
                    event_id = event.id
                    existing_mapping = self.tracker.history.find_by_calendar_id(
                        event_id
                    )

                    if existing_mapping:
                        # Primary detection: Compare workout content hash
                        if existing_mapping.workout_hash != description_hash:
                            logger.info("🔄 Workout content has changed!")
                            logger.info(f"   Old hash: {existing_mapping.workout_hash}")
                            logger.info(f"   New hash: {description_hash}")

                            # Delete the old workout from Intervals.icu
                            if existing_mapping.intervalicu_id:
                                workout_id = existing_mapping.intervalicu_id
                                logger.info(
                                    f"   🗑️  Deleting old workout (ID: {workout_id})..."
                                )
                                delete_result = self.intervalicu_client.delete_workout(
                                    existing_mapping.intervalicu_id
                                )
                                if delete_result.get("success"):
                                    logger.info("   ✅ Deleted old workout")
                                else:
                                    error_detail = delete_result.get(
                                        "error", "Unknown error"
                                    )
                                    error_message = (
                                        "   ⚠️  Failed to delete old workout: {}"
                                    )
                                    logger.info(error_message.format(error_detail))

                            # Continue to upload new version
                        else:
                            # Content unchanged - skip
                            logger.info(
                                f"⏭️  Skipping unchanged workout: '{workout.name}'"
                            )
                            logger.info("   Content hash matches - no changes detected")
                            results["processed"] -= 1
                            continue

                # Check for duplicate
                if workout_signature in uploaded_signatures:
                    logger.info(f"⏭️  Skipping duplicate workout: '{workout.name}'")
                    logger.info("   Already processed in this sync session")
                    results["processed"] -= 1
                    continue

                # Mark as seen
                uploaded_signatures.add(workout_signature)

                if dry_run:
                    logger.info(f"🔍 DRY RUN: Would upload workout: {workout.name}")
                    logger.info(f"   Type: {workout.type}")
                    if hasattr(workout, "moving_time"):
                        logger.info(f"   Duration: {workout.moving_time}s")
                    results["uploaded"] += 1
                else:
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
                                "event": event.summary,
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
                logger.error(f"❌ Error processing event '{event.summary}': {e}")
                results["failed"] += 1
                results["success"] = False
                results["errors"].append({"event": event.summary, "error": str(e)})

        # Print summary
        logger.info(f"\n{'=' * 70}")
        logger.info("📊 SYNC SUMMARY")
        logger.info(f"{'=' * 70}")
        logger.info(f"Total events processed: {results['processed']}")
        logger.info(f"✅ Successfully uploaded: {results['uploaded']}")
        logger.error(f"❌ Failed: {results['failed']}")

        if results["errors"]:
            logger.warning("\n⚠️  Errors encountered:")
            for error in results["errors"]:
                logger.info(f"   - {error['event']}: {error['error']}")

        logger.info(f"{'=' * 70}\n")
        logger.info(f"{'=' * 70}\n")

        # Print tracker stats if enabled
        if self.tracker:
            self.tracker.print_stats()

        return results

    def adapt_daily_plan(self) -> Dict[str, Any]:
        """
        Adapt today's scheduled workouts based on recent wellness data using the LLM.

        This method:
        1. Fetches recent wellness data (HRV, RHR) from Intervals.icu
        2. Fetches today's upcoming events from Google Calendar
        3. Sends the data to Gemini to get modified workouts
        4. Updates the Calendar events with the new workout payloads
        """
        logger.info("=" * 70)
        logger.info("🧠  Starting daily plan adaptation based on Wellness Data")
        logger.info("=" * 70)
        logger.info("")

        # 1. Fetch recent wellness data
        wellness_history = self.intervalicu_client.get_wellness_history()
        if not wellness_history:
            logger.warning("⚠️  Could not fetch wellness data. Aborting adaptation.")
            return {"success": False, "adapted": 0, "error": "No wellness data"}

        # 2. Fetch today's events from Calendar
        logger.info("📅 Fetching today's events from Calendar...")
        events = self.calendar_client.list_upcoming_events(max_results=20)
        coach_events = [event for event in events if "coach" in event.summary.lower()]

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        today_coach_events = []
        for event in coach_events:
            # Handle if event.start is somehow not timezone aware or missing
            if event.start and today_start <= event.start < today_end:
                today_coach_events.append(event)

        if not today_coach_events:
            logger.info("✅ No coach events found for today. Nothing to adapt.")
            return {"success": True, "adapted": 0, "failed": 0, "errors": []}

        logger.info(
            f"🎯 Found {len(today_coach_events)} coach events today to evaluate."
        )

        results = {"success": True, "adapted": 0, "failed": 0, "errors": []}

        for event in today_coach_events:
            logger.info(f"\nEvaluating event: {event.summary}")
            description = (event.description or "").strip()

            if not description:
                logger.warning(
                    f"⚠️ Event '{event.summary}' missing description. Skipping."
                )
                continue

            try:
                # Decode HTML entities and parse JSON payload
                description = html.unescape(description)
                original_workout_json = json.loads(description)

                # Check if it was already adapted today
                if (
                    "original_workout" in original_workout_json
                    and original_workout_json["original_workout"]
                ):
                    logger.info(
                        "⏭️  This workout has already been adapted by the LLM. Skipping."
                    )
                    continue

                # 3. Call LLM to adapt the workout
                adapted_workout_json = self.llm_client.adapt_workout(
                    current_workout_json=original_workout_json,
                    wellness_history=wellness_history,
                )

                # Make sure the LLM actually returned a valid dict
                if not adapted_workout_json:
                    logger.info("✅ LLM returned empty data. Skipping.")
                    continue

                # 4. Integrate the original workout text into the adapted struct
                adapted_workout_json["original_workout"] = original_workout_json

                # Update event in Calendar
                new_description = json.dumps(adapted_workout_json, indent=2)

                logger.info(
                    f"📝 Updating Calendar Event '{event.summary}' with adapted data..."
                )
                updated_event = self.calendar_client.update_event_description(
                    event_id=event.id, new_description=new_description
                )

                if updated_event:
                    logger.info("✨ Successfully adapted workout and updated calendar.")
                    results["adapted"] += 1
                else:
                    logger.error("❌ Failed to update the calendar event.")
                    results["failed"] += 1
                    results["errors"].append(f"Failed to update {event.id}")

            except json.JSONDecodeError:
                logger.error(
                    f"❌ Failed to parse JSON description for event '{event.summary}'"
                )
                results["failed"] += 1
                results["errors"].append(f"JSON Decode Error on {event.id}")
            except Exception as e:
                logger.error(f"❌ Error during adaptation for '{event.summary}': {e}")
                results["failed"] += 1
                results["errors"].append(str(e))

        # Print summary
        logger.info(f"\n{'=' * 70}")
        logger.info("📊 ADAPTATION SUMMARY")
        logger.info(f"{'=' * 70}")
        logger.info(f"Total events evaluated: {len(today_coach_events)}")
        logger.info(f"✅ Successfully adapted: {results['adapted']}")
        if results["failed"] > 0:
            logger.error(f"❌ Failed: {results['failed']}")

        logger.info(f"{'=' * 70}\n")

        return results

    def cleanup_deleted_events(
        self, calendar_events: List[CalendarEvent] = None
    ) -> Dict[str, Any]:
        """
        Clean up workouts that were deleted from calendar.

        Finds workouts in database that no longer exist in calendar,
        deletes them from Intervals.icu, and removes from database.

        Args:
            calendar_events: List of current calendar events (optional,
                           will fetch if not provided)

        Returns:
            dict: {
                "success": bool,
                "deleted": int,
                "failed": int,
                "errors": []
            }
        """
        if not self.tracker:
            logger.warning("⚠️  Tracking not enabled - cannot clean up deleted events")
            return {
                "success": False,
                "deleted": 0,
                "failed": 0,
                "errors": ["Tracking not enabled"],
            }

        # Fetch calendar events if not provided
        if calendar_events is None:
            calendar_events = self.calendar_client.list_upcoming_events(max_results=100)

        # Create set of current calendar event IDs
        current_event_ids = {event.id for event in calendar_events}

        # Find deleted events (in DB but not in calendar)
        deleted_mappings = []
        for mapping in self.tracker.history.mappings:
            if mapping.calendar_event_id not in current_event_ids:
                deleted_mappings.append(mapping)

        if not deleted_mappings:
            return {"success": True, "deleted": 0, "failed": 0, "errors": []}

        logger.info(f"\n🗑️  Found {len(deleted_mappings)} deleted calendar event(s)")

        deleted_count = 0
        failed_count = 0
        errors = []

        for mapping in deleted_mappings:
            logger.info(f"   • {mapping.calendar_event_summary}")

            # Delete from Intervals.icu if ID exists
            if mapping.intervalicu_id:
                delete_result = self.intervalicu_client.delete_workout(
                    mapping.intervalicu_id
                )

                if delete_result.get("success"):
                    logger.info("     ✅ Deleted from Intervals.icu")
                    deleted_count += 1
                else:
                    error_msg = delete_result.get("error", "Unknown error")
                    logger.error(f"     ⚠️  Failed: {error_msg}")
                    failed_count += 1
                    errors.append(f"{mapping.calendar_event_summary}: {error_msg}")

            # Remove from database
            self.tracker.history.mappings.remove(mapping)
            logger.info("     ✅ Removed from database")

        # Save updated database
        self.tracker._save_history()

        logger.info(
            f"\n✅ Cleanup complete: {deleted_count} deleted, {failed_count} failed"
        )

        return {
            "success": failed_count == 0,
            "deleted": deleted_count,
            "failed": failed_count,
            "errors": errors,
        }

    def _filter_coach_events(self, events: List[CalendarEvent]) -> List[CalendarEvent]:
        """
        Filter calendar events for those with 'coach' in the summary.

        Args:
            events: List of calendar event objects

        Returns:
            Filtered list of coach events
        """
        coach_events = []

        for event in events:
            summary = event.summary.lower()
            if "coach" in summary:
                coach_events.append(event)
                logger.info(f"   ✓ Found coach event: {event.summary}")

        return coach_events

    def _parse_workout_from_event(self, event: CalendarEvent) -> WorkoutUnion:
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
        description = (event.description or "").strip()

        if not description:
            raise ValueError(f"Event '{event.summary}' has no description")

        logger.info("📝 Parsing workout from event description...")

        try:
            # Decode HTML entities (Google Calendar may escape quotes as &quot;)
            description = html.unescape(description)

            # Parse JSON from event description
            payload = json.loads(description)

            # If start_date_local not provided, use event start time
            if "start_date_local" not in payload or not payload["start_date_local"]:
                # event.start is already a datetime object
                payload["start_date_local"] = event.start.isoformat()

            # Create Workout instance (handles Run/Ride/Strength)
            workout = Workout(**payload)

            logger.info(f"✅ Successfully parsed workout: {workout.name}")
            logger.info(f"   Type: {workout.type}")
            if hasattr(workout, "moving_time"):
                logger.info(
                    f"   Duration: {workout.moving_time}s "
                    f"({workout.moving_time // 60}min)"
                )
            if hasattr(workout, "steps"):
                logger.info(f"   Blocks: {len(workout.steps)}")

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
    CLI entry point for manual sync/adaptation testing.

    Usage:
        python -m project_chiang_m_ai.services.coach [adapt|sync]
    """
    action = sys.argv[1].lower() if len(sys.argv) > 1 else "sync"

    logger.info("🏋️  LLM Coach - Calendar to Intervals.icu Orchestrator\n")

    coach_service = CoachService()

    if action == "adapt":
        results = coach_service.adapt_daily_plan()
    else:
        results = coach_service.sync_from_calendar(
            max_results=28, days=28, dry_run=False
        )

    # Exit with appropriate code
    exit(0 if results.get("success") and results.get("failed", 0) == 0 else 1)
