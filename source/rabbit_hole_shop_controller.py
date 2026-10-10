"""Transaction-verified shop runner with an injected desktop adapter.

The UI adapter is deliberately separate. Never repeat an unverified
transaction after a timeout; stop for review instead.
"""
from dataclasses import dataclass
from source.rabbit_hole import CheckpointRequired
from source.rabbit_hole_shop_policy import Action, ShopState, next_action


@dataclass(frozen=True)
class ShopReport:
    actions: tuple[Action, ...]
    missing: tuple[str, ...]


def _changed(action: Action, before: ShopState, after: ShopState, *, fusion_result=None) -> bool:
    before_names, after_names = set(before.owned), set(after.owned)
    added, removed = after_names-before_names, before_names-after_names
    if action.kind == "sell":
        price = next((s.price for s in before.sales if s.name == action.name and s.verified), None)
        return (removed == {action.name} and not added and price is not None
                and after.currency-before.currency == price)
    if action.kind == "buy":
        return (added == {action.name} and not removed
                and before.currency-after.currency == action.cost)
    if action.kind == "upgrade":
        return (not added and not removed and before.currency-after.currency == action.cost
                and after.owned.get(action.name, -1) == before.owned.get(action.name, -1)+1)
    if action.kind == "heal":
        old = before.sp.get(action.name)
        return (old is not None and old < 45 and not added and not removed
                and before.currency-after.currency == action.cost
                and after.sp.get(action.name) == min(45, old+45))
    if action.kind == "fuse":
        result = fusion_result if action.random_result else action.name
        return (result is not None and added == {result}
                and removed == set(action.ingredients)
                and before.currency-after.currency == action.cost)
    return False


def run_shop(floor, adapter, *, max_actions=25):
    """Adapter contract: observe()->ShopState, execute(Action), leave().

    Unavailable gifts are nonfatal. Unrecognized interface states or unverified
    transactions remain hard checkpoints to protect the player's inventory.
    """
    if max_actions < 1:
        raise ValueError("max_actions must be positive")
    actions = []
    attempted = set()
    material_purchases = 0
    for _ in range(max_actions):
        before = adapter.observe()
        if not isinstance(before, ShopState):
            raise CheckpointRequired("Shop could not be read with sufficient confidence.")
        action = next_action(floor, before, completed=frozenset(attempted),
                             materials_bought=material_purchases)
        if action.kind == "leave":
            from source.rabbit_hole_shop_policy import REQUIRED_BY_FLOOR
            missing = tuple(sorted(REQUIRED_BY_FLOOR[floor] - before.owned.keys()))
            adapter.leave()
            return ShopReport(tuple(actions), missing)
        key = f"{action.kind}:{action.name}"
        if action.kind == "upgrade":
            key += f":{before.owned[action.name]}"
        # Adapter must verify the exact named gift at confirmation; the generic
        # source.shop.sell() selects by tier alone and MUST NOT be used here.
        if not adapter.execute(action):
            raise CheckpointRequired(f"Could not verify {action.kind} {action.name}; review shop manually.")
        after = adapter.observe()
        if not isinstance(after, ShopState) or not _changed(action, before, after, fusion_result=getattr(adapter, "last_fusion_result", None)):
            raise CheckpointRequired(f"{action.kind} {action.name} was not visibly confirmed; no retry.")
        actions.append(action)
        if action.kind != "heal" or after.sp.get(action.name, -45) >= 45:
            attempted.add(key)
        if action.kind == "buy" and action.name not in {
                "Fragment of Conceit", "Fragment of Decay",
                "Clear Mirror, Calm Water", "Artistic Sense"}:
            material_purchases += 1
    raise CheckpointRequired("Shop action limit reached; review shop before resuming.")
