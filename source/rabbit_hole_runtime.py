"""Rabbit Hole runtime. Uses its own verified combat and shop controllers."""
from pathlib import Path
from datetime import datetime

from source.rabbit_hole import CheckpointRequired, checkpoint_text, floor_plan, node_allowed


def checkpoint(stage, detail=None):
    from source.utils.utils import p, screenshot, cv2, BASE_PATH
    message = detail or checkpoint_text(p.LVL, stage)
    directory = Path(BASE_PATH) / "data" / "rabbit-hole"
    capture_note = ""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{datetime.now():%Y%m%d-%H%M%S-%f}-floor{p.LVL}-{stage}.png"
        if cv2.imwrite(str(path), screenshot()):
            capture_note = f"\nCalibration screenshot: {path}"
    except Exception as exc:
        capture_note = f"\nScreenshot unavailable: {exc}"
    raise CheckpointRequired(f"Rabbit Hole checkpoint — floor {p.LVL}\n{message}{capture_note}")


def require_node(name):
    from source.utils import params as p
    if not node_allowed(p.LVL, name):
        checkpoint("route", f"Cannot enter {name} on floor {p.LVL}. Choose a verified safe route manually.")
    p.RABBIT_NODE = name


def try_first_turn():
    from source.utils.utils import screenshot, p
    from source.rabbit_hole_vision import HollowVision
    from source.rabbit_hole_combat import fight_first_turn, allowed_encounter
    if allowed_encounter(p.LVL,p.RABBIT_NODE):
        vision = HollowVision()
        if vision.observe(screenshot()) != "unknown":
            fight_first_turn(vision)
            return True
    from source.rabbit_hole_boss_vision import BossVision
    from source.rabbit_hole_boss_combat import run_solo_battle
    vision = BossVision()
    encounter,state = vision.inspect(screenshot())
    if state is None:
        return False
    eligible = {"faelantern":3,"kod":4,"roses":5}
    if encounter in eligible and p.LVL == eligible[encounter] and p.RABBIT_NODE == "Boss":
        if state.planning or (encounter == "kod" and state.turn >= 3):
            run_solo_battle(vision,encounter)
            return True
    if p.LVL in (3,4,5) and p.RABBIT_NODE in ("Normal","Focused","Miniboss") and state.planning and not encounter:
        run_solo_battle(vision,"ordinary")
        return True
    return False


def deploy():
    from source.utils.utils import p
    from source.rabbit_hole_combat import allowed_encounter
    if not allowed_encounter(p.LVL, p.RABBIT_NODE) and p.RABBIT_NODE not in ("Boss", "Normal", "Focused", "Miniboss"):
        checkpoint("combat")
    from source.battle import select
    if not select(["FAUST"]):
        checkpoint("combat", "Could not deploy Faust. Check the team and current encounter manually.")


def run():
    from source.utils.utils import p, now, now_rgb, time, gui, pause, StopExecution
    from source.pack import pack
    from source.move import move

    while not p.stop_event.is_set():
        if p.LIMBUS_NAME not in (window := gui.getActiveWindowTitle()):
            pause(window)
            continue
        if now.button("PackChoice"):
            pack()
        elif now.button("TOBATTLE"):
            deploy()
        elif try_first_turn():
            pass
        elif now_rgb.button("winrate") or now.button("pause"):
            checkpoint("combat")
        elif now.button("shop") or now.button("supershop"):
            from source.rabbit_hole_shop_adapter import run_windows_shop
            run_windows_shop()
        elif now.button("EGObin") or now.button("encounterreward"):
            checkpoint("reward")
        elif now_rgb.button("event"):
            checkpoint("event")
        elif now.button("victory") or now.button("defeat"):
            checkpoint("finish", "Run ended. Collect rewards manually. Relaunch with floor 1 for a new run.")
        elif now.button("Move"):
            p.HARD = floor_plan(p.LVL).hard
            if not move():
                checkpoint("route")
        elif now.button("loading") or now.button("connecting"):
            # Bounded wait; unknown/transitional screens never reach click recovery.
            for _ in range(60):
                if p.stop_event.is_set():
                    raise StopExecution
                if not (now.button("loading") or now.button("connecting")):
                    break
                time.sleep(0.5)
            else:
                checkpoint("loading", "Loading did not finish within 30 seconds.")
        else:
            checkpoint("setup" if p.LVL == 1 else "unknown")
        time.sleep(0.2)
    raise StopExecution
