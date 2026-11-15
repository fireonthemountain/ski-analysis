"""Assessment schema + the catalog of things an assessor can rate.

Each catalog item maps one observation an instructor would make to ONE
measured value on a number line that is cut into ordered categories by
explicit thresholds (``bounds``). The assessor picks a category; the
validation engine measures the value and compares.

The thresholds are engineering defaults chosen for this tool - PSIA publishes
the fundamentals qualitatively, not as degree cut-offs - so they are kept here
in one place, shown in the UI next to every verdict, and meant to be tuned.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

PSIA = {
    1: "Control the relationship of the centre of mass to the base of support to direct pressure along the length of the skis",
    2: "Control pressure from ski to ski and direct pressure toward the outside ski",
    3: "Control edge angles through a combination of inclination and angulation",
    4: "Control the skis' rotation with leg rotation, separate from the upper body",
    5: "Regulate the magnitude of pressure created through ski/snow interaction",
}


@dataclass(frozen=True)
class Option:
    id: str
    label: str
    hint: str = ""


@dataclass(frozen=True)
class Item:
    id: str
    label: str
    group: str
    fundamental: str                 # which PSIA fundamental (or outcome) this speaks to
    question: str                    # what the assessor is rating
    measure: str                     # what the engine measures, in plain words
    unit: str
    options: tuple[Option, ...]      # ordered low -> high along the measured value
    bounds: tuple[float, ...]        # len(options) - 1 thresholds, increasing
    base_uncertainty: float          # measurement uncertainty floor, in ``unit``
    needs_video: bool = False
    needs_view: Optional[str] = None  # 'frontal' | 'side' | None (any view)
    needs_3d: bool = False
    conf_cap: float = 1.0            # ceiling on confidence for inherently weak measurements
    experimental: bool = False
    extra_options: tuple[Option, ...] = ()   # categories that are not on the number line
    limitations: tuple[str, ...] = ()

    def all_options(self) -> tuple[Option, ...]:
        return self.options + self.extra_options

    def category_for(self, value: float) -> Option:
        i = 0
        for b in self.bounds:
            if value >= b:
                i += 1
        return self.options[i]

    def range_for(self, option_id: str) -> tuple[float, float]:
        ids = [o.id for o in self.options]
        i = ids.index(option_id)
        lo = self.bounds[i - 1] if i > 0 else float("-inf")
        hi = self.bounds[i] if i < len(self.bounds) else float("inf")
        return lo, hi


_ROLL = "Angles are measured against image vertical: a tilted camera or a side-hill biases them by the same amount."
_Z = "Uses monocular 3D (depth is estimated, not measured), so confidence is capped."

CATALOG: tuple[Item, ...] = (
    Item(
        id="stance_width", label="Stance width", group="Stance & balance",
        fundamental=f"PSIA #2 - {PSIA[2]}",
        question="How wide is the stance?",
        measure="Ankle spacing measured across the body (perpendicular to the leg axis), divided by hip-joint width. Median over all confident frames.",
        unit="x hip width",
        options=(Option("narrow", "Narrow", "feet together, inside hip width"),
                 Option("functional", "Hip width / functional", "feet about under the hips"),
                 Option("wide", "Wide", "clearly outside hip width")),
        bounds=(0.75, 1.5), base_uncertainty=0.15,
        limitations=("Best from a front or back view; from the side it falls back to estimated 3D.",),
    ),
    Item(
        id="fore_aft", label="Fore-aft balance", group="Stance & balance",
        fundamental=f"PSIA #1 - {PSIA[1]}",
        question="Where is the skier balanced along the length of the skis?",
        measure="Angle from the ankles to the estimated centre of mass, relative to the slope normal (taken from the boot-sole line when the feet are visible, else image vertical). Median over confident frames.",
        unit="deg",
        options=(Option("aft", "Aft / back seat", "hips behind the feet"),
                 Option("centered", "Centered", "centre of mass over the feet"),
                 Option("forward", "Forward", "pressing well ahead of the feet")),
        bounds=(-4.0, 12.0), base_uncertainty=5.0, needs_view="side",
        limitations=("Needs a side view.", "The centred band is only ~16 deg wide and pose noise is several degrees, so expect 'inconclusive' unless the stance is clearly aft or forward."),
    ),
    Item(
        id="stance_height", label="Stance height (knee flexion)", group="Stance & balance",
        fundamental=f"PSIA #5 - {PSIA[5]}",
        question="How flexed is the skier on average?",
        measure="Included knee angle (hip-knee-ankle, 180 = straight leg), mean of both legs, median over confident frames.",
        unit="deg",
        options=(Option("low", "Low / deep", "very flexed, sitting low"),
                 Option("athletic", "Athletic", "flexed and ready"),
                 Option("tall", "Tall / stiff", "nearly straight legs")),
        bounds=(120.0, 155.0), base_uncertainty=6.0,
    ),
    Item(
        id="hip_flexion", label="Upper-body posture (hip flexion)", group="Stance & balance",
        fundamental=f"PSIA #1 - {PSIA[1]}",
        question="How is the upper body carried over the legs?",
        measure="Included hip angle (shoulder-hip-knee, 180 = standing straight), mean of both sides, median over confident frames.",
        unit="deg",
        options=(Option("folded", "Folded at the waist", "chest dropped toward the thighs"),
                 Option("athletic", "Athletic forward lean", ""),
                 Option("upright", "Upright", "torso nearly in line with the thighs")),
        bounds=(105.0, 150.0), base_uncertainty=7.0,
    ),
    Item(
        id="vertical_movement", label="Flexion / extension range", group="Pressure",
        fundamental=f"PSIA #5 - {PSIA[5]}",
        question="How much does the skier flex and extend through the run?",
        measure="Range of the knee angle over the clip (90th minus 10th percentile).",
        unit="deg",
        options=(Option("static", "Static", "one position all the way down"),
                 Option("moderate", "Moderate", ""),
                 Option("active", "Active", "clear flex and extend every turn")),
        bounds=(15.0, 30.0), base_uncertainty=5.0, needs_video=True,
    ),
    Item(
        id="edge_angle", label="Edge angle (peak)", group="Edging",
        fundamental=f"PSIA #3 - {PSIA[3]}",
        question="How much edge angle is developed at the strongest point of the turn?",
        measure="Lateral tilt of the outside-leg shin from vertical (a proxy for ski edge angle). Video: peak in each turn, median across turns. Stills: the largest value among the frames given.",
        unit="deg",
        options=(Option("low", "Low", "skis nearly flat"),
                 Option("moderate", "Moderate", ""),
                 Option("high", "High", "big angles, hip toward the snow")),
        bounds=(20.0, 40.0), base_uncertainty=4.0, needs_view="frontal",
        limitations=("Shin tilt is a proxy: the skis themselves are not tracked.", _ROLL),
    ),
    Item(
        id="angulation", label="Angulation", group="Edging",
        fundamental=f"PSIA #3 - {PSIA[3]}",
        question="When the legs are inclined, does the upper body stay more upright (angulate) or lean in with them (bank)?",
        measure="Leg-axis lean minus torso lean, on frames where the legs are inclined at least 12 deg. Positive = torso more upright than the legs.",
        unit="deg",
        options=(Option("banked", "Banked / leaning in", "body tips in as one piece"),
                 Option("moderate", "Moderate angulation", ""),
                 Option("strong", "Strong angulation", "level shoulders over an inclined lower body")),
        bounds=(5.0, 18.0), base_uncertainty=4.0, needs_view="frontal",
        limitations=(_ROLL,),
    ),
    Item(
        id="separation", label="Upper / lower body separation", group="Rotary",
        fundamental=f"PSIA #4 - {PSIA[4]}",
        question="How much do the legs turn under a quiet upper body?",
        measure="Yaw of the shoulder line relative to the direction the feet point (or the pelvis when the feet are not visible), from 3D landmarks. Video: 90th percentile of the absolute value. Stills: largest value.",
        unit="deg",
        options=(Option("unit", "Little / none", "body turns as one unit"),
                 Option("moderate", "Moderate", ""),
                 Option("strong", "Strong", "legs clearly turn under a stable upper body")),
        bounds=(10.0, 35.0), base_uncertainty=8.0, needs_3d=True, conf_cap=0.6,
        limitations=(_Z,),
    ),
    Item(
        id="counter", label="Rotation / counter", group="Rotary",
        fundamental=f"PSIA #4 - {PSIA[4]}",
        question="Through the turn, does the upper body rotate into the turn, stay square, or face the outside (counter)?",
        measure="Upper/lower separation signed by turn direction on frames with at least 8 deg of lean. Positive = upper body faces the outside of the turn (countered); negative = rotated into the turn.",
        unit="deg",
        options=(Option("rotated", "Rotated into the turn", "shoulders lead / over-rotate"),
                 Option("square", "Square", "upper body follows the skis"),
                 Option("countered", "Countered", "upper body faces the outside of the turn")),
        bounds=(-10.0, 10.0), base_uncertainty=8.0, needs_view="frontal", needs_3d=True, conf_cap=0.6,
        limitations=(_Z,),
    ),
    Item(
        id="turn_shape", label="Turn shape", group="Turn outcome",
        fundamental="Outcome - duration, intensity, rate and timing of edging movements",
        question="Are turns round and progressive, or abrupt (Z-shaped, rushed start)?",
        measure="How far into each turn the lean reaches 70% of its peak, as a fraction of the turn's duration (a smooth arc is ~0.25, a snapped edge set is under 0.1). Median across complete turns.",
        unit="fraction of turn",
        options=(Option("abrupt", "Abrupt / Z-shaped", "edges are thrown on at the top"),
                 Option("round", "Round / progressive", "edge builds through the turn")),
        bounds=(0.15,), base_uncertainty=0.04, needs_video=True, needs_view="frontal", conf_cap=0.7, experimental=True,
        limitations=("Inferred from how lean builds over time, not from the track in the snow.",),
    ),
    Item(
        id="turn_symmetry", label="Left / right symmetry", group="Turn outcome",
        fundamental="Outcome - consistency of movements in both directions",
        question="Are left and right turns equally strong?",
        measure="Peak lean of right turns versus left turns (skier's own left/right): (right - left) / mean, in percent.",
        unit="%",
        options=(Option("left_stronger", "Left turns stronger", ""),
                 Option("symmetric", "Symmetric", ""),
                 Option("right_stronger", "Right turns stronger", "")),
        bounds=(-20.0, 20.0), base_uncertainty=8.0, needs_video=True, needs_view="frontal",
        limitations=(_ROLL + " A side-hill therefore looks like asymmetry.",),
    ),
    Item(
        id="pole_plant", label="Pole plant timing", group="Timing",
        fundamental="Timing and coordination (supports PSIA #1 and #4)",
        question="When does the pole touch relative to the edge change?",
        measure="A downward reach of the new inside hand near each edge change, timed against the edge change as a fraction of turn duration (negative = before).",
        unit="fraction of turn",
        options=(Option("early", "Early", "well before the edge change"),
                 Option("on_time", "On time", "at the edge change"),
                 Option("late", "Late", "after the new turn has started")),
        extra_options=(Option("none", "No visible pole plant", ""),),
        bounds=(-0.15, 0.12), base_uncertainty=0.06, needs_video=True, needs_view="frontal", conf_cap=0.55, experimental=True,
        limitations=("Poles are not tracked - this looks for the hand movement of a plant, so a wrist-only touch is invisible to it.",),
    ),
)

CATALOG_BY_ID = {i.id: i for i in CATALOG}


def catalog_json() -> list[dict]:
    """Catalog for the frontend form (and docs)."""
    out = []
    for it in CATALOG:
        opts = []
        for o in it.options:
            lo, hi = it.range_for(o.id)
            opts.append({"id": o.id, "label": o.label, "hint": o.hint,
                         "min": None if lo == float("-inf") else lo, "max": None if hi == float("inf") else hi})
        for o in it.extra_options:
            opts.append({"id": o.id, "label": o.label, "hint": o.hint, "min": None, "max": None})
        out.append({
            "id": it.id, "label": it.label, "group": it.group, "fundamental": it.fundamental,
            "question": it.question, "measure": it.measure, "unit": it.unit, "options": opts,
            "bounds": list(it.bounds), "base_uncertainty": it.base_uncertainty,
            "needs_video": it.needs_video, "needs_view": it.needs_view, "needs_3d": it.needs_3d,
            "conf_cap": it.conf_cap, "experimental": it.experimental, "limitations": list(it.limitations),
        })
    return out


# ------------------------------------------------------------------ schema
class AssessedItem(BaseModel):
    item_id: str
    rating: str
    notes: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _check(self):
        item = CATALOG_BY_ID.get(self.item_id)
        if item is None:
            raise ValueError(f"unknown assessment item '{self.item_id}'")
        valid = [o.id for o in item.all_options()]
        if self.rating not in valid:
            raise ValueError(f"'{self.rating}' is not a rating for {self.item_id}; choose one of {valid}")
        return self


class Assessment(BaseModel):
    """What the assessor believes about the run - the thing being validated."""

    run_label: str = Field(default="Untitled run", max_length=200)
    skier: Optional[str] = Field(default=None, max_length=200)
    assessed_by: Optional[str] = Field(default=None, max_length=200)
    terrain: Optional[str] = Field(default=None, max_length=200)
    camera_view: Literal["auto", "frontal", "side", "oblique"] = "auto"
    framework: str = "PSIA Alpine fundamentals"
    general_notes: Optional[str] = Field(default=None, max_length=5000)
    items: list[AssessedItem] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self):
        ids = [i.item_id for i in self.items]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise ValueError(f"items rated more than once: {sorted(dup)}")
        return self
