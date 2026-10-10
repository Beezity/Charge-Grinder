"""Rabbit Hole strategy policy. Pure Python; no game input or GUI imports.

Source: MD 5F Crates Farming Guide, Rabbit Hole, updated 8 Oct 2026.
Visual automation lives in rabbit_hole_runtime; uncalibrated steps stop there.
"""
from dataclasses import dataclass

GUIDE = "https://docs.google.com/spreadsheets/d/1xt72hupklzKFN8AEvsjphApR1D2CRyYvurzAFMxA76s/htmlview#gid=486536596"
KEYWORD = "RUPTURE"


def validate_keyword(affinities):
    """The first affinity controls upstream team-icon recognition."""
    if not affinities or affinities[0].upper() != KEYWORD:
        raise ValueError("Rabbit Hole requires RUPTURE as the team's first keyword.")


class CheckpointRequired(Exception):
    """Intentional handoff, never an error that should trigger click recovery."""


@dataclass(frozen=True)
class Floor:
    number: int
    pack: str
    hard: bool
    shop: str


FLOORS = {
    1: Floor(1, "FlatbrokeGamblers", False,
        "Buy T2/T3 fusion material. Heal a non-Faust event-check ID to 45 SP; "
        "prefer a 1-3 coin skill rolling at least 16 in Wrath/Gluttony/Gloom/Pride/Envy. "
        "Do not SP-heal Faust yet."),
    2: Floor(2, "HellsChicken", False,
        "Buy T2/T3 material. Fuse Fragment of Conceit (Poise Rock); "
        "Grand Welcome may now be consumed. Keep Clear Mirror, Calm Water but "
        "do not upgrade it. Fragment of Decay is an optional early target."),
    3: Floor(3, "TobeCleaved", False,
        "Buy T2/T3 material and finish Fragment of Conceit. Do not auto-heal Faust here. "
        "Keep Clear Mirror, Calm Water unupgraded. Avoid risky encounters."),
    4: Floor(4, "HatredandDespair", False,
        "Heal Faust to 45 SP. Obtain Fragment of Conceit, Clear Mirror, Calm Water++, "
        "Fragment of Decay and Artistic Sense++. Optional: buy a Poise potency gift."),
    5: Floor(5, "Line2", True,
        "Do not auto-heal Faust here. Optional: buy a Poise potency gift. Field Faust solo."),
}

SETUP = (
    "Start a NORMAL run manually with Mao Faust, level 60+, UT3+; equip only Hollow "
    "(TS3+, preferably TS4). Select graces 1 and 3 and two Gift Searches. "
    "Start with Cigarette Holder, Grand Welcome and Sharp Needles & Threads. "
    "Field only Faust; bench IDs can rotate for rest bonus. "
    "The guide estimates about -21 Starlight per run. "
    "Resume this draft at the pack-selection or map screen."
)


def floor_plan(number):
    if type(number) is not int or number not in FLOORS:
        raise ValueError("Rabbit Hole supports floors 1 through 5 only.")
    return FLOORS[number]


def choose_pack(number, detected, refresh_available):
    """Choose the exact required pack, refresh, or hand control back."""
    target = floor_plan(number).pack
    if target in detected:
        return detected[target]
    if refresh_available:
        return None
    raise CheckpointRequired(
        f"Required pack {target} was not recognized. Use Pack Search manually; "
        "do not select a substitute pack. Resume after selecting the required pack."
    )


def node_allowed(number, name):
    floor_plan(number)
    return name in {"Normal", "Focused", "Miniboss", "Event", "Shop", "Boss", "Risky"} and not (
        number == 3 and name == "Risky"
    )


def combat(number, boss=False, faelantern=False, turn=1):
    floor_plan(number)
    if type(turn) is not int or turn < 1:
        raise ValueError("Turn must be a positive integer.")
    if faelantern and (number != 3 or not boss):
        raise ValueError("Faelantern is the floor-3 boss exception.")
    if number <= 3 and not (number == 3 and boss):
        return "OVERCLOCK Hollow Faust; field Faust solo."
    if faelantern:
        if turn == 1:
            return ("Field 7 sinners. Use their skills on turn 1 and Awakening Hollow "
                    "(Le Trou) on Faust. Retry if Faust is Charmed.")
        return ("Use Awakening Hollow (Boucher un trou) only after Faelantern emerges. "
                "Do not use the other sinners' attacks after turn 1.")
    if number == 4 and boss and turn > 2:
        return "RETRY: KoD survived turn 2."
    if turn == 1:
        return "Awakening Hollow Faust (Le Trou)."
    if turn == 2:
        if number == 5:
            return ("Awakening Hollow (Boucher un trou), hitting Rose + Signpost + Flesh. "
                    "If Roses outspeeds Faust, clash with the faster part while retaining all parts.")
        return "Awakening Hollow Faust (Boucher un trou)."
    return "Manual review required: fight exceeded the scripted two-turn sequence."


def protected_gifts(number):
    floor_plan(number)
    gifts = {"Sharp Needles & Threads", "Cigarette Holder", "Fragment of Conceit",
             "Fragment of Decay", "Clear Mirror, Calm Water", "Artistic Sense"}
    if number == 1:
        gifts.add("Grand Welcome")
    return frozenset(gifts)


def checkpoint_text(number, stage):
    plan = floor_plan(number)
    if stage == "setup":
        return SETUP
    if stage == "shop":
        return plan.shop + " Preserve: " + ", ".join(sorted(protected_gifts(number))) + "."
    if stage == "combat":
        text = combat(number) + " Complete this fight manually, then resume on the map."
        if number == 3:
            text += (" For the boss, use Awakening on turns 1/2. "
                     "Slash/Pride/Lust indicates Faelantern: " + combat(3, True, True, 1)
                     + " " + combat(3, True, True, 2))
        if number == 4:
            text += " Use Awakening on turns 1/2. Retry if KoD survives turn 2. Meatshields must not attack."
        if number == 5:
            text += " " + combat(5, True, turn=2)
        return text
    if stage == "reward":
        return "Choose gifts/fusion material manually. Avoid HP trials, or choose the lowest HP increase."
    if stage == "event":
        return "Complete the event manually, using the non-Faust ID healed to 45 SP for skill checks."
    return "Screen is not calibrated. Complete the current step manually, then resume at the map or pack selection."
