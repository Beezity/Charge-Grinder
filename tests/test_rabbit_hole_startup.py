import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from source.rabbit_hole import CheckpointRequired
from source.rabbit_hole_startup import START_BUTTONS, is_startup, enter_dungeon


class StartupTests(unittest.TestCase):
    def test_recognizes_entry_stages_without_generic_confirmation(self):
        for stage in START_BUTTONS:
            self.assertTrue(is_startup(SimpleNamespace(button=lambda name: name == stage)))
        for stage in ('Confirm', 'Move', 'PackChoice', 'winrate'):
            self.assertFalse(is_startup(SimpleNamespace(button=lambda name: name == stage)))

    def test_uses_shared_startup_with_normal_strategy_defaults(self):
        params = SimpleNamespace(LVL=1, HARD=True, HOS_MODE=True, EXTREME=True)
        shared, checkpoint = Mock(), Mock()
        selector = Mock()
        enter_dungeon(shared, params, checkpoint, gift_selector=selector)
        self.assertFalse(params.HARD)
        self.assertFalse(params.HOS_MODE)
        self.assertFalse(params.EXTREME)
        self.assertEqual(params.BUFF, [1, 0, 1, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(params.SELECTED, ['FAUST'])
        shared.call_args.kwargs['starting_gifts']()
        selector.assert_called_once()
        checkpoint.assert_not_called()

    def test_wrong_floor_does_not_start_a_new_run(self):
        shared = Mock()
        with self.assertRaises(CheckpointRequired):
            enter_dungeon(shared, SimpleNamespace(LVL=4), Mock())
        shared.assert_not_called()

    def test_real_shared_chain_keeps_graces_and_replaces_affinity_gifts(self):
        # Execute the real function with an inert desktop boundary. This checks
        # that resuming at each entry stage reaches the custom gift hook, never
        # the generic Rupture selection or an HOS battle sequence.
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'Bot.py').read_text())
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'dungeon_start'
                 or isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'start_locations' for t in n.targets)]
        for stage in START_BUTTONS:
            with self.subTest(stage=stage):
                team, grace, hook = Mock(), Mock(), Mock(side_effect=CheckpointRequired('gift boundary'))
                actions = []
                def chain(preset, steps):
                    actions.extend(steps)
                    for step in steps:
                        if callable(step):
                            step()
                namespace = dict(
                    p=SimpleNamespace(EXTREME=False, HOS_MODE=False),
                    Action=lambda *a, **kw: ('action', a, kw),
                    ClickAction=lambda *a, **kw: ('click', a, kw),
                    select_team=team, select_grace=grace,
                    confirm_team_warning=Mock(),
                    time=SimpleNamespace(sleep=Mock()),
                    now_click=SimpleNamespace(button=Mock()),
                    try_click=SimpleNamespace(button=Mock()),
                    now=SimpleNamespace(button=lambda name: name == stage),
                    now_rgb=SimpleNamespace(button=Mock(return_value=False)),
                    wait_while_condition=Mock(), chain_actions=chain,
                    gui=SimpleNamespace(PauseException=type('PauseException', (Exception,), {})),
                )
                exec(compile(ast.Module(body=nodes, type_ignores=[]), 'Bot.py', 'exec'), namespace)
                with self.assertRaises(CheckpointRequired):
                    namespace['dungeon_start'](starting_gifts=hook)
                hook.assert_called_once()
                self.assertFalse(any(isinstance(a, tuple) and a[0] == 'click' for a in actions))
                if stage in ('Drive', 'MD', 'Start', 'enterInvert', 'ConfirmTeam'):
                    team.assert_called_once()
                if stage not in ('Confirm.0', 'refuse'):
                    grace.assert_called_once()
