import hashlib
import uuid
from typing import Any, Dict

from project_chiang_m_ai.interfaces.brain import IBrain
from project_chiang_m_ai.interfaces.platform import ISportPlatform
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.services.workout_tracker import WorkoutSyncTracker


class CoachService:
    """
    Main service that coordinates workout synchronization between
    the Brain (decision maker) and the Sport Platform (data storage/display).
    """

    def __init__(
        self,
        brain: IBrain,
        platform: ISportPlatform,
        enable_tracking: bool = True,
    ):
        """
        Initialize the coach service with required dependencies.

        Args:
            brain: The intelligence deciding the workouts to sync.
            platform: The destination platform to push the workouts to.
            enable_tracking: Enable workout sync tracking (default: True)
        """
        self.brain = brain
        self.platform = platform
        self.tracker = WorkoutSyncTracker() if enable_tracking else None

    def sync_workouts(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Sync workouts from Brain to Platform.
        """
        logger.info("=" * 70)
        logger.info("🏋️  Starting workflow: Brain -> Platform")
        logger.info("=" * 70)

        results = {
            "success": True,
            "processed": 0,
            "uploaded": 0,
            "failed": 0,
            "errors": [],
        }

        # 1. Platform context
        wellness = self.platform.get_wellness_data()

        # 2. Brain decisions
        final_workouts = self.brain.get_final_workouts(wellness_data=wellness)

        results["processed"] = len(final_workouts)
        if not final_workouts:
            logger.info("✅ No workouts returned by the Brain. Nothing to sync.")
            return results

        sync_session_id = str(uuid.uuid4())[:8]
        uploaded_signatures = set()

        for idx, ws in enumerate(final_workouts, 1):
            workout = ws.workout
            source_id = ws.source_id

            logger.info(f"\n{'=' * 70}")
            logger.info(
                f"Processing decided workout {idx}/{len(final_workouts)}: "
                f"{workout.name}"
            )
            logger.info(f"{'=' * 70}")

            # Content hash for detecting changes between syncs
            workout_json = workout.model_dump_json()
            description_hash = hashlib.sha256(workout_json.encode("utf-8")).hexdigest()[
                :16
            ]

            workout_signature = (source_id, description_hash)

            # Check for tracker changes
            if self.tracker:
                existing_mapping = self.tracker.history.find_by_calendar_id(source_id)
                if existing_mapping:
                    if existing_mapping.workout_hash != description_hash:
                        logger.info("🔄 Workout content has changed!")

                        if existing_mapping.intervalicu_id:
                            logger.info("   🗑️  Deleting old instance on platform...")
                            delete_result = self.platform.delete_workout(
                                existing_mapping.intervalicu_id
                            )
                            if delete_result.get("success"):
                                logger.info("   ✅ Deleted old workout")
                            else:
                                logger.error(
                                    "   ⚠️  Failed to delete: "
                                    f"{delete_result.get('error')}"
                                )
                    else:
                        logger.info(f"⏭️  Skipping unchanged workout: '{workout.name}'")
                        results["processed"] -= 1
                        continue

            if workout_signature in uploaded_signatures:
                logger.info(f"⏭️  Skipping duplicate workout: '{workout.name}'")
                results["processed"] -= 1
                continue

            uploaded_signatures.add(workout_signature)

            if dry_run:
                logger.info(
                    f"🔍 DRY RUN: Would upload workout to platform: {workout.name}"
                )
                results["uploaded"] += 1
            else:
                upload_result = self.platform.push_workout(workout)

                if upload_result.get("success"):
                    results["uploaded"] += 1
                    workout_id = upload_result.get("workout_id")

                    if self.tracker:
                        self.tracker.record_sync(
                            source_id=source_id,
                            source_name=workout.name,
                            source_date=workout.start_date_local or "unknown",
                            workout_name=workout.name,
                            workout_type=workout.type,
                            workout_hash=description_hash,
                            sync_session_id=sync_session_id,
                            intervalicu_id=workout_id,
                            status="uploaded",
                        )
                else:
                    results["failed"] += 1
                    error_msg = upload_result.get("error", "Upload failed")
                    results["errors"].append(
                        {"workout": workout.name, "error": error_msg}
                    )
                    logger.error(f"❌ Upload failed: {error_msg}")

                    if self.tracker:
                        self.tracker.record_sync(
                            source_id=source_id,
                            source_name=workout.name,
                            source_date=workout.start_date_local or "unknown",
                            workout_name=workout.name,
                            workout_type=workout.type,
                            workout_hash=description_hash,
                            sync_session_id=sync_session_id,
                            intervalicu_id=None,
                            status="failed",
                        )

        logger.info(f"\n{'=' * 70}")
        logger.info("📊 SYNC SUMMARY")
        logger.info(f"{'=' * 70}")
        logger.info(f"Total evaluated: {results['processed']}")
        logger.info(f"✅ Successfully uploaded: {results['uploaded']}")
        if results["failed"] > 0:
            logger.error(f"❌ Failed: {results['failed']}")

        if self.tracker:
            self.tracker.print_stats()

        return results

    def cleanup_orphaned_workouts(self) -> Dict[str, Any]:
        """
        Cleans up platform workouts whose source no longer exists
        (e.g. a calendar event that has been deleted).

        Requires both tracking and brain.get_current_source_ids() support.

        Returns:
            Dict with keys: success, deleted, failed, errors
        """
        if not self.tracker:
            logger.warning(
                "⚠️  Tracking not enabled — cannot clean up orphaned workouts."
            )
            return {
                "success": False,
                "deleted": 0,
                "failed": 0,
                "errors": ["Tracking not enabled"],
            }

        active_ids = self.brain.get_current_source_ids()
        if active_ids is None:
            logger.warning(
                "⚠️  Brain does not support source enumeration. Cleanup skipped."
            )
            return {
                "success": False,
                "deleted": 0,
                "failed": 0,
                "errors": ["Brain does not support cleanup"],
            }

        active_id_set = set(active_ids)
        orphaned = [
            m
            for m in self.tracker.history.mappings
            if m.calendar_event_id not in active_id_set
        ]

        if not orphaned:
            logger.info("✅ No orphaned workouts found.")
            return {"success": True, "deleted": 0, "failed": 0, "errors": []}

        logger.info(f"\n🗑️  Found {len(orphaned)} orphaned workout(s) to clean up.")

        deleted, failed, errors = 0, 0, []

        for mapping in list(orphaned):
            logger.info(f"   • {mapping.calendar_event_summary}")

            if mapping.intervalicu_id:
                result = self.platform.delete_workout(mapping.intervalicu_id)
                if result.get("success"):
                    logger.info("     ✅ Deleted from platform.")
                    deleted += 1
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"     ⚠️  Failed to delete: {error_msg}")
                    failed += 1
                    errors.append(f"{mapping.calendar_event_summary}: {error_msg}")

            # Always remove from the tracker, even on platform delete failure,
            # so stale references don't accumulate.
            self.tracker.history.mappings.remove(mapping)

        self.tracker._save_history()

        logger.info(f"\n✅ Cleanup complete: {deleted} deleted, {failed} failed.")
        return {
            "success": failed == 0,
            "deleted": deleted,
            "failed": failed,
            "errors": errors,
        }


if __name__ == "__main__":
    from project_chiang_m_ai.factory import get_brain, get_platform

    logger.info("🏋️  LLM Coach - Orchestrator\n")

    # We load defaults. CLI handles args.
    service = CoachService(brain=get_brain(), platform=get_platform())
    service.sync_workouts()
