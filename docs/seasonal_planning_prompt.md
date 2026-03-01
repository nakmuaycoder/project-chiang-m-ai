# 📅 Seasonal Planning & Strategy Prompt

This document contains the **"Director Sportif"** prompt.

**Usage:** Copy and paste the prompt below into a "Reasoning Model" (e.g., ChatGPT o1/4o, Claude 3.5 Sonnet, or Gemini Advanced). Attach your historical data files (CSV of past activities, injury history, future race dates) to the chat.

The goal is to generate the `season_plan.json` file that drives the daily coaching logic.

---

## 📋 The Prompt

**Subject:** Annual Season Planning & Performance Audit

**Context:**
Act as an elite Olympic Performance Director and Head Coach. I am an endurance athlete (Cycling/Running) preparing for the upcoming season.

**I am providing you with the following data:**
1.  **Activity History:** My past 6-12 months of training loads and performances.
2.  **Physiological Metrics:** My Power Curve, HR Zones, HRV baseline, and Resting HR trends.
3.  **Injury History:** A list of past injuries and dates.
4.  **Goals:** My main "A-Race" objective and intermediate goals.

**YOUR MISSION:**

**Phase 1: The Audit**
Analyze the provided data. Identify my limiting factors (e.g., aerobic ceiling, muscular endurance, durability). Be critical: if my goals are unrealistic given my history, tell me immediately.

**Phase 2: Periodization**
Design a complete Macro-Cycle leading up to my A-Race. Break the season down into distinct **Phases** (e.g., General Base, Specific Base, Build, Peak, Taper, Recovery).
For *each* phase, define:
* **Dates:** Precise start and end dates.
* **Physiological Focus:** What system are we building? (e.g., VO2Max, Fat Oxidation, Torque).
* **Weekly Volume:** Target hours per discipline (Bike, Run, Strength).
* **Elevation:** Target vertical gain (D+) per week.
* **Intensity Distribution:** How should the zones be distributed? (e.g., Polarized 80/20, Pyramidal).

**Phase 3: The Iteration**
Do not generate the final file yet. Present the plan to me in text format first. Let's discuss and refine it until I validate the strategy.

**Phase 4: The Handover (JSON)**
Once we agree on the plan, you must output the result as a strictly formatted **JSON object**. This JSON will be fed into an automated daily coaching agent.

**JSON SCHEMA REQUIREMENTS:**
The output must match this exact structure:

```json
{
  "athlete_name": "String",
  "season_goal": "String",
  "phases": [
    {
      "name": "String (e.g., General Base 1)",
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "focus": "String (Short description of the physiological goal)",
      "weekly_targets": {
        "bike_hours": Number,
        "run_hours": Number,
        "swim_hours": Number,
        "strength_sessions": Number,
        "elevation_gain_meters": Number
      },
      "intensity_guidelines": "String (Description of how to distribute intensity)"
    }
  ]
}

```

## 🛠 Workflow Tips

Data Ingestion: If your data is in CSV format (from Intervals.icu or Garmin), upload the files directly to the chat.

Challenge the LLM: If the AI suggests 15 hours of training but you only have 10 hours available, tell it. Ask it to re-optimize the quality of sessions to fit your constraints.

Sanity Check: Ensure the dates are continuous (Phase 2 starts the day after Phase 1 ends).

Save: Copy the final JSON code block and save it to data/season_plan.json.
