"""Shared MD progression and bounded run management for Rabbit Hole."""
from copy import deepcopy
from source.rabbit_hole import CheckpointRequired


def configure_rewards(params, teams, keywordless):
    # The upstream reward picker needs these even though the custom shop does not.
    params.GIFTS = [deepcopy(teams[k]) for k in ('RUPTURE','POISE','SINKING')]
    params.KEYWORDLESS = {'clearmirror':2,'artisticsense':2,'grandwelcome':2,'holder':2, **keywordless}


def reset_run(params):
    params.LVL=1
    params.HARD=False
    params.RABBIT_NODE=None
    params.DEAD=0
    params.MOVE_ANIMATION=False
    params.SELECTED=['FAUST']


def repeat_runs(run, params, count, resource_check=None):
    completed=0
    failures=0
    while completed<count and not params.stop_event.is_set():
        if run():
            completed+=1
            failures=0
        else:
            failures+=1
            if not params.RESTART:
                return completed
            if failures>=3:
                raise CheckpointRequired('Three consecutive runs failed. Automation stopped instead of spending resources indefinitely.')
        if completed>=count:
            return completed
        if resource_check is not None:
            resource_check()
        reset_run(params)
    return completed


def recover_connection(u, checkpoint):
    for _ in range(3):
        if u.p.stop_event.is_set():
            raise u.StopExecution
        if u.p.LIMBUS_NAME not in (u.gui.getActiveWindowTitle() or ''):
            u.pause(u.gui.getActiveWindowTitle())
        if not u.now.button('ServerError'):
            return
        u.now_click.button('ServerError')
        u.time.sleep(2)
    if u.now.button('ServerError'):
        checkpoint('connection','Server error remained after three recognized retry attempts.')
