"""
Basic tests for Project Chiang M-ai .
"""

from datetime import datetime, timezone

import pytest

from project_chiang_m_ai.cli import calculate_block_days
from project_chiang_m_ai.interfaces.calendar import CalendarEvent


def test_imports():
    """Test that main modules can be imported."""
    import importlib

    modules = [
        "project_chiang_m_ai.config",
        "project_chiang_m_ai.factory",
        "project_chiang_m_ai.services.coach",
    ]
    for module in modules:
        try:
            importlib.import_module(module)
        except ImportError as e:
            pytest.fail(f"Failed to import {module}: {e}")


def test_calendar_event_model():
    """Test CalendarEvent model validation."""
    now = datetime.now(timezone.utc)

    # Valid event
    event = CalendarEvent(
        id="test-123",
        summary="Test Run",
        start=now,
        end=now,
        description='{"type": "Run", "duration": "30m"}',
    )
    assert event.id == "test-123"
    assert event.summary == "Test Run"

    # Check default raw_data is None
    assert event.raw_data is None


def test_periodization_logic():
    """Test periodization calculation logic."""
    assert calculate_block_days("3:1") == 28
    assert calculate_block_days("2:1") == 21

    # Test fallback
    assert calculate_block_days("unknown") == 28
