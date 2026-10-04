"""
Module: project_chiang_m_ai.nutrition

Daily carbohydrate calculation, BMR baseline customization, intra-workout fueling,
Hom Mali Jasmine Rice (Rice Cooker ratio), multi-language formatting (FR, EN, TH),
and Free Mobile SMS sanitization for Chiang Mai 160k.
"""

import os
import re
from datetime import datetime

SUPPORTED_LANGUAGES = ["fr", "en", "th"]

# Hom Mali Rice Cooker ratio: 1g dry Hom Mali rice yields ~2.35g cooked rice.
HOM_MALI_RATIO = 2.35

NUTRITION_TRANSLATIONS = {
    "fr": {
        "title_prefix": "Plan Repas & Riz Hom Mali",
        "header": "PLAN NUTRITION DU JOUR - {date}",
        "category_label": "Catégorie",
        "duration": "Durée",
        "dplus": "D+",
        "breakdown_header": "RÉPARTITION NUTRITION DU JOUR :",
        "breakfast": "Petit-déjeuner : {oats}g Flocons d'Avoine",
        "intra": "Pendant l'effort : {intra}g Glucides (Boisson d'effort & Gels)",
        "intra_rest": "Pendant l'effort : 0g (Repos)",
        "lunch": "Déjeuner (Midi) : {midi}g Riz Hom Mali Cuit",
        "snack": "Collation 16h : 1 Banane (~25g glucides)",
        "snack_rest": "Collation 16h : Repos (0g)",
        "dinner": "Dîner (Soir) : {diner}g Riz Hom Mali Cuit",
        "total": (
            "TOTAL RIZ HOM MALI JOUR : {total_cuit}g Cuit "
            "(~{total_cru}g Sec Rice Cooker)"
        ),
        "no_note": "Plan Riz ({date}) : Aucune note trouvée sur TrainingPeaks.",
        "categories": {
            "rest": "🛋️ Repos / Récupération",
            "light": "🏃 Séance Léger / Maintien",
            "moderate": "⛰️ Séance Modérée / 2h30 Figuerolles",
            "high": "💣 Gros Volume / D+",
            "peak": "👑 PEAK 100-MILES / Ultra",
        },
    },
    "en": {
        "title_prefix": "Hom Mali Rice Plan",
        "header": "DAILY NUTRITION PLAN - {date}",
        "category_label": "Category",
        "duration": "Duration",
        "dplus": "D+",
        "breakdown_header": "DAILY NUTRITION BREAKDOWN:",
        "breakfast": "Breakfast: {oats}g Rolled Oats",
        "intra": "During Workout: {intra}g Carbs (Sports Drink & Gels)",
        "intra_rest": "During Workout: 0g (Rest)",
        "lunch": "Lunch: {midi}g Cooked Hom Mali Rice",
        "snack": "Afternoon Snack (4PM): 1 Banana (~25g carbs)",
        "snack_rest": "Afternoon Snack (4PM): Rest (0g)",
        "dinner": "Dinner: {diner}g Cooked Hom Mali Rice",
        "total": (
            "TOTAL HOM MALI RICE: {total_cuit}g Cooked (~{total_cru}g Dry Rice Cooker)"
        ),
        "no_note": "Rice Plan ({date}): No note found on TrainingPeaks.",
        "categories": {
            "rest": "🛋️ Rest / Recovery",
            "light": "🏃 Light Session / Maintenance",
            "moderate": "⛰️ Moderate Session / 2h30 Figuerolles",
            "high": "💣 High Volume / Elevation",
            "peak": "👑 PEAK 100-MILES / Ultra",
        },
    },
    "th": {
        "title_prefix": "แผนข้าวหอมมะลิ",
        "header": "แผนโภชนาการประจำวัน - {date}",
        "category_label": "ประเภท",
        "duration": "ระยะเวลา",
        "dplus": "ความชัน",
        "breakdown_header": "ตารางโภชนาการประจำวัน:",
        "breakfast": "มื้อเช้า: ข้าวโอ๊ต {oats}g",
        "intra": "ระหว่างออกกำลังกาย: คาร์บ {intra}g (เครื่องดื่มเกลือแร่ & เจล)",
        "intra_rest": "ระหว่างออกกำลังกาย: 0g (พักผ่อน)",
        "lunch": "มื้อเที่ยง: ข้าวหอมมะลิสุก {midi}g",
        "snack": "อาหารว่าง (16:00 น.): กล้วย 1 ลูก (~25g คาร์บ)",
        "snack_rest": "อาหารว่าง (16:00 น.): พักผ่อน (0g)",
        "dinner": "มื้อเย็น: ข้าวหอมมะลิสุก {diner}g",
        "total": (
            "รวมข้าวหอมมะลิประจำวัน: {total_cuit}g สุก (~ข้าวสาร {total_cru}g หม้อหุงข้าว)"
        ),
        "no_note": "แผนข้าว ({date}): ไม่พบโน้ตบน TrainingPeaks",
        "categories": {
            "rest": "🛋️ พักผ่อน / ฟื้นฟู",
            "light": "🏃 ออกกำลังกายเบาๆ / ประคอง",
            "moderate": "⛰️ ออกกำลังกายปานกลาง / 2ชม.30 Figuerolles",
            "high": "💣 ปริมาณมาก / ความชันสูง",
            "peak": "👑 พีค 100 ไมล์ / อัลตร้า",
        },
    },
}


def sanitize_for_free_mobile_sms(text: str) -> str:
    """Strips Emojis and converts characters for Free Mobile SMS API."""
    replacements = {
        "🍚": "[RIZ]",
        "🎯": "[PLAN]",
        "🌅": "[Matin]",
        "⚡": "[Effort]",
        "☀️": "[Midi]",
        "🍌": "[16h]",
        "🍎": "[16h]",
        "🌙": "[Soir]",
        "⚖️": "[Total]",
        "⚖": "[Total]",
        "🛋️": "[Repos]",
        "🛋": "[Repos]",
        "🏃": "[Courir]",
        "⛰️": "[Trail]",
        "⛰": "[Trail]",
        "💣": "[Volume]",
        "👑": "[Peak]",
        "📱": "",
        "🔑": "",
        "⚠️": "",
        "️": "",  # variation selector-16
    }
    for emoji, replacement in replacements.items():
        text = text.replace(emoji, replacement)

    # Replace double newlines with single newline for Free Mobile API stability
    while "\n\n" in text:
        text = text.replace("\n\n", "\n")

    # Remove any remaining 4-byte unicode / emoji characters
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    return text


def calculate_rice_plan(
    day_str: str,
    workouts: list[dict],
    base_rice_meal: int | None = None,
    base_oats: int | None = None,
) -> dict:
    """
    Calculates daily Hom Mali rice, oats, intra-workout carbs, and snack targets.

    BMR (Basal Metabolic Rate) baseline is determined by base_rice_meal
    (default: 120g cooked Hom Mali per meal) and base_oats (default: 60g).
    Can be configured via arguments or environment variables BASE_RICE_MEAL / BASE_OATS.
    """
    dt = datetime.strptime(day_str, "%Y-%m-%d")
    is_weekend = dt.weekday() >= 5  # 5=Saturday, 6=Sunday

    if base_rice_meal is None:
        base_rice_meal = int(os.getenv("BASE_RICE_MEAL", "120"))
    if base_oats is None:
        base_oats = int(os.getenv("BASE_OATS", "60"))

    total_tss = sum(w.get("tssPlanned") or w.get("tssActual") or 0 for w in workouts)
    total_dur = sum(
        w.get("totalTimePlanned") or w.get("totalTime") or 0 for w in workouts
    )
    total_dplus = sum(
        w.get("elevationGainPlanned") or w.get("elevationGain") or 0 for w in workouts
    )

    oats_breakfast = base_oats

    if total_dur == 0 or total_tss == 0:
        # --- REST DAY (BMR BASELINE) ---
        cat_key = "rest"
        intra_carbs = 0
        has_snack = False
        midi = base_rice_meal
        diner = base_rice_meal
    elif total_dur <= 1.25 and total_tss < 75:
        # --- LIGHT SESSION ---
        cat_key = "light"
        intra_carbs = 30
        has_snack = True
        if is_weekend:
            oats_breakfast = base_oats + 10
            midi = base_rice_meal + 40
            diner = base_rice_meal + 20
        else:
            midi = base_rice_meal + 20
            diner = base_rice_meal + 40
    elif total_dur <= 2.6 or (total_tss < 160 and total_dplus < 1000):
        # --- MODERATE SESSION (e.g. 2h30 Figuerolles) ---
        cat_key = "moderate"
        intra_carbs = 120
        has_snack = True
        if is_weekend:
            oats_breakfast = base_oats + 20
            midi = base_rice_meal + 60
            diner = base_rice_meal + 60
        else:
            midi = base_rice_meal + 60
            diner = base_rice_meal + 100
    elif total_dur <= 4.0 or (total_tss < 260 and total_dplus < 1800):
        # --- HIGH VOLUME DAY ---
        cat_key = "high"
        intra_carbs = 200
        has_snack = True
        if is_weekend:
            oats_breakfast = base_oats + 20
            midi = base_rice_meal + 100
            diner = base_rice_meal + 100
        else:
            midi = base_rice_meal + 100
            diner = base_rice_meal + 130
    else:
        # --- PEAK / ULTRA DAY (5h+) ---
        cat_key = "peak"
        intra_carbs = 300
        has_snack = True
        if is_weekend:
            oats_breakfast = base_oats + 30
            midi = base_rice_meal + 130
            diner = base_rice_meal + 160
        else:
            midi = base_rice_meal + 140
            diner = base_rice_meal + 180

    total_rice_cuit = midi + diner
    total_rice_cru = int(total_rice_cuit / HOM_MALI_RATIO)

    return {
        "day": day_str,
        "cat_key": cat_key,
        "oats_breakfast": oats_breakfast,
        "intra_carbs": intra_carbs,
        "has_snack": has_snack,
        "midi": midi,
        "diner": diner,
        "total_rice_cuit": total_rice_cuit,
        "total_rice_cru": total_rice_cru,
        "total_dur": round(total_dur, 2),
        "total_tss": round(total_tss, 1),
        "total_dplus": int(total_dplus),
    }


def parse_rice_note_text(raw_text: str, day_str: str) -> dict:
    """Extract numerical plan values from TP note description (FR, EN, TH)."""
    oats_match = re.search(
        r"(?:Petit-déjeuner|Breakfast|มื้อเช้า)\s*:\s*(?:ข้าวโอ๊ต\s*)?(\d+)g",
        raw_text,
        re.IGNORECASE,
    )
    intra_match = re.search(
        r"(?:Pendant l'effort|During Workout|ระหว่างออกกำลังกาย)"
        r"\s*:\s*(?:คาร์บ\s*)?(\d+)g",
        raw_text,
        re.IGNORECASE,
    )
    midi_match = re.search(
        r"(?<![a-zA-Z-])(?:Déjeuner|Lunch|มื้อเที่ยง)[^:\n]*:?\s*[^\d\n]*(\d+)g",
        raw_text,
        re.IGNORECASE,
    )
    diner_match = re.search(
        r"(?:Dîner|Dinner|มื้อเย็น)[^:\n]*:?\s*[^\d\n]*(\d+)g",
        raw_text,
        re.IGNORECASE,
    )

    dur_match = re.search(
        r"(?:Durée|Duration|ระยะเวลา)\s*:\s*([\d\.]+)h?",
        raw_text,
        re.IGNORECASE,
    )
    tss_match = re.search(r"TSS\s*:\s*([\d\.]+)", raw_text, re.IGNORECASE)
    dplus_match = re.search(
        r"(?:D\+|Elevation|ความชัน)\s*:\s*(\d+)m?",
        raw_text,
        re.IGNORECASE,
    )

    oats = int(oats_match.group(1)) if oats_match else 60
    intra = int(intra_match.group(1)) if intra_match else 0
    midi = int(midi_match.group(1)) if midi_match else 150
    diner = int(diner_match.group(1)) if diner_match else 180

    dur = float(dur_match.group(1)) if dur_match else 0.0
    tss = float(tss_match.group(1)) if tss_match else 0.0
    dplus = int(dplus_match.group(1)) if dplus_match else 0

    cat_key = "rest"
    if any(k in raw_text for k in ["Léger", "Maintenance", "Light", "เบา"]):
        cat_key = "light"
    elif any(k in raw_text for k in ["Modérée", "Moderate", "Figuerolles", "ปานกลาง"]):
        cat_key = "moderate"
    elif any(k in raw_text for k in ["Volume", "Gros", "High", "ปริมาณมาก"]):
        cat_key = "high"
    elif any(k in raw_text for k in ["PEAK", "Ultra", "พีค"]):
        cat_key = "peak"

    tot_cuit = midi + diner
    tot_cru = int(tot_cuit / HOM_MALI_RATIO)

    return {
        "day": day_str,
        "cat_key": cat_key,
        "oats_breakfast": oats,
        "intra_carbs": intra,
        "has_snack": dur > 0,
        "midi": midi,
        "diner": diner,
        "total_rice_cuit": tot_cuit,
        "total_rice_cru": tot_cru,
        "total_dur": dur,
        "total_tss": tss,
        "total_dplus": dplus,
    }


def format_rice_plan_message(
    plan: dict, lang: str = "fr", for_sms: bool = False
) -> tuple[str, str]:
    """Formats the nutrition plan title and description for display or SMS."""
    lang_code = lang.lower().strip()
    if lang_code not in SUPPORTED_LANGUAGES:
        lang_code = "fr"

    t = NUTRITION_TRANSLATIONS[lang_code]
    cat_key = plan.get("cat_key", "rest")
    category_name = t["categories"].get(cat_key, t["categories"]["rest"])

    date_str = plan["day"]
    tot_cuit = plan["total_rice_cuit"]
    tot_cru = plan["total_rice_cru"]
    intra = plan.get("intra_carbs", 0)

    dur_str = f"{t['duration']}: {plan['total_dur']}h"
    tss_str = f"TSS: {plan['total_tss']}"
    dplus_str = f"{t['dplus']}: {plan['total_dplus']}m"

    cat_line = (
        f"{t['category_label']} : {category_name} ({dur_str} | {tss_str} | {dplus_str})"
    )

    if for_sms:
        title = f"[{t['title_prefix']} {date_str}]"
        lines = [
            title,
            cat_line,
            t["breakdown_header"],
            f"- 🌅 {t['breakfast'].format(oats=plan['oats_breakfast'])}",
        ]
    else:
        title = f"🍚 {t['title_prefix']} : {tot_cuit}g ({category_name})"
        header = t["header"].format(date=date_str)
        lines = [
            title,
            f"{t['title_prefix']} : {tot_cuit}g ({category_name})",
            "",
            header,
            cat_line,
            "",
            t["breakdown_header"],
            f"- 🌅 {t['breakfast'].format(oats=plan['oats_breakfast'])}",
        ]

    if intra > 0:
        lines.append(f"- ⚡ {t['intra'].format(intra=intra)}")
    else:
        lines.append(f"- ⚡ {t['intra_rest']}")

    lines.append(f"- ☀️ {t['lunch'].format(midi=plan['midi'])}")

    if plan.get("has_snack"):
        lines.append(f"- 🍌 {t['snack']}")
    else:
        lines.append(f"- 🍌 {t['snack_rest']}")

    lines.extend(
        [
            f"- 🌙 {t['dinner'].format(diner=plan['diner'])}",
            "",
            f"⚖️ {t['total'].format(total_cuit=tot_cuit, total_cru=tot_cru)}",
        ]
    )

    full_text = "\n".join(lines)

    if for_sms:
        full_text = sanitize_for_free_mobile_sms(full_text)

    return title, full_text
