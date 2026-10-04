"""
Script: generate_all_rice_notes.py

Generates and posts Day Notes on TrainingPeaks for all days in the plan
specifying exact Cooked Rice (Riz Cuit) quantities in grams for:
- Petit-déjeuner (Breakfast)
- Déjeuner (Midi)
- Collation 16h (Afternoon Snack)
- Dîner (Evening Meal)

Calculated based on athlete weight (~91kg), workout timing,
duration, elevation gain (D+), and TSS planned.
"""

import sys
from datetime import datetime, timedelta

import requests

# Ensure src is on python path
sys.path.insert(0, "src")

from project_chiang_m_ai.clients.trainingpeaks import TrainingPeaksClient


def calculate_rice_plan(day_str: str, workouts: list[dict]) -> dict:
    dt = datetime.strptime(day_str, "%Y-%m-%d")
    is_weekend = dt.weekday() >= 5  # 5=Saturday, 6=Sunday

    # Total planned TSS & duration for the day
    total_tss = sum(w.get("tssPlanned") or w.get("tssActual") or 0 for w in workouts)
    total_dur = sum(
        w.get("totalTimePlanned") or w.get("totalTime") or 0 for w in workouts
    )
    total_dplus = sum(
        w.get("elevationGainPlanned") or w.get("elevationGain") or 0 for w in workouts
    )

    # Base rice targets in grams of COOKED RICE (Riz Cuit) for ~91kg athlete
    if total_dur == 0 or total_tss == 0:
        # --- REST DAY ---
        breakfast = 60
        midi = 120
        snack = 0
        diner = 120
        category = "🛋️ Repos / Récupération"
    elif total_dur <= 1.25 and total_tss < 75:
        # --- LIGHT WORKOUT DAY ---
        if is_weekend:
            breakfast = 80
            midi = 240
            snack = 0
            diner = 150
        else:
            breakfast = 60
            midi = 180
            snack = 80
            diner = 220
        category = "🏃 Séance Léger / Maintien"
    elif total_dur <= 2.5 or (total_tss < 160 and total_dplus < 1000):
        # --- MODERATE WORKOUT DAY ---
        if is_weekend:
            breakfast = 100
            midi = 350
            snack = 80
            diner = 180
        else:
            breakfast = 80
            midi = 220
            snack = 120
            diner = 320
        category = "⛰️ Séance Modérée / Trail"
    elif total_dur <= 4.0 or (total_tss < 260 and total_dplus < 1800):
        # --- HIGH VOLUME DAY ---
        if is_weekend:
            breakfast = 120
            midi = 480
            snack = 100
            diner = 220
        else:
            breakfast = 90
            midi = 280
            snack = 150
            diner = 450
        category = "💣 Gros Volume / D+"
    else:
        # --- PEAK / ULTRA DAY (5h+ or 1800m+ D+) ---
        if is_weekend:
            breakfast = 150
            midi = 650
            snack = 150
            diner = 300
        else:
            breakfast = 100
            midi = 350
            snack = 200
            diner = 600
        category = "👑 PEAK 100-MILES / Ultra"

    total_rice_cuit = breakfast + midi + snack + diner
    total_rice_cru = int(total_rice_cuit / 3.0)

    return {
        "day": day_str,
        "category": category,
        "breakfast": breakfast,
        "midi": midi,
        "snack": snack,
        "diner": diner,
        "total_cuit": total_rice_cuit,
        "total_cru": total_rice_cru,
        "total_dur": round(total_dur, 2),
        "total_tss": round(total_tss, 1),
        "total_dplus": int(total_dplus),
    }


def main():
    client = TrainingPeaksClient()
    token = client._get_access_token()
    athlete_id = client._get_athlete_id()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    start_date = "2026-10-04"
    end_date = "2026-12-07"  # Through Chiang Mai 160k

    print(f"📅 Fetching calendar workouts from {start_date} to {end_date}...")
    tp_base = "https://tpapi.trainingpeaks.com"
    url_w = (
        f"{tp_base}/fitness/v6/athletes/{athlete_id}/workouts/{start_date}/{end_date}"
    )
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

        title = f"🍚 Plan Riz Cuit : {plan['total_cuit']}g ({plan['category']})"

        dur_str = f"Durée: {plan['total_dur']}h"
        tss_str = f"TSS: {plan['total_tss']}"
        dplus_str = f"D+: {plan['total_dplus']}m"

        desc_lines = [
            f"🎯 PLAN NUTRITION RIZ CUIT - {day_str}",
            f"Catégorie : {plan['category']} ({dur_str} | {tss_str} | {dplus_str})",
            "",
            "🍚 QUANTITÉS EN GRAMMES DE RIZ CUIT (dans l'assiette) :",
            f"- 🌅 Petit-déjeuner : {plan['breakfast']}g (riz cuit / crème de riz)",
            f"- ☀️ Déjeuner (Midi) : {plan['midi']}g",
        ]
        if plan["snack"] > 0:
            snack_txt = f"- 🍎 Collation 16h  : {plan['snack']}g"
            desc_lines.append(snack_txt)
        else:
            desc_lines.append("- 🍎 Collation 16h  : Repos (0g)")

        tot_cuit = plan["total_cuit"]
        tot_cru = plan["total_cru"]
        desc_lines.extend(
            [
                f"- 🌙 Dîner (Soir)    : {plan['diner']}g",
                "",
                f"⚖️ TOTAL DU JOUR : {tot_cuit}g Riz Cuit (~{tot_cru}g Riz Sec / Cru)",
            ]
        )

        description = "\n".join(desc_lines)

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
