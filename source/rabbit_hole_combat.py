"""Verified first-turn overclock sequence; input injected for replay tests."""
from source.rabbit_hole import CheckpointRequired


def allowed_encounter(floor, node):
    return floor in (1, 2) or (floor == 3 and node in ("Normal", "Focused", "Miniboss", "Risky"))


def slot_and_start(io, floor, node=None):
    """Advance each visual transition once. Never retry an unverified input.

    Mouse release is guaranteed by the input adapter even if interrupted.
    Turn 1/wave 1 and Mao's portrait are enforced by HollowVision.
    """
    if not allowed_encounter(floor, node):
        raise CheckpointRequired("This floor/boss requires manual Awakening or targeting; overclock is disabled.")
    state = io.observe()
    if state == "battle":
        io.hold((909, 987), 1.5)
        state = io.expect("le_trou_menu")
    if state == "le_trou_menu":
        io.hold((1180, 391), 1.5)
        state = io.expect("overclock_menu")
    if state == "overclock_menu":
        io.click((1180, 391))
        state = io.expect("slotted")
    if state == "slotted":
        io.press("p")
        state = io.expect("ready")
    if state != "ready":
        raise CheckpointRequired("Could not verify solo Mao Faust, turn 1, wave 1 and Hollow overclock. No turn was started.")
    io.press("enter")
    return "started"


class DesktopInput:
    def __init__(self, vision):
        from source.utils import utils
        self.u = utils
        self.vision = vision

    def guard(self):
        if self.u.p.stop_event.is_set():
            raise self.u.StopExecution
        if self.u.p.LIMBUS_NAME not in (self.u.gui.getActiveWindowTitle() or ""):
            raise CheckpointRequired("Limbus lost focus during Hollow selection. Resume with Limbus focused.")

    def observe(self):
        self.guard()
        return self.vision.observe(self.u.screenshot())

    def expect(self, expected):
        deadline = self.u.time.monotonic() + 4
        while self.u.time.monotonic() < deadline:
            if self.observe() == expected:
                return expected
            self.u.time.sleep(0.1)
        raise CheckpointRequired(f"Hollow selection did not reach {expected}. Stopped without repeating the click.")

    def hold(self, point, seconds):
        self.guard()
        self.u.win_moveTo(*point, tsize=(1, 1))
        try:
            self.u.gui.mouseDown()
            deadline = self.u.time.monotonic() + seconds
            while self.u.time.monotonic() < deadline:
                self.guard()
                self.u.time.sleep(0.05)
        finally:
            self.u.gui.mouseUp()

    def click(self, point):
        self.guard()
        self.u.win_click(*point, tsize=(1, 1))

    def press(self, key):
        self.guard()
        self.u.gui.press(key)


def fight_first_turn(vision):
    from source.utils import utils as u
    from source.rabbit_hole_runtime import checkpoint
    io = DesktopInput(vision)
    try:
        slot_and_start(io, u.p.LVL, u.p.RABBIT_NODE)
        from source.rabbit_hole_boss_vision import BossVision
        from source.rabbit_hole_boss_combat import SoloBattleIO, advance
        from source.rabbit_hole_combat_policy import BattlePolicy
        later_io = SoloBattleIO(BossVision())
        policy = BattlePolicy("ordinary", hollow_used=True, started_turns={1})
        # Never reuse the overclock sequence; surviving enemies use Win Rate.
        deadline = u.time.monotonic() + 180
        while u.time.monotonic() < deadline:
            io.guard()
            if any(u.now.button(name) for name in (
                "EGObin", "encounterreward", "victory", "defeat", "Move", "PackChoice")):
                u.p.RABBIT_NODE = None
                return
            _, state = later_io.observe_battle()
            if state is not None and state.turn > 1 and state.planning:
                action = advance(policy,state,later_io)
                if action != "wait":
                    deadline = u.time.monotonic()+180
            u.time.sleep(0.2)
        raise CheckpointRequired("The battle did not finish within 180 seconds. Check for a surviving enemy or a later turn.")
    except CheckpointRequired as exc:
        checkpoint("combat", str(exc))
