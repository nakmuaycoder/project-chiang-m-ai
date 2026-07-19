from unittest.mock import MagicMock, patch

from project_chiang_m_ai.clients.intervalicu import IntervalicuClient


@patch("project_chiang_m_ai.clients.intervalicu.requests.get")
@patch("project_chiang_m_ai.clients.intervalicu.settings")
def test_intervalicu_get_metrics(mock_settings, mock_get):
    """Test that fetching metrics from Intervals.icu returns the correct schema."""
    mock_settings.INTERVALS_ATHLETE_ID = "athlete123"
    mock_settings.INTERVALS_API_KEY.get_secret_value.return_value = "fake_key"
    mock_settings.API_TIMEOUT = 10

    # Mock response
    mock_r = MagicMock()
    mock_r.status_code = 200
    mock_r.json.return_value = [
        {
            "id": "2026-01-01",
            "hrv": 55.4,
            "restingHR": 52,
        },
        {
            "id": "2026-01-02",
            "hrv": 58.0,
            # restingHR missing or None
        },
    ]
    mock_get.return_value = mock_r

    client = IntervalicuClient()
    metrics = client.get_metrics("2026-01-01", "2026-01-02")

    # We expect 3 records:
    # 1. 2026-01-01 HRV
    # 2. 2026-01-01 RestingHR
    # 3. 2026-01-02 HRV
    assert len(metrics) == 3
    assert metrics[0] == {
        "Timestamp": "2026-01-01 00:00:00",
        "Type": "HRV",
        "Value": "55.4",
    }
    assert metrics[1] == {
        "Timestamp": "2026-01-01 00:00:00",
        "Type": "RestingHR",
        "Value": "52",
    }
    assert metrics[2] == {
        "Timestamp": "2026-01-02 00:00:00",
        "Type": "HRV",
        "Value": "58.0",
    }


@patch("project_chiang_m_ai.clients.intervalicu.requests.get")
@patch("project_chiang_m_ai.clients.intervalicu.settings")
def test_intervalicu_get_metrics_error_format(mock_settings, mock_get):
    """Test that get_metrics returns empty list on invalid JSON response format."""
    mock_settings.INTERVALS_ATHLETE_ID = "athlete123"
    mock_settings.INTERVALS_API_KEY.get_secret_value.return_value = "fake_key"
    mock_settings.API_TIMEOUT = 10

    # Mock response returning dict instead of list
    mock_r = MagicMock()
    mock_r.status_code = 200
    mock_r.json.return_value = {"error": "rate limit"}
    mock_get.return_value = mock_r

    client = IntervalicuClient()
    metrics = client.get_metrics("2026-01-01", "2026-01-02")
    assert metrics == []
