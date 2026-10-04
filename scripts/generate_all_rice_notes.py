"""
Script: generate_all_rice_notes.py

Generates and posts Day Notes on TrainingPeaks for all days in the plan
specifying exact Cooked Rice (Riz Cuit) quantities for Midi and Dîner,
Intra-workout Carbs (Gels & Sports Drink), 16h Banana snack, and Rolled Oats.
"""

import sys
from datetime import datetime, timedelta

import requests

# Ensure src is on python path
sys.path.insert(0, "src")

from project_chiang_m_ai.clients.trainingpeaks import (  # noqa: E402
    TrainingPeaksClient,
)
from project_chiang_m_ai.nutrition import (  # noqa: E402
    calculate_rice_plan,
    format_rice_plan_message,
)


def main():
    client = TrainingPeaksClient()
    token = client._get_access_token()
    athlete_id = client._get_athlete_id()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    start_date = "2026-10-04"
    end_date = "2026-12-07"  # Through Chiang Mai 160k

    print(f"📅 Fetching calendar workouts from {start_date} to {end_date}...")
    tp_base = "https://tpapi.trainingpeaks.com"
    endpoint = f"/fitness/v6/athletes/{athlete_id}/workouts/{start_date}/{end_date}"
    url_w = f"{tp_base}{endpoint}"
    res = requests.get(url_w, headers=headers, timeout=15)
    res.raise_for_status()
    all_items = res.json()

    workouts_by_day = {}
    existing_notes_by_day = {}

    for item in all_items:
        day_str = item.get("workoutDay", "")[:10]
        if not day_str:
            continue
        if item.get("workoutTypeValueId") == 100:
            existing_notes_by_day[day_str] = item.get("workoutId")
        else:
            workouts_by_day.setdefault(day_str, []).append(item)

    current_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    count_created = 0
    count_updated = 0

    while current_dt <= end_dt:
        day_str = current_dt.strftime("%Y-%m-%d")
        w_list = workouts_by_day.get(day_str, [])
        plan = calculate_rice_plan(day_str, w_list)

        title, description = format_rice_plan_message(plan, lang="fr", for_sms=False)

        if day_str in existing_notes_by_day:
            n_id = existing_notes_by_day[day_str]
            put_url = f"{tp_base}/fitness/v6/athletes/{athlete_id}/workouts/{n_id}"
            payload = {
                "athleteId": athlete_id,
                "workoutId": n_id,
                "workoutDay": f"{day_str}T00:00:00",
                "title": title,
                "description": description,
                "workoutTypeFamilyId": 0,
                "workoutTypeValueId": 100,
            }
            r = requests.put(put_url, headers=headers, json=payload, timeout=15)
            if r.status_code in (200, 201):
                count_updated += 1
        else:
            res_add = client.add_day_note(day_str, title, description)
            if res_add.get("success"):
                count_created += 1

        current_dt += timedelta(days=1)

    print(
        f"🎉 Complete! Day Notes processed: {count_created} created, "
        f"{count_updated} updated."
    )


if __name__ == "__main__":
    main()
