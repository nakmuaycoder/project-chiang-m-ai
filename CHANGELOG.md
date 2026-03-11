# Changelog

All notable changes to **Project Chiang M-AI** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **LLM Wellness Adaptation**: The AI Coach can now dynamically adapt your daily scheduled workouts based on recent Health & Readiness data (HRV and RHR) from Intervals.icu before syncing.
- Added `python -m project_chiang_m_ai adapt` command to run the wellness adjustment logic.
- Integration with the `google-genai` package for interacting with Gemini APIs natively.
- Added a highly flexible PromptBuilder for templates management, allowing for separation of code and prompt text logic.
- Implemented `ILlmClient` interface so developers can seamlessly plug in alternative AI backends like Anthropic Claude or OpenAI ChatGPT.
- Added `.env` configuration for `LLM_PROVIDER`, `LLM_MODEL`, `GEMINI_API_KEY`, and `WELLNESS_HISTORY_DAYS`.
- Modified Pydantic model structure to wrap the `original_workout` under the hood dynamically whenever a workout is transformed by the LLM.
