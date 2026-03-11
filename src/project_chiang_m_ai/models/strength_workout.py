"""
Strength Training Workout Model

Simple format for Intervals.icu strength workouts
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class StrengthExercise(BaseModel):
    """A single strength exercise"""

    name: str
    sets: int
    reps: str  # Can be "10" or "8-12" or "AMRAP"
    weight: Optional[str] = None  # e.g., "60kg", "bodyweight", "80% 1RM"
    rest: Optional[str] = None  # e.g., "90s", "2m"
    notes: Optional[str] = None


class StrengthBlock(BaseModel):
    """A block of exercises (e.g., superset, circuit)"""

    name: Optional[str] = None  # e.g., "Main Set", "Warmup", "Superset A"
    exercises: List[StrengthExercise]
    repetitions: int = 1  # For circuits


class StrengthWorkout(BaseModel):
    """Complete strength training workout"""

    name: str
    start_date_local: Optional[str] = None
    description: str
    type: Literal["WeightTraining", "Strength"] = (
        "WeightTraining"  # Discriminator field
    )
    blocks: List[StrengthBlock]
    estimated_duration: Optional[int] = None  # in seconds
    color: Optional[str] = None
    category: str = "WORKOUT"
    original_workout: Optional[Dict] = Field(
        default=None,
        description="The original macro-plan workout before LLM adaptation",
    )

    def to_intervals_description(self) -> str:
        """
        Convert to plain text format for Intervals.icu.

        Simple readable format without workout step syntax.
        """
        lines = []

        for block in self.blocks:
            # Block header
            if block.name:
                lines.append(f"━━━ {block.name.upper()} ━━━")
                lines.append("")

            # Circuit/repetition indicator
            if block.repetitions > 1:
                lines.append(f"🔄 {block.repetitions} Rounds")
                lines.append("")

            # Exercises
            for exercise in block.exercises:
                # Exercise name
                lines.append(f"• {exercise.name}")

                # Details line
                details = []
                details.append(f"{exercise.sets} sets × {exercise.reps} reps")

                if exercise.weight:
                    details.append(f"Weight: {exercise.weight}")

                if exercise.rest:
                    details.append(f"Rest: {exercise.rest}")

                lines.append(f"  {' | '.join(details)}")

                # Notes
                if exercise.notes:
                    lines.append(f"  💡 {exercise.notes}")

                lines.append("")  # Blank line between exercises

            # Extra blank line between blocks
            lines.append("")

        return "\n".join(lines).strip()
