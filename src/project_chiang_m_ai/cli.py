"""
Project Chiang M-ai CLI

Command-line interface for syncing LLM-generated workouts to Intervals.icu
(and subsequently to Garmin, Wahoo, and home trainer apps).
"""

import argparse
import sys

from project_chiang_m_ai.config import settings
from project_chiang_m_ai.factory import get_brain, get_platform
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.services.coach import CoachService


def calculate_block_days(periodization: str) -> int:
    """Calculate training block duration from periodization pattern."""
    if periodization == "2:1":
        return 21  # 2 weeks on + 1 week recovery
    elif periodization == "3:1":
        return 28  # 3 weeks on + 1 week recovery
    else:
        logger.warning(
            f"⚠️  Unknown periodization: {periodization}, defaulting to 28 days"
        )
        return 28


def cmd_sync(args):
    """Sync workouts from Google Calendar to Intervals.icu."""
    logger.info("=" * 70)
    logger.info("🔄 LLM Coach - Sync Workouts")
    logger.info("=" * 70)
    logger.info("")

    # Determine sync mode and days
    if args.block:
        days = calculate_block_days(settings.PERIODIZATION)
        mode = "all"
        logger.info(
            f"📅 Syncing training block ({settings.PERIODIZATION} = {days} days)"
        )
    elif args.week:
        days = 7
        mode = "all"
        logger.info("📅 Syncing this week (7 days)")
    elif args.today:
        days = 1
        mode = "today"
        logger.info("📅 Syncing today's workouts")
    elif args.days:
        days = args.days
        mode = "all"
        logger.info(f"📅 Syncing next {days} days")
    else:
        # Default: block
        days = calculate_block_days(settings.PERIODIZATION)
        mode = "all"
        logger.info(
            f"📅 Syncing training block ({settings.PERIODIZATION} = {days} days)"
        )

    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No workouts will be uploaded")

    logger.info("")

    # Initialize coach service
    brain = get_brain(sync_mode=mode, days=days)
    platform = get_platform()
    coach = CoachService(brain=brain, platform=platform, enable_tracking=True)

    # Run sync
    results = coach.sync_workouts(dry_run=args.dry_run)

    # Summary
    logger.info("")
    if results["failed"] == 0:
        logger.info("✅ Sync completed successfully!")
        sys.exit(0)
    else:
        logger.warning("⚠️  Sync completed with errors")
        sys.exit(1)


def cmd_adapt(args):
    """Adapt today's workouts based on wellness data."""
    logger.info("=" * 70)
    logger.info("🧠 LLM Coach - Adapt Workouts")
    logger.info("=" * 70)
    logger.info("")

    # Initialize coach service — brain type comes from coach_config.yaml

    # adapt always targets today, regardless of YAML brain type
    brain = get_brain(sync_mode="today", days=1)
    platform = get_platform()
    coach = CoachService(brain=brain, platform=platform, enable_tracking=True)

    # Run adaptation
    results = coach.sync_workouts(dry_run=False)

    # Summary
    logger.info("")
    if results.get("success") and results.get("failed", 0) == 0:
        logger.info("✅ Adaptation completed successfully!")
        sys.exit(0)
    else:
        logger.warning("⚠️  Adaptation completed with errors")
        sys.exit(1)


def cmd_clean(args):
    """Clean up synced workouts from Intervals.icu."""
    from project_chiang_m_ai.services.workout_tracker import WorkoutSyncTracker

    tracker = WorkoutSyncTracker()
    stats = tracker.get_stats()

    logger.info("=" * 70)
    logger.info("🗑️  Clean Synced Workouts")
    logger.info("=" * 70)
    logger.info("")

    if stats["total_synced"] == 0:
        logger.info("📭 No synced workouts found")
        sys.exit(0)

    logger.info(f"Found {stats['total_synced']} synced workout(s)")
    logger.info("")
    logger.warning("⚠️  WARNING: This will delete workouts from Intervals.icu")
    logger.info("   Calendar events will NOT be deleted")
    logger.info("")

    if not args.yes:
        response = input("Delete all synced workouts? (yes/NO): ").strip().lower()
        if response != "yes":
            logger.error("❌ Cancelled")
            sys.exit(0)

    # Delete workouts
    # Delete workouts using the configured platform

    platform = get_platform()
    deleted = 0
    failed = 0

    logger.info("")
    logger.info("🗑️  Deleting workouts...")
    for idx, mapping in enumerate(tracker.history.mappings, 1):
        if mapping.platform_id:
            logger.info(
                f"{idx}/{stats['total_synced']} - Deleting: "
                f"{mapping.platform_name} (ID: {mapping.platform_id})"
            )
            result = platform.delete_workout(mapping.platform_id)
            if result.get("success"):
                deleted += 1
            else:
                failed += 1
                logger.error(f"   ⚠️  Failed: {result.get('error')}")

    # Clear database
    if args.clear_db:
        tracker.history.mappings = []
        tracker._save_history()
        logger.info("")
        logger.info("✅ Database cleared")

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"✅ Deleted: {deleted}, ❌ Failed: {failed}")
    logger.info("=" * 70)


def cmd_status(args):
    """Show sync status and statistics."""
    from project_chiang_m_ai.services.workout_tracker import WorkoutSyncTracker

    tracker = WorkoutSyncTracker()
    stats = tracker.get_stats()

    logger.info("=" * 70)
    logger.info("📊 LLM Coach - Status")
    logger.info("=" * 70)
    logger.info("")
    logger.info(f"Training periodization: {settings.PERIODIZATION}")
    logger.info(f"Block duration: {calculate_block_days(settings.PERIODIZATION)} days")
    logger.info("")
    tracker.print_stats()

    if args.list and stats["total_synced"] > 0:
        logger.info("")
        logger.info("📋 Synced Workouts:")
        logger.info("-" * 70)
        for mapping in tracker.history.mappings:
            status_emoji = {
                "uploaded": "✅",
                "failed": "❌",
                "updated": "🔄",
                "deleted": "🗑️",
            }.get(mapping.status, "❓")

            logger.info(
                f"{status_emoji} {mapping.source_summary} "
                f"→ {mapping.platform_name} (ID: {mapping.platform_id})"
            )
            logger.info(f"   Date: {mapping.source_start}")
            logger.info(f"   Synced: {mapping.synced_at[:10]}")
            logger.info("")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LLM Coach - Sync AI-generated workouts to your devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync current training block (based on PERIODIZATION setting)
  python -m project_chiang_m_ai sync --block

  # Sync this week
  python -m project_chiang_m_ai sync --week

  # Sync today only
  python -m project_chiang_m_ai sync --today

  # Sync next 14 days
  python -m project_chiang_m_ai sync --days 14

  # Adapt today's workouts using LLM based on wellness data
  python -m project_chiang_m_ai adapt

  # Show status
  python -m project_chiang_m_ai status

  # Clean up all synced workouts
  python -m project_chiang_m_ai clean
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync workouts to Intervals.icu")
    sync_group = sync_parser.add_mutually_exclusive_group()
    sync_group.add_argument(
        "--block", action="store_true", help="Sync current training block"
    )
    sync_group.add_argument(
        "--week", action="store_true", help="Sync this week (7 days)"
    )
    sync_group.add_argument(
        "--today", action="store_true", help="Sync today's workouts only"
    )
    sync_group.add_argument("--days", type=int, metavar="N", help="Sync next N days")
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse workouts but don't upload",
    )
    sync_parser.set_defaults(func=cmd_sync)

    # Clean command
    clean_parser = subparsers.add_parser(
        "clean", help="Delete synced workouts from Intervals.icu"
    )
    clean_parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation prompt"
    )
    clean_parser.add_argument(
        "--clear-db",
        action="store_true",
        help="Also clear sync database",
    )
    clean_parser.set_defaults(func=cmd_clean)

    # Status command
    status_parser = subparsers.add_parser("status", help="Show sync status")
    status_parser.add_argument(
        "--list", action="store_true", help="List all synced workouts"
    )
    status_parser.set_defaults(func=cmd_status)

    # Adapt command
    adapt_parser = subparsers.add_parser(
        "adapt", help="Adapt today's workouts based on wellness data"
    )
    adapt_parser.set_defaults(func=cmd_adapt)

    # Parse args
    args = parser.parse_args()

    # Show help if no command
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()
