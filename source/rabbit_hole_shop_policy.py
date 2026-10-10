"""Deterministic, side-effect-free Rabbit Hole shop strategy.

Actions describe intent only: the desktop adapter must verify every item,
price, ingredient and resulting screen before clicking confirmation. An absent
required gift is never a reason to forfeit or abort the run.
"""
from dataclasses import dataclass, field
from typing import Mapping

PROTECTED = frozenset({
    "Clear Mirror, Calm Water", "Fragment of Decay", "Fragment of Conceit",
    "Artistic Sense", "Sharp Needles & Threads",
})
REQUIRED_BY_FLOOR = {
    1: frozenset(),
    2: frozenset({"Fragment of Conceit"}),
    3: frozenset({"Fragment of Conceit"}),
    4: frozenset({"Fragment of Conceit", "Fragment of Decay",
                  "Clear Mirror, Calm Water", "Artistic Sense"}),
    5: frozenset({"Fragment of Conceit", "Fragment of Decay",
                  "Clear Mirror, Calm Water", "Artistic Sense"}),
}
UPGRADE_GOALS = {"Clear Mirror, Calm Water": 2, "Artistic Sense": 2}
TIER4_UPGRADE_COST = {0: 100, 1: 200, 2: 0}
SP_HEAL_COST = 100


@dataclass(frozen=True)
class Offer:
    name: str
    tier: int
    price: int
    verified: bool = False


@dataclass(frozen=True)
class Sale:
    name: str
    price: int
    verified: bool = False
    tier: int = 0


@dataclass(frozen=True)
class Fusion:
    result: str
    ingredients: tuple[str, ...]
    cost: int = 0
    verified: bool = False
    # Keyword fusion forecasts a tier/keyword, not an exact resulting gift.
    random_result: bool = False


@dataclass(frozen=True)
class ShopState:
    currency: int
    owned: Mapping[str, int] = field(default_factory=dict)
    sp: Mapping[str, int] = field(default_factory=dict)
    offers: tuple[Offer, ...] = ()
    sales: tuple[Sale, ...] = ()
    fusions: tuple[Fusion, ...] = ()
    event_check_id: str | None = None


@dataclass(frozen=True)
class Action:
    kind: str
    name: str = ""
    cost: int = 0
    ingredients: tuple[str, ...] = ()
    random_result: bool = False


def remaining_upgrade_cost(level: int) -> int:
    """100 + 200 = 300 for an unupgraded tier-IV gift."""
    if level not in TIER4_UPGRADE_COST:
        raise ValueError("Tier IV enhancement must be 0, 1, or 2")
    return sum(TIER4_UPGRADE_COST[i] for i in range(level, 2))


def floor4_reserve(state: ShopState) -> int:
    """Full unfunded floor-4 cost, not an unconditional spending order."""
    cost = sum(remaining_upgrade_cost(state.owned.get(name, 0))
               for name in UPGRADE_GOALS)
    if state.sp.get("Faust", -1) < 45:
        sp = state.sp.get("Faust", 0)
        cost += SP_HEAL_COST * (2 if sp < 0 else 1)
    return cost


def allowed_fusion(recipe: Fusion, state: ShopState) -> bool:
    """No protected gift may be consumed, even to create another target gift."""
    if not recipe.verified or recipe.cost < 0 or recipe.result not in REQUIRED_BY_FLOOR[4]:
        return False
    if (not recipe.ingredients or len(set(recipe.ingredients)) != len(recipe.ingredients)
            or any(g in PROTECTED for g in recipe.ingredients)):
        return False
    return all(g in state.owned for g in recipe.ingredients)


def choose_sale(sales: tuple[Sale, ...], floor: int,
                *, needed: int, currency: int, reserved=frozenset()) -> Sale | None:
    """Sell a verified, unprotected gift only to fund an actual pending action."""
    if needed <= currency or not 1 <= floor <= 5:
        return None
    candidates = [s for s in sales if s.verified and s.price > 0
                  and s.name not in PROTECTED and s.name not in reserved
                  and not (floor == 1 and s.name == "Grand Welcome")]
    # Prefer spare unprotected gifts; keep useful Cigarette Holder last.
    candidates.sort(key=lambda s: (s.name == "Cigarette Holder", s.tier, -s.price, s.name))
    return candidates[0] if candidates else None


def with_budget(action: Action, state: ShopState, floor: int) -> Action | None:
    if action.cost <= state.currency:
        return action
    reserved = frozenset(ingredient for recipe in state.fusions
                         if recipe.verified and recipe.result in REQUIRED_BY_FLOOR[floor]
                         and recipe.result not in state.owned
                         for ingredient in recipe.ingredients)
    sale = choose_sale(state.sales, floor, needed=action.cost, currency=state.currency,
                       reserved=reserved)
    return Action("sell", sale.name) if sale else None


def next_action(floor: int, state: ShopState, *, completed=frozenset(),
                materials_bought: int = 0) -> Action:
    """Choose one verified transaction, or leave if no safe action remains.

    completed contains stable action IDs like 'heal:Faust', 'buy:X', 'fuse:Y',
    'upgrade:X:0', or 'sell:Z' to avoid repeating a failed transaction.
    """
    if floor not in REQUIRED_BY_FLOOR or state.currency < 0:
        raise ValueError("Invalid Rabbit Hole shop state")

    def eligible(action: Action) -> Action | None:
        key = f"{action.kind}:{action.name}"
        if action.kind == "upgrade":
            key += f":{state.owned[action.name]}"
        if key in completed:
            return None
        return with_budget(action, state, floor)

    # Heal Faust only at floor-4; floor-1 event checks use a different ID.
    heal_id = state.event_check_id if floor == 1 else "Faust" if floor == 4 else None
    if (heal_id and (floor != 1 or heal_id != "Faust")
            and heal_id in state.sp and state.sp[heal_id] < 45):
        action = eligible(Action("heal", heal_id, SP_HEAL_COST))
        if action:
            return action

    # Only attempt an upgrade if the gift is confirmed in inventory.
    if floor == 4:
        for name in UPGRADE_GOALS:
            if name not in state.owned:
                continue
            level = state.owned[name]
            if level not in TIER4_UPGRADE_COST:
                continue
            if level < 2:
                action = eligible(Action("upgrade", name, TIER4_UPGRADE_COST[level]))
                if action:
                    return action

    for name in sorted(REQUIRED_BY_FLOOR[floor]):
        if name in state.owned:
            continue
        for offer in state.offers:
            if offer.name == name and offer.verified and offer.price >= 0:
                action = eligible(Action("buy", name, offer.price))
                if action:
                    return action
        for recipe in state.fusions:
            if recipe.result == name and allowed_fusion(recipe, state):
                action = eligible(Action("fuse", name, recipe.cost, recipe.ingredients, recipe.random_result))
                if action:
                    return action

    # Floors 1-3: purchase up to two tier-II/III fusion materials per visit.
    if floor <= 3 and materials_bought < 2:
        for offer in sorted(state.offers, key=lambda x: (-x.tier, x.price, x.name)):
            if (offer.verified and offer.tier in (2, 3) and offer.price >= 0
                and offer.name not in PROTECTED and offer.name not in state.owned
                and f"buy:{offer.name}" not in completed):
                action = eligible(Action("buy", offer.name, offer.price))
                if action:
                    return action

    # Missing required gifts do not abort the run.
    return Action("leave")
