"""
Module: project_chiang_m_ai.nutrition

Daily carbohydrate calculation, intra-workout fueling (Gels & Sports Drink),
and multi-language formatting (FR, EN, TH) for Chiang Mai 160k.
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
        "breakdown_header": "RÉPARTITION NUTRITION DU JOUR :",
        "breakfast": "Petit-déjeuner : {oats}g Flocons d'Avoine",
        "intra": "Pendant l'effort : {intra}g Glucides (Boisson d'effort & Gels)",
        "intra_rest": "Pendant l'effort : 0g (Repos)",
        "lunch": "Déjeuner (Midi) : {midi}g Riz Cuit",
        "snack": "Collation 16h : 1 Banane (~25g glucides)",
        "snack_rest": "Collation 16h : Repos (0g)",
        "dinner": "Dîner (Soir) : {diner}g Riz Cuit",
        "total": (
            "TOTAL RIZ CUIT JOUR : {total_cuit}g Riz Cuit (~{total_cru}g Riz Sec)"
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
        "title_prefix": "Meal & Rice Plan",
        "header": "DAILY NUTRITION PLAN - {date}",
        "category_label": "Category",
        "duration": "Duration",
        "dplus": "D+",
        "breakdown_header": "DAILY NUTRITION BREAKDOWN:",
        "breakfast": "Breakfast: {oats}g Rolled Oats",
        "intra": "During Workout: {intra}g Carbs (Sports Drink & Gels)",
        "intra_rest": "During Workout: 0g (Rest)",
        "lunch": "Lunch: {midi}g Cooked Rice",
        "snack": "Afternoon Snack (4PM): 1 Banana (~25g carbs)",
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
            "moderate": "⛰️ Moderate Session / 2h30 Figuerolles",
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
        "breakdown_header": "ตารางโภชนาการประจำวัน:",
        "breakfast": "มื้อเช้า: ข้าวโอ๊ต {oats}g",
        "intra": "ระหว่างออกกำลังกาย: คาร์บ {intra}g (เครื่องดื่มเกลือแร่ & เจล)",
        "intra_rest": "ระหว่างออกกำลังกาย: 0g (พักผ่อน)",
        "lunch": "มื้อเที่ยง: ข้าวสวย {midi}g",
        "snack": "อาหารว่าง (16:00 น.): กล้วย 1 ลูก (~25g คาร์บ)",
        "snack_rest": "อาหารว่าง (16:00 น.): พักผ่อน (0g)",
        "dinner": "มื้อเย็น: ข้าวสวย {diner}g",
        "total": "รวมข้าวสวยประจำวัน: {total_cuit}g (~ข้าวสาร {total_cru}g)",
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


def calculate_rice_plan(day_str: str, workouts: list[dict]) -> dict:
    """Calculates daily rice, oats, intra-workout carbs, and snack targets."""
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
        # --- REST DAY ---
        cat_key = "rest"
        intra_carbs = 0
        has_snack = False
        midi = 120
        diner = 120
    elif total_dur <= 1.25 and total_tss < 75:
        # --- LIGHT SESSION ---
        cat_key = "light"
        intra_carbs = 30  # 1 bidon boisson / 1 gel
        has_snack = True
        if is_weekend:
            oats_breakfast = 70
            midi = 180
            diner = 150
        else:
            midi = 150
            diner = 180
    elif total_dur <= 2.6 or (total_tss < 160 and total_dplus < 1000):
        # --- MODERATE SESSION (e.g. 2h30 Figuerolles) ---
        cat_key = "moderate"
        intra_carbs = 120  # ~50g/h: 2 bidons + 2 gels
        has_snack = True
        if is_weekend:
            oats_breakfast = 80
            midi = 220
            diner = 220
        else:
            midi = 200
            diner = 250
    elif total_dur <= 4.0 or (total_tss < 260 and total_dplus < 1800):
        # --- HIGH VOLUME DAY ---
        cat_key = "high"
        intra_carbs = 200  # ~50-60g/h: boisson + gels/compotes
        has_snack = True
        if is_weekend:
            oats_breakfast = 80
            midi = 280
            diner = 270
        else:
            midi = 250
            diner = 300
    else:
        # --- PEAK / ULTRA DAY (5h+) ---
        cat_key = "peak"
        intra_carbs = 300  # ~60g/h: boisson + gels + ravito
        has_snack = True
        if is_weekend:
            oats_breakfast = 90
            midi = 320
            diner = 330
        else:
            midi = 300
            diner = 350

    total_rice_cuit = midi + diner
    total_rice_cru = int(total_rice_cuit / 3.0)

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
    """Extract numerical plan values from an existing TP note description."""
    oats_match = re.search(r"Petit-déjeuner\s*:\s*(\d+)g", raw_text)
    intra_match = re.search(r"Pendant l'effort\s*:\s*(\d+)g", raw_text)
    midi_match = re.search(r"Déjeuner.*:\s*(\d+)g", raw_text)
    diner_match = re.search(r"Dîner.*:\s*(\d+)g", raw_text)

    dur_match = re.search(r"Durée:\s*([\d\.]+)h", raw_text)
    tss_match = re.search(r"TSS:\s*([\d\.]+)", raw_text)
    dplus_match = re.search(r"D\+:\s*(\d+)m", raw_text)

    oats = int(oats_match.group(1)) if oats_match else 60
    intra = int(intra_match.group(1)) if intra_match else 0
    midi = int(midi_match.group(1)) if midi_match else 150
    diner = int(diner_match.group(1)) if diner_match else 180

    dur = float(dur_match.group(1)) if dur_match else 0.0
    tss = float(tss_match.group(1)) if tss_match else 0.0
    dplus = int(dplus_match.group(1)) if dplus_match else 0

    cat_key = "rest"
    if "Léger" in raw_text or "Maintenance" in raw_text or "Light" in raw_text:
        cat_key = "light"
    elif "Modérée" in raw_text or "Moderate" in raw_text or "Figuerolles" in raw_text:
        cat_key = "moderate"
    elif "Volume" in raw_text or "Gros" in raw_text or "High" in raw_text:
        cat_key = "high"
    elif "PEAK" in raw_text or "Ultra" in raw_text:
        cat_key = "peak"

    tot_cuit = midi + diner
    tot_cru = int(tot_cuit / 3.0)

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
        # Inline emoji sanitizer for Free Mobile SMS API
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
            "️": "",
        }
        for emoji, replacement in replacements.items():
            full_text = full_text.replace(emoji, replacement)

        full_text = re.sub(r"[\U00010000-\U0010ffff]", "", full_text)

    return title, full_text
