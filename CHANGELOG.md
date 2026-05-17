# Changelog

All notable changes to **Project Chiang M-AI** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-05-17

### Added
- **TrainingPeaks Integration**: Added `TrainingPeaksClient` as a new `ISportPlatform` destination, enabling direct workout synchronization to TrainingPeaks using cookie-based authentication (`TP_AUTH_COOKIE`).
- **TrainingPeaks Wire Format Support**: Implemented transformation of simplified workout steps into TP's native hierarchical structure (nesting repetitions, converting intervals, calculating cumulative duration times).
- **Dynamic Sport Intensity Metrics**:
  - Automatically selects `percentOfFtp` (Power) for Cycling (`Bike`, `Ride`) and `percentOfThresholdHr` (Heart Rate) for Running (`Run`, `TrailRun`).
  - Automatically generates TrainingPeaks `polyline` segment data for high/low visualization in the UI.
- **Automatic Workout Metric Calculation**: Implemented automatic calculation of **Intensity Factor (IF)** and **Training Stress Score (TSS)** based on NP-style weighted average (4th power of zone midpoints) to pass API validations.

### Changed
- **Robust CI Testing**: Set `TP_AUTH_COOKIE` as optional in `Settings` configuration to prevent test suite validation crashes in CI/CD pipelines without environment credentials.
- **Agnostic Warnings**: Generalized command-line warning messages from "Intervals.icu" to "Sport Platform" for better alignment with multiple platforms.

## [1.1.0] - 2026-03-14

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
