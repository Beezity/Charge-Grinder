import importlib.util
import logging
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

from source.rabbit_hole import (
    CheckpointRequired, FLOORS, choose_pack, combat, floor_plan,
    node_allowed, protected_gifts, checkpoint_text,
    validate_keyword,
)

ROOT = Path(__file__).resolve().parents[1]


def load_without_desktop(filename, **objects):
    """Load real controller functions with an inert input/capture boundary."""
    stub = types.ModuleType("source.utils.utils")
    stub.__dict__.update(objects)
    spec = importlib.util.spec_from_file_location("isolated_" + filename, ROOT / "source" / (filename + ".py"))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"source.utils.utils": stub}):
        spec.loader.exec_module(module)
    return module


class PolicyTests(unittest.TestCase):
    def test_rabbit_hole_requires_primary_rupture_keyword(self):
        validate_keyword(["RUPTURE"])
        validate_keyword(["Rupture", "POISE"])
        for keywords in ([], ["BURN"], ["POISE", "RUPTURE"]):
            with self.subTest(keywords=keywords), self.assertRaises(ValueError):
                validate_keyword(keywords)

    def test_normal_to_hard_boundary(self):
        self.assertEqual([floor_plan(i).hard for i in range(1, 6)], [False] * 4 + [True])

    def test_floor_validation(self):
        for bad in (0, 6, -1, True, 3.0, "3"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                floor_plan(bad)

    def test_exact_packs(self):
        expected = ["FlatbrokeGamblers", "HellsChicken", "TobeCleaved", "HatredandDespair", "Line2"]
        self.assertEqual([FLOORS[i].pack for i in range(1, 6)], expected)
        for floor in range(1, 6):
            self.assertEqual(choose_pack(floor, {expected[floor - 1]: 0}, False), 0)

    def test_pack_absence_never_selects_an_arbitrary_pack(self):
        self.assertIsNone(choose_pack(3, {"HellsChicken": 0}, True))
        with self.assertRaises(CheckpointRequired):
            choose_pack(3, {"HellsChicken": 0}, False)
        with self.assertRaises(CheckpointRequired):
            choose_pack(3, {}, False)

    def test_grand_welcome_protection_expires_after_floor_one(self):
        self.assertIn("Grand Welcome", protected_gifts(1))
        for floor in range(2, 6):
            self.assertNotIn("Grand Welcome", protected_gifts(floor))
            self.assertIn("Sharp Needles & Threads", protected_gifts(floor))
            self.assertIn("Clear Mirror, Calm Water", protected_gifts(floor))

    def test_early_battles_and_floor_three_boss_differ(self):
        for floor in range(1, 4):
            self.assertIn("OVERCLOCK", combat(floor))
        self.assertIn("Le Trou", combat(3, boss=True))
        self.assertIn("Boucher un trou", combat(3, boss=True, turn=2))

    def test_faelantern_exception(self):
        self.assertIn("7 sinners", combat(3, True, True))
        self.assertIn("Charmed", combat(3, True, True))
        self.assertIn("emerges", combat(3, True, True, 2))
        with self.assertRaises(ValueError):
            combat(2, True, True)

    def test_kod_and_roses(self):
        self.assertIn("RETRY", combat(4, True, turn=3))
        self.assertIn("Rose + Signpost + Flesh", combat(5, True, turn=2))
        self.assertIn("Manual review", combat(5, True, turn=3))

    def test_invalid_turn(self):
        for turn in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                combat(1, turn=turn)

    def test_unknown_and_risky_nodes(self):
        self.assertFalse(node_allowed(3, "Risky"))
        self.assertTrue(node_allowed(2, "Risky"))
        self.assertFalse(node_allowed(1, "Unknown"))
        self.assertFalse(node_allowed(1, None))

    def test_shop_upgrade_timing(self):
        self.assertIn("do not upgrade", checkpoint_text(2, "shop"))
        self.assertIn("unupgraded", checkpoint_text(3, "shop"))
        self.assertIn("Calm Water++", checkpoint_text(4, "shop"))
        self.assertIn("Artistic Sense++", checkpoint_text(4, "shop"))


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.params = types.SimpleNamespace(RABBIT_HOLE=True, LVL=3)
        self.move = load_without_desktop("move", p=self.params)

    def test_blocks_risky_even_if_other_route_is_slower(self):
        nodes = [["Event", "Focused", None], ["Risky", "Focused", None]]
        self.assertEqual(self.move.next_step(nodes, []), (1, "Focused"))

    def test_no_safe_path(self):
        self.assertEqual(self.move.next_step([["Risky", None, None]], []), (None, None))

    def test_cross_connection_avoids_future_risk(self):
        nodes = [["Event", None, None], ["Risky", "Normal", None]]
        self.assertEqual(self.move.next_step(nodes, [((0, 0), (1, 1))]), (0, "Event"))

    def test_upstream_route_costs_unchanged_when_disabled(self):
        self.params.RABBIT_HOLE = False
        nodes = [["Event", "Focused", None], ["Risky", "Focused", None]]
        self.assertEqual(self.move.next_step(nodes, []), (0, "Event"))

    def test_unknown_node_is_not_chosen(self):
        self.assertEqual(self.move.next_step([["Unknown", "Normal", None]], []), (1, "Normal"))

    def test_unknown_route_fallback_stops_before_input(self):
        with patch("source.rabbit_hole_runtime.checkpoint", side_effect=CheckpointRequired("route")):
            with self.assertRaises(CheckpointRequired):
                self.move.move_fallback()


class PackControllerTests(unittest.TestCase):
    def test_unrecognized_floor_does_not_increment(self):
        params = types.SimpleNamespace(RABBIT_HOLE=True, EXTREME=False)
        detector = types.SimpleNamespace(locate_all=lambda *a, **kw: [])
        module = load_without_desktop("pack", p=params, LocateGray=detector,
            PTH={f"lvl{i}": str(i) for i in range(1, 6)}, REG={"lvl": None})
        with patch("source.rabbit_hole_runtime.checkpoint", side_effect=CheckpointRequired("floor")):
            with self.assertRaises(CheckpointRequired):
                module.update_lvl(3)
        params.RABBIT_HOLE = False
        self.assertEqual(module.update_lvl(3), 4)

    def test_recognized_floor_is_used(self):
        detector = types.SimpleNamespace(locate_all=lambda image, **kw: [1] if image == "5" else [],
                                         get_conf=lambda *a, **kw: 1)
        module = load_without_desktop("pack", p=types.SimpleNamespace(RABBIT_HOLE=True, EXTREME=False),
            LocateGray=detector, PTH={f"lvl{i}": str(i) for i in range(1, 6)}, REG={"lvl": None})
        self.assertEqual(module.update_lvl(1), 5)


class RuntimeTests(unittest.TestCase):
    def test_sensitive_stages_never_reach_regular_combat_or_shop(self):
        from source.rabbit_hole_runtime import run
        for visible, stage in (("TOBATTLE", "combat"), ("winrate", "combat"),
                               ("shop", "shop"), ("EGObin", "reward"),
                               ("event", "event"), ("victory", "finish")):
            with self.subTest(visible=visible):
                stub = types.ModuleType("source.utils.utils")
                stub.p = types.SimpleNamespace(stop_event=types.SimpleNamespace(is_set=lambda: False),
                                               LIMBUS_NAME="LimbusCompany", LVL=3)
                stub.now = stub.now_rgb = types.SimpleNamespace(button=lambda name: name == visible)
                stub.time = types.SimpleNamespace(sleep=Mock())
                stub.gui = types.SimpleNamespace(getActiveWindowTitle=lambda: "LimbusCompany")
                stub.pause = Mock()
                stub.StopExecution = type("StopExecution", (Exception,), {})
                pack_stub = types.ModuleType("source.pack")
                pack_stub.pack = Mock()
                move_stub = types.ModuleType("source.move")
                move_stub.move = Mock()
                with patch.dict(sys.modules, {"source.utils.utils": stub, "source.pack": pack_stub,
                                              "source.move": move_stub}), \
                     patch("source.rabbit_hole_runtime.try_first_turn", return_value=False), \
                     patch("source.rabbit_hole_runtime.deploy", side_effect=lambda: __import__('source.rabbit_hole_runtime', fromlist=['checkpoint']).checkpoint('combat')), \
                     patch("source.rabbit_hole_runtime.checkpoint", side_effect=CheckpointRequired) as stop:
                    with self.assertRaises(CheckpointRequired):
                        run()
                    self.assertEqual(stop.call_args.args[0], stage)
                    move_stub.move.assert_not_called()
                    pack_stub.pack.assert_not_called()


class SettingsCompatibilityTests(unittest.TestCase):
    def setUp(self):
        stub = types.ModuleType("source_app.utils")
        stub.QObject = object
        stub.pyqtSignal = lambda *args: None
        paths = types.ModuleType("source.utils.paths")
        paths.PACKS = paths.WORDLESS = {}
        spec = importlib.util.spec_from_file_location("isolated_settings", ROOT / "source_app/settings_manager.py")
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"source_app.utils": stub, "source.utils.paths": paths}):
            spec.loader.exec_module(module)
        self.manager = object.__new__(module.SettingsManager)
        self.manager._thread = None

    def test_old_settings_remain_valid(self):
        values = [1, 1, 1] + [False] * 6
        result, corrupt = self.manager.verify_file_data({"EXTRA": values})
        self.assertFalse(corrupt)
        self.assertEqual(result["EXTRA"], values)

    def test_rabbit_toggle_round_trip_and_type_validation(self):
        import json
        values = [1, 1, 1] + [False] * 6 + [True]
        result, corrupt = self.manager.verify_file_data(json.loads(json.dumps({"EXTRA": values})))
        self.assertFalse(corrupt)
        self.assertTrue(result["EXTRA"][9])
        values[9] = "true"
        result, corrupt = self.manager.verify_file_data({"EXTRA": values})
        self.assertTrue(corrupt)
        self.assertNotIn("EXTRA", result)


if __name__ == "__main__":
    unittest.main()
