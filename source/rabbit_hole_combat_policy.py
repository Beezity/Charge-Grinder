"""Battle-local decisions. Usage is recorded only after a verified turn start.

These rules do not infer that EGO was used from a turn number. Resuming an
unknown battle requires calibration rather than replaying EGO blindly.
"""
from dataclasses import dataclass, field
from source.rabbit_hole import CheckpointRequired


@dataclass(frozen=True)
class BattleState:
    turn: int
    planning: bool = True
    alive: bool = True
    emerged: bool = False
    charmed: bool = False
    corroded: bool = False


@dataclass
class BattlePolicy:
    encounter: str
    le_trou_used: bool = False
    boucher_used: bool = False
    hollow_used: bool = False
    started_turns: set = field(default_factory=set)

    def decide(self, state):
        if type(state.turn) is not int or state.turn < 1:
            raise CheckpointRequired("The battle turn counter is not verified.")
        if not state.alive:
            return "finished"
        # A turn-3 counter is enough for KoD's reset, even during its banner.
        if self.encounter == "kod" and state.turn >= 3:
            return "reset"
        if not state.planning or state.turn in self.started_turns:
            return "wait"
        if self.encounter == "faelantern":
            if self.hollow_used:
                return "damage"
            return "hollow" if state.emerged and not state.charmed else "wait_emergence"
        if self.hollow_used or self.boucher_used:
            return "winrate"
        if not self.le_trou_used:
            if state.turn != 1:
                raise CheckpointRequired("Cannot infer EGO history from the turn counter.")
            return "le_trou"
        return "boucher_roses" if self.encounter == "roses" else "boucher"

    def started(self, action, state):
        if action not in {"le_trou", "boucher", "boucher_roses", "hollow", "winrate", "damage", "wait_emergence"}:
            raise ValueError("Only a verified combat start can be recorded.")
        if state.turn in self.started_turns:
            raise CheckpointRequired("This turn was already started; no duplicate combat input.")
        self.started_turns.add(state.turn)
        if action == "le_trou":
            self.le_trou_used = True
        elif action in {"boucher", "boucher_roses"}:
            self.boucher_used = True
        elif action == "hollow":
            self.hollow_used = True

    def reset_verified(self, state):
        if not state.planning or state.turn != 1:
            raise CheckpointRequired("Retry has not returned to turn 1; EGO usage remains recorded.")
        self.le_trou_used = self.boucher_used = self.hollow_used = False
        self.started_turns.clear()
