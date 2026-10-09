"""The built-in risk matrix and the rules every matrix must satisfy."""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError

HEX_COLOUR = re.compile(r"^#[0-9a-fA-F]{6}$")


def validate_matrix(probability, impact, levels, grid) -> None:
    problems = {}

    def named(items, name, low, high):
        ok = (
            isinstance(items, list)
            and low <= len(items) <= high
            and all(
                isinstance(i, dict) and isinstance(i.get("name"), str) and i["name"].strip()
                for i in items
            )
        )
        if not ok:
            problems[name] = f"Give between {low} and {high} entries, each with a name."
        return ok

    ok_p = named(probability, "probability", 2, 9)
    ok_i = named(impact, "impact", 2, 9)
    ok_l = named(levels, "levels", 2, 8)
    if ok_l and not all(HEX_COLOUR.match(str(lv.get("colour", ""))) for lv in levels):
        problems["levels"] = "Each level needs a colour such as #b3261e."
    if ok_p and ok_i and ok_l:
        shape_ok = (
            isinstance(grid, list)
            and len(grid) == len(probability)
            and all(isinstance(row, list) and len(row) == len(impact) for row in grid)
        )
        if not shape_ok:
            problems["grid"] = "The grid needs one row per probability and one column per impact."
        elif not all(
            isinstance(c, int) and not isinstance(c, bool) and 0 <= c < len(levels)
            for row in grid
            for c in row
        ):
            problems["grid"] = "Every cell must be the number of one of the levels."
    elif "grid" not in problems:
        problems["grid"] = "The grid cannot be checked until the scales and levels are valid."
    if problems:
        raise ValidationError(problems)


def default_matrix() -> dict:
    probability = [
        {"name": "Very unlikely", "description": "Not expected within the planning horizon."},
        {"name": "Unlikely", "description": "Could happen, but not expected."},
        {"name": "Possible", "description": "Might happen within the planning horizon."},
        {"name": "Likely", "description": "Expected to happen at least once."},
        {"name": "Almost certain", "description": "Expected to happen repeatedly."},
    ]
    impact = [
        {"name": "Negligible", "description": "Absorbed in normal operations."},
        {"name": "Minor", "description": "Small, short-lived effect."},
        {"name": "Moderate", "description": "Noticeable effect that needs management attention."},
        {"name": "Major", "description": "Serious effect on objectives."},
        {"name": "Severe", "description": "Threatens the organisation."},
    ]
    levels = [
        {"name": "Very low", "colour": "#2e7d5b"},
        {"name": "Low", "colour": "#7a9a2e"},
        {"name": "Medium", "colour": "#c99a12"},
        {"name": "High", "colour": "#d0621a"},
        {"name": "Critical", "colour": "#b3261e"},
    ]

    def level_of(score: int) -> int:
        return (
            0 if score <= 2 else 1 if score <= 5 else 2 if score <= 10 else 3 if score <= 16 else 4
        )

    grid = [[level_of((p + 1) * (i + 1)) for i in range(5)] for p in range(5)]
    return {"probability": probability, "impact": impact, "levels": levels, "grid": grid}


def sync_builtin_matrix(**kwargs):
    from .models import RiskMatrix

    RiskMatrix.objects.update_or_create(
        name="Default 5x5",
        defaults={
            "description": "Five likelihood steps by five impact steps, five risk levels.",
            "builtin": True,
            **default_matrix(),
        },
    )
