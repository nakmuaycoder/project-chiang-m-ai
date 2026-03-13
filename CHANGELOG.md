# Changelog

All notable changes to **Project Chiang M-AI** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Modular Architecture (Brain vs. Platform)**: Decoupled workout decision logic (`IBrain`) from data storage/sync logic (`ISportPlatform`).
- **Local Testing Support**: Added `LocalArchivePlatform` to save workouts as local JSON files for safer testing and AI output comparison.
- **Factory Pattern**: Implemented `get_brain()` and `get_platform()` for flexible dependency injection based on configuration.
- **YAML Configuration**: Introduced `coach_config.yaml` to manage modular components and sync modes centrally.
- **Stable Tracking**: Switched from fragile name-based IDs to stable source IDs (e.g., Google Calendar Event IDs) to prevent duplicate workouts when renaming events.
- **Calendar Base Intelligence**: Extracted shared logic for calendar fetching, filtering, and parsing into a reusable `CalendarBaseBrain`.

### Changed
- Refactored `CoachService` to be implementation-agnostic, using injected `IBrain` and `ISportPlatform` instances.
- Updated `AutoAdaptiveBrain` and `GoogleCalendarBrain` to inherit from `CalendarBaseBrain` (DRY).
- Improved error handling for Pydantic validation and JSON parsing across all brain implementations.

### Fixed
- Restored `cleanup_orphaned_workouts` functionality within the new modular architecture.
- Fixed a bug where renaming a workout in the source would lead to a duplicate on the platform.
- Resolved various Ruff linting issues (E501 line length).
