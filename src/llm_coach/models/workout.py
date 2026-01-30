import re
from enum import Enum
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, PrivateAttr, field_validator, model_validator


class ZoneDefinition(BaseModel):
    """
    Basic structure to define the lower and upper bounds of a training zone.
    """

    name: str
    start: int
    end: int


class SportZone(Enum):
    """
    Base Enum class to handle zone lookups.
    """

    @classmethod
    def get_zone(cls, value: str) -> Optional[ZoneDefinition]:
        """
        Retrieves the ZoneDefinition object associated with the Enum member name.
        Example: get_zone("Z2") returns the ZoneDefinition for Zone 2.
        """
        try:
            # Access the Enum member by name (e.g., "Z1") and return its value
            member = cls[value]
            return member.value
        except KeyError:
            return None


class CyclingPowerZone(SportZone):
    """
    Coggan Power Zones (% FTP).
    Standard reference for cycling based on functional threshold power.
    """

    Z1 = ZoneDefinition(name="Active Recovery", start=0, end=55)
    Z2 = ZoneDefinition(name="Endurance", start=56, end=75)
    Z3 = ZoneDefinition(name="Tempo", start=76, end=90)
    Z4 = ZoneDefinition(name="Threshold", start=91, end=105)
    Z5 = ZoneDefinition(name="VO2 Max", start=106, end=120)
    Z6 = ZoneDefinition(name="Anaerobic", start=121, end=150)
    Z7 = ZoneDefinition(name="Neuromuscular", start=151, end=1000)


class RunningHRZone(SportZone):
    """
    Running Heart Rate Zones (% Max HR).
    Standard reference for running based on maximum heart rate.
    """

    Z1 = ZoneDefinition(name="Recovery", start=0, end=84)
    Z2 = ZoneDefinition(name="Aerobic", start=85, end=89)
    Z3 = ZoneDefinition(name="Tempo", start=90, end=94)
    Z4 = ZoneDefinition(name="Sub Threshold", start=95, end=99)
    Z5 = ZoneDefinition(name="Super Threshold", start=100, end=102)
    Z6 = ZoneDefinition(name="Aerobic Capacity", start=103, end=105)
    Z7 = ZoneDefinition(name="Anaerobic", start=106, end=1000)


class WorkoutType(str, Enum):
    """Supported sport types for the workout."""

    RUN = "Run"
    BIKE = "Bike"
    SWIM = "Swim"
    OTHER = "Other"


class Zone(BaseModel):
    """
    Intensity Parser.
    Converts raw AI output (e.g., 'Z2', 'Z2 HR', '75%', '70-80%')
    into a normalized percentage range.
    """

    z: str = Field(..., description="Raw intensity string from LLM")

    # Private attributes for internal storage (not exposed in JSON output)
    _start: Optional[int] = PrivateAttr(default=None)
    _end: Optional[int] = PrivateAttr(default=None)
    _unit: Literal["HR", ""] = PrivateAttr(default="")

    @model_validator(mode="after")
    def parse_content(self):
        """
        Parses the raw string `z` to extract unit, start, and end values.
        """
        # Clean up input: uppercase and remove extra spaces
        raw = self.z.strip().upper()

        # 1. Unit Detection (Heart Rate)
        if "HR" in raw:
            self._unit = "LTHR"  # Use "LTHR" to test Intervals.icu compatibility
            # Remove "HR" to simplify numeric parsing later
            raw = raw.replace("HR", "").strip()
        else:
            self._unit = ""

        # 2. Zone Lookup Case (e.g., "Z2" -> Lookup in Enum)
        if raw.startswith("Z"):
            match = re.match(r"(Z\d+)", raw)
            if match:
                zone_key = match.group(1)

                # Select the correct reference table based on the unit
                if self._unit == "LTHR":
                    definition = RunningHRZone.get_zone(zone_key)
                else:
                    definition = CyclingPowerZone.get_zone(zone_key)

                # Apply the zone bounds found
                if definition:
                    self._start = definition.start
                    self._end = definition.end
                return self

        # 3. Numeric Values Case (Percentage is implicit)
        # Remove '%' signs to extract raw numbers
        raw_nums = raw.replace("%", "").strip()
        numbers = [int(n) for n in re.findall(r"\d+", raw_nums)]

        if len(numbers) >= 2:
            # Explicit Range found (e.g., "70-80")
            self._start = min(numbers)
            self._end = max(numbers)
        elif len(numbers) == 1:
            # Single Value found -> Create an artificial range of +/- 2%
            val = numbers[0]
            self._start = val - 2
            self._end = val + 2

        return self

    def to_value(self):
        """
        Formats the zone as a string range for Intervals.icu API.
        Format: 'MIN% UNIT - MAX% UNIT'
        """
        unit_str = f" {self._unit}" if self._unit else ""
        if self._start is not None and self._end is not None:
            return f"{self._start}%{unit_str} - {self._end}%{unit_str}"
        # Fallback: return raw string if parsing failed
        return self.z


class Step(BaseModel):
    """
    Represents a single atomic interval in the workout.
    """

    duration: int
    zone: Zone
    cadence: str | None = None
    description: str | None = None

    @field_validator("duration", mode="before")
    @classmethod
    def parse_duration(cls, v: Union[str, int]) -> int:
        if isinstance(v, int):
            return v

        # Simple parsing logic or reuse existing one
        v_clean = v.strip().lower()
        if v_clean.isdigit():
            return int(v_clean)

        # Basic parser for "1h 30m 10s" format
        pattern = re.compile(
            r"(?:(?P<h>\d+)\s*h)?\s*(?:(?P<m>\d+)\s*m)?\s*(?:(?P<s>\d+)\s*s)?"
        )
        match = pattern.match(v_clean)
        if not match:
            # Fallback lazy match
            pattern_lazy = re.compile(r"^(?P<h>\d+)\s*h\s*(?P<m>\d+)$")
            match = pattern_lazy.match(v_clean)

        if match:
            parts = match.groupdict()
            h = int(parts.get("h") or 0)
            m = int(parts.get("m") or 0)
            s = int(parts.get("s") or 0)
            total = (h * 3600) + (m * 60) + s
            if total > 0:
                return total

        raise ValueError(f"Invalid duration format: '{v}'")


class Steps(BaseModel):
    """
    A block of steps that can be repeated.
    Example: 10x (30s On, 30s Off)
    """

    steps: List[Step]
    repetitions: int = 1

    @property
    def duration(self) -> int:
        """
        Total duration of this block (sequence * repetitions).
        """
        return sum(s.duration for s in self.steps) * self.repetitions


class Workout(BaseModel):
    """
    The main object representing the structured workout.
    """

    name: str
    start_date_local: str  # ISO Format YYYY-MM-DDTHH:MM:SS
    category: str = "WORKOUT"
    description: str
    type: Literal["Run", "Ride", "Swim", "Other"]
    color: str | None = None
    steps: List[Steps]

    @property
    def moving_time(self):
        """
        Automatically calculates the total moving time if not provided.
        Sums up the duration of all blocks of steps.
        """
        return sum(block.duration for block in self.steps)
