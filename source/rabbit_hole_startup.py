"""Reuse normal MD entry with Rabbit Hole's verified starting gifts."""
from source.rabbit_hole import CheckpointRequired

START_BUTTONS = (
    'Drive', 'MD', 'Start', 'enterInvert', 'ConfirmTeam',
    'underleveled', 'enterBonus', 'Confirm.0', 'refuse',
)


def is_startup(now):
    return any(now.button(name) for name in START_BUTTONS)


def enter_dungeon(dungeon_start, params, checkpoint, gift_selector=None):
    if params.LVL != 1:
        raise CheckpointRequired('A new MD run starts on floor 1. Select floor 1 and start again.')
    params.HARD = False
    params.HOS_MODE = False
    params.EXTREME = False
    params.BUFF = [1, 0, 1, 0, 0, 0, 0, 0, 0, 0]
    params.SELECTED = ['FAUST']
    params.RABBIT_NODE = None

    def starting_gifts():
        if gift_selector is not None:
            return gift_selector()
        from source.rabbit_hole_startup_gifts import run_starting_gifts
        return run_starting_gifts()

    dungeon_start(starting_gifts=starting_gifts)
