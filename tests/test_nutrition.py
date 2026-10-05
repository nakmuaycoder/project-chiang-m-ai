"""
Unit tests for project_chiang_m_ai.nutrition module.
"""

import os
from unittest.mock import patch

from project_chiang_m_ai.nutrition import (
    HOM_MALI_RATIO,
    calculate_rice_plan,
    format_rice_plan_message,
    parse_rice_note_text,
    sanitize_for_free_mobile_sms,
)


def test_sanitize_for_free_mobile_sms():
    """Test emoji replacement, double newline collapsing, and unicode cleanup."""
    raw = "🍚 Plan Repas\n\n🛋️ Repos / Récupération\n\n🍌 1 Banane\n\n⚖️ TOTAL: 300g"
    sanitized = sanitize_for_free_mobile_sms(raw)

    assert "[RIZ]" in sanitized
    assert "[Repos]" in sanitized
    assert "[16h]" in sanitized
    assert "[Total]" in sanitized
    assert "\n\n" not in sanitized


def test_calculate_rice_plan_rest_day():
    """Test calculation for rest day (BMR baseline)."""
    # Rest day: no workouts (weekday: Monday 2026-02-02)
    plan = calculate_rice_plan("2026-02-02", [])
    assert plan["cat_key"] == "rest"
    assert plan["oats_breakfast"] == 60
    assert plan["intra_carbs"] == 0
    assert plan["has_snack"] is False
    assert plan["midi"] == 120
    assert plan["diner"] == 120
    assert plan["total_rice_cuit"] == 240
    assert plan["total_rice_cru"] == int(240 / HOM_MALI_RATIO)


def test_calculate_rice_plan_custom_bmr():
    """Test custom base_rice_meal and base_oats parameters and env vars."""
    plan = calculate_rice_plan("2026-02-02", [], base_rice_meal=150, base_oats=80)
    assert plan["oats_breakfast"] == 80
    assert plan["midi"] == 150
    assert plan["diner"] == 150

    with patch.dict(os.environ, {"BASE_RICE_MEAL": "140", "BASE_OATS": "70"}):
        plan_env = calculate_rice_plan("2026-02-02", [])
        assert plan_env["oats_breakfast"] == 70
        assert plan_env["midi"] == 140
        assert plan_env["diner"] == 140


def test_calculate_rice_plan_categories():
    """Test intensity categories and weekend vs weekday adjustments."""
    # 1. Light session (weekday, dur 1.0h, TSS 50)
    w_light = [{"totalTimePlanned": 1.0, "tssPlanned": 50, "elevationGainPlanned": 100}]
    p_light = calculate_rice_plan("2026-02-02", w_light)  # Monday
    assert p_light["cat_key"] == "light"
    assert p_light["intra_carbs"] == 30
    assert p_light["has_snack"] is True
    assert p_light["midi"] == 140
    assert p_light["diner"] == 160

    # 2. Moderate session (e.g. 2h30 Figuerolles - dur 2.5h, TSS 140, D+ 500)
    w_mod = [{"totalTimePlanned": 2.5, "tssPlanned": 140, "elevationGainPlanned": 500}]
    p_mod = calculate_rice_plan("2026-02-03", w_mod)  # Tuesday
    assert p_mod["cat_key"] == "moderate"
    assert p_mod["intra_carbs"] == 120

    # 3. High volume (dur 3.5h, TSS 200, D+ 1200)
    w_high = [
        {"totalTimePlanned": 3.5, "tssPlanned": 200, "elevationGainPlanned": 1200}
    ]
    p_high = calculate_rice_plan("2026-02-04", w_high)  # Wednesday
    assert p_high["cat_key"] == "high"
    assert p_high["intra_carbs"] == 200

    # 4. Peak / Ultra (dur 5.0h, TSS 300, D+ 2500)
    w_peak = [
        {"totalTimePlanned": 5.0, "tssPlanned": 300, "elevationGainPlanned": 2500}
    ]
    p_peak = calculate_rice_plan("2026-02-07", w_peak)  # Saturday (weekend)
    assert p_peak["cat_key"] == "peak"
    assert p_peak["intra_carbs"] == 300
    assert p_peak["oats_breakfast"] == 60 + 30  # weekend peak oats
    assert p_peak["midi"] == 120 + 130
    assert p_peak["diner"] == 120 + 160


def test_parse_rice_note_text_multi_lang():
    """Test parsing TrainingPeaks note text across FR, EN, and TH languages."""
    # French note
    fr_text = (
        "PLAN NUTRITION DU JOUR - 2026-02-02\n"
        "Catégorie : 🏃 Séance Léger / Maintien (Durée: 1.0h | TSS: 50 | D+: 100m)\n"
        "RÉPARTITION NUTRITION DU JOUR :\n"
        "- Petit-déjeuner : 60g Flocons d'Avoine\n"
        "- Pendant l'effort : 30g Glucides\n"
        "- Déjeuner (Midi) : 140g Riz Hom Mali Cuit\n"
        "- Collation 16h : 1 Banane\n"
        "- Dîner (Soir) : 160g Riz Hom Mali Cuit\n"
    )
    fr_parsed = parse_rice_note_text(fr_text, "2026-02-02")
    assert fr_parsed["oats_breakfast"] == 60
    assert fr_parsed["intra_carbs"] == 30
    assert fr_parsed["midi"] == 140
    assert fr_parsed["diner"] == 160
    assert fr_parsed["cat_key"] == "light"
    assert fr_parsed["total_dur"] == 1.0

    # English note
    en_text = (
        "DAILY NUTRITION PLAN - 2026-02-03\n"
        "Category : ⛰️ Moderate Session (Duration: 2.5h | TSS: 140 | D+: 500m)\n"
        "- Breakfast: 70g Rolled Oats\n"
        "- During Workout: 120g Carbs\n"
        "- Lunch: 180g Cooked Hom Mali Rice\n"
        "- Dinner: 220g Cooked Hom Mali Rice\n"
    )
    en_parsed = parse_rice_note_text(en_text, "2026-02-03")
    assert en_parsed["oats_breakfast"] == 70
    assert en_parsed["intra_carbs"] == 120
    assert en_parsed["midi"] == 180
    assert en_parsed["diner"] == 220
    assert en_parsed["cat_key"] == "moderate"

    # Thai note
    th_text = (
        "แผนโภชนาการประจำวัน - 2026-02-07\n"
        "ประเภท : 👑 พีค 100 ไมล์ / อัลตร้า (ระยะเวลา: 5.0h | TSS: 300 | ความชัน: 2500m)\n"
        "- มื้อเช้า: ข้าวโอ๊ต 90g\n"
        "- ระหว่างออกกำลังกาย: คาร์บ 300g\n"
        "- มื้อเที่ยง: ข้าวหอมมะลิสุก 250g\n"
        "- มื้อเย็น: ข้าวหอมมะลิสุก 300g\n"
    )
    th_parsed = parse_rice_note_text(th_text, "2026-02-07")
    assert th_parsed["oats_breakfast"] == 90
    assert th_parsed["intra_carbs"] == 300
    assert th_parsed["midi"] == 250
    assert th_parsed["diner"] == 300
    assert th_parsed["cat_key"] == "peak"


def test_format_rice_plan_message():
    """Test message formatting for default display and SMS across languages."""
    plan = {
        "day": "2026-02-02",
        "cat_key": "light",
        "oats_breakfast": 60,
        "intra_carbs": 30,
        "has_snack": True,
        "midi": 140,
        "diner": 160,
        "total_rice_cuit": 300,
        "total_rice_cru": 127,
        "total_dur": 1.0,
        "total_tss": 50.0,
        "total_dplus": 100,
    }

    # French standard display
    title_fr, body_fr = format_rice_plan_message(plan, lang="fr", for_sms=False)
    assert "Plan Repas & Riz Hom Mali : 300g" in title_fr
    assert "PLAN NUTRITION DU JOUR" in body_fr
    assert "140g Riz Hom Mali Cuit" in body_fr

    # Thai SMS format
    title_th_sms, body_th_sms = format_rice_plan_message(plan, lang="th", for_sms=True)
    assert "[แผนข้าวหอมมะลิ 2026-02-02]" in title_th_sms
    assert "มื้อเช้า: ข้าวโอ๊ต 60g" in body_th_sms
    assert "มื้อเที่ยง: ข้าวหอมมะลิสุก 140g" in body_th_sms
    assert "\n\n" not in body_th_sms  # verify SMS sanitization
