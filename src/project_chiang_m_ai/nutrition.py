"""
Module: project_chiang_m_ai.nutrition

Daily carbohydrate calculation and multi-language formatting (FR, EN, TH)
for ultra-marathon training (Hoka Chiang Mai 160k).
"""

import re
from datetime import datetime

SUPPORTED_LANGUAGES = ["fr", "en", "th"]

NUTRITION_TRANSLATIONS = {
    "fr": {
        "title_prefix": "Plan Repas & Riz",
        "header": "PLAN NUTRITION DU JOUR - {date}",
        "category_label": "Catégorie",
        "duration": "Durée",
        "dplus": "D+",
        "breakdown_header": "RÉPARTITION DES REPAS DU JOUR :",
        "breakfast": "Petit-déjeuner : {oats}g Flocons d'Avoine",
        "lunch": "Déjeuner (Midi) : {midi}g Riz Cuit",
        "snack": "Collation 16h : {snack}g Riz Cuit / Compote",
        "snack_rest": "Collation 16h : Repos (0g)",
        "dinner": "Dîner (Soir) : {diner}g Riz Cuit",
        "total": "TOTAL RIZ CUIT JOUR : {total_cuit}g Riz Cuit (~{total_cru}g Riz Sec)",
        "no_note": "Plan Riz ({date}) : Aucune note trouvée sur TrainingPeaks.",
        "categories": {
            "rest": "🛋️ Repos / Récupération",
            "light": "🏃 Séance Léger / Maintien",
            "moderate": "⛰️ Séance Modérée / Trail",
            "high": "💣 Gros Volume / D+",
            "peak": "👑 PEAK 100-MILES / Ultra",
        },
    },
    "en": {
        "title_prefix": "Meal & Rice Plan",
        "header": "DAILY NUTRITION PLAN - {date}",
        "category_label": "Category",
        "duration": "Duration",
        "dplus": "D+",
        "breakdown_header": "DAILY MEAL BREAKDOWN:",
        "breakfast": "Breakfast: {oats}g Rolled Oats",
        "lunch": "Lunch: {midi}g Cooked Rice",
        "snack": "Afternoon Snack (4PM): {snack}g Cooked Rice / Compote",
        "snack_rest": "Afternoon Snack (4PM): Rest (0g)",
        "dinner": "Dinner: {diner}g Cooked Rice",
        "total": (
            "TOTAL DAILY COOKED RICE: {total_cuit}g Cooked Rice "
            "(~{total_cru}g Dry Rice)"
        ),
        "no_note": "Rice Plan ({date}): No note found on TrainingPeaks.",
        "categories": {
            "rest": "🛋️ Rest / Recovery",
            "light": "🏃 Light Session / Maintenance",
            "moderate": "⛰️ Moderate Session / Trail",
            "high": "💣 High Volume / Elevation",
            "peak": "👑 PEAK 100-MILES / Ultra",
        },
    },
    "th": {
        "title_prefix": "แผนอาหาร & ข้าว",
        "header": "แผนโภชนาการประจำวัน - {date}",
        "category_label": "ประเภท",
        "duration": "ระยะเวลา",
        "dplus": "ความชัน",
        "breakdown_header": "ตารางมื้ออาหารประจำวัน:",
        "breakfast": "มื้อเช้า: ข้าวโอ๊ต {oats}g",
        "lunch": "มื้อเที่ยง: ข้าวสวย {midi}g",
        "snack": "อาหารว่าง (16:00 น.): ข้าวสวย {snack}g / แอปเปิ้ลซอส",
        "snack_rest": "อาหารว่าง (16:00 น.): พักผ่อน (0g)",
        "dinner": "มื้อเย็น: ข้าวสวย {diner}g",
        "total": "รวมข้าวสวยประจำวัน: {total_cuit}g (~ข้าวสาร {total_cru}g)",
        "no_note": "แผนข้าว ({date}): ไม่พบโน้ตบน TrainingPeaks",
        "categories": {
            "rest": "🛋️ พักผ่อน / ฟื้นฟู",
            "light": "🏃 ออกกำลังกายเบาๆ / ประคอง",
            "moderate": "⛰️ ออกกำลังกายปานกลาง / เทรล",
            "high": "💣 ปริมาณมาก / ความชันสูง",
            "peak": "👑 พีค 100 ไมล์ / อัลตร้า",
        },
    },
}


def calculate_rice_plan(day_str: str, workouts: list[dict]) -> dict:
    """Calculates daily rice & oats targets based on workouts."""
    dt = datetime.strptime(day_str, "%Y-%m-%d")
    is_weekend = dt.weekday() >= 5  # 5=Saturday, 6=Sunday

    total_tss = sum(w.get("tssPlanned") or w.get("tssActual") or 0 for w in workouts)
    total_dur = sum(
        w.get("totalTimePlanned") or w.get("totalTime") or 0 for w in workouts
    )
    total_dplus = sum(
        w.get("elevationGainPlanned") or w.get("elevationGain") or 0 for w in workouts
    )

    oats_breakfast = 60

    if total_dur == 0 or total_tss == 0:
        cat_key = "rest"
        midi = 120
        snack = 0
        diner = 120
    elif total_dur <= 1.25 and total_tss < 75:
        cat_key = "light"
        if is_weekend:
            oats_breakfast = 70
            midi = 240
            snack = 0
            diner = 150
        else:
            midi = 180
            snack = 80
            diner = 220
    elif total_dur <= 2.5 or (total_tss < 160 and total_dplus < 1000):
        cat_key = "moderate"
        if is_weekend:
            oats_breakfast = 80
            midi = 350
            snack = 80
            diner = 180
        else:
            midi = 220
            snack = 120
            diner = 320
    elif total_dur <= 4.0 or (total_tss < 260 and total_dplus < 1800):
        cat_key = "high"
        if is_weekend:
            oats_breakfast = 90
            midi = 480
            snack = 100
            diner = 220
        else:
            midi = 280
            snack = 150
            diner = 450
    else:
        cat_key = "peak"
        if is_weekend:
            oats_breakfast = 100
            midi = 650
            snack = 150
            diner = 300
        else:
            midi = 350
            snack = 200
            diner = 600

    total_rice_cuit = midi + snack + diner
    total_rice_cru = int(total_rice_cuit / 3.0)

    return {
        "day": day_str,
        "cat_key": cat_key,
        "oats_breakfast": oats_breakfast,
        "midi": midi,
        "snack": snack,
        "diner": diner,
        "total_rice_cuit": total_rice_cuit,
        "total_rice_cru": total_rice_cru,
        "total_dur": round(total_dur, 2),
        "total_tss": round(total_tss, 1),
        "total_dplus": int(total_dplus),
    }


def parse_rice_note_text(raw_text: str, day_str: str) -> dict:
    """Extract numerical plan values from an existing TP note description."""
    oats_match = re.search(r"Petit-déjeuner\s*:\s*(\d+)g", raw_text)
    midi_match = re.search(r"Déjeuner.*:\s*(\d+)g", raw_text)
    snack_match = re.search(r"Collation 16h\s*:\s*(\d+)g", raw_text)
    diner_match = re.search(r"Dîner.*:\s*(\d+)g", raw_text)

    dur_match = re.search(r"Durée:\s*([\d\.]+)h", raw_text)
    tss_match = re.search(r"TSS:\s*([\d\.]+)", raw_text)
    dplus_match = re.search(r"D\+:\s*(\d+)m", raw_text)

    oats = int(oats_match.group(1)) if oats_match else 60
    midi = int(midi_match.group(1)) if midi_match else 120
    snack = int(snack_match.group(1)) if snack_match else 0
    diner = int(diner_match.group(1)) if diner_match else 120

    dur = float(dur_match.group(1)) if dur_match else 0.0
    tss = float(tss_match.group(1)) if tss_match else 0.0
    dplus = int(dplus_match.group(1)) if dplus_match else 0

    cat_key = "rest"
    if "Léger" in raw_text or "Maintenance" in raw_text or "Light" in raw_text:
        cat_key = "light"
    elif "Modérée" in raw_text or "Moderate" in raw_text or "Trail" in raw_text:
        cat_key = "moderate"
    elif "Volume" in raw_text or "Gros" in raw_text or "High" in raw_text:
        cat_key = "high"
    elif "PEAK" in raw_text or "Ultra" in raw_text:
        cat_key = "peak"

    tot_cuit = midi + snack + diner
    tot_cru = int(tot_cuit / 3.0)

    return {
        "day": day_str,
        "cat_key": cat_key,
        "oats_breakfast": oats,
        "midi": midi,
        "snack": snack,
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

    if for_sms:
        title = f"[{t['title_prefix']} {date_str}]"
    else:
        title = f"🍚 {t['title_prefix']} : {tot_cuit}g ({category_name})"

    dur_str = f"{t['duration']}: {plan['total_dur']}h"
    tss_str = f"TSS: {plan['total_tss']}"
    dplus_str = f"{t['dplus']}: {plan['total_dplus']}m"

    header = t["header"].format(date=date_str)
    cat_line = (
        f"{t['category_label']} : {category_name} ({dur_str} | {tss_str} | {dplus_str})"
    )

    lines = [
        title,
        f"{t['title_prefix']} : {tot_cuit}g ({category_name})",
        "",
        header,
        cat_line,
        "",
        t["breakdown_header"],
        f"- 🌅 {t['breakfast'].format(oats=plan['oats_breakfast'])}",
        f"- ☀️ {t['lunch'].format(midi=plan['midi'])}",
    ]

    if plan["snack"] > 0:
        lines.append(f"- 🍎 {t['snack'].format(snack=plan['snack'])}")
    else:
        lines.append(f"- 🍎 {t['snack_rest']}")

    lines.extend(
        [
            f"- 🌙 {t['dinner'].format(diner=plan['diner'])}",
            "",
            f"⚖️ {t['total'].format(total_cuit=tot_cuit, total_cru=tot_cru)}",
        ]
    )

    full_text = "\n".join(lines)

    if for_sms:
        # Inline emoji sanitizer
        replacements = {
            "🍚": "[RIZ]",
            "🎯": "[PLAN]",
            "🌅": "[Matin]",
            "☀️": "[Midi]",
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
            "️": "",
        }
        for emoji, replacement in replacements.items():
            full_text = full_text.replace(emoji, replacement)

        full_text = re.sub(r"[\U00010000-\U0010ffff]", "", full_text)

    return title, full_text
