import os
import ast
from pathlib import Path
import types
import unittest
from unittest.mock import Mock

from source.rabbit_hole import CheckpointRequired
from source.rabbit_hole_combat import DesktopInput, allowed_encounter, slot_and_start


class ReplayInput:
    def __init__(self, states):
        self.states = iter(states)
        self.actions = []

    def observe(self):
        return next(self.states)

    def expect(self, expected):
        state = self.observe()
        if state != expected:
            raise CheckpointRequired(f"Expected {expected}, got {state}")
        return state

    def hold(self, point, seconds):
        self.actions.append(("hold", point, seconds))

    def click(self, point):
        self.actions.append(("click", point))

    def press(self, key):
        self.actions.append(("press", key))


STATES = ["battle", "le_trou_menu", "overclock_menu", "slotted", "ready"]


class OverclockSequenceTests(unittest.TestCase):
    def test_hold_then_click_before_targeting_and_start(self):
        io = ReplayInput(STATES)
        self.assertEqual(slot_and_start(io, 1), "started")
        self.assertEqual(io.actions, [
            ("hold", (909, 987), 1.5), ("hold", (1180, 391), 1.5),
            ("click", (1180, 391)), ("press", "p"), ("press", "enter")])

    def test_resume_does_not_toggle_overclock_back_off(self):
        io = ReplayInput(STATES[2:])
        slot_and_start(io, 2)
        self.assertEqual(io.actions, [("click", (1180, 391)), ("press", "p"), ("press", "enter")])

    def test_resume_at_ready_starts_once(self):
        io = ReplayInput(["ready"])
        slot_and_start(io, 1)
        self.assertEqual(io.actions, [("press", "enter")])

    def test_failed_transition_never_starts_or_retries(self):
        for failed_at in range(1, len(STATES)):
            io = ReplayInput(STATES[:failed_at] + ["unknown"])
            with self.subTest(failed_at=failed_at), self.assertRaises(CheckpointRequired):
                slot_and_start(io, 1)
            self.assertNotIn(("press", "enter"), io.actions)
            self.assertEqual(len(io.actions), failed_at)

    def test_unknown_initial_screen_is_untouched(self):
        io = ReplayInput(["unknown"])
        with self.assertRaises(CheckpointRequired):
            slot_and_start(io, 1)
        self.assertEqual(io.actions, [])

    def test_late_floors_and_unknown_floor_three_are_untouched(self):
        for floor, node in ((3, None), (3, "Boss"), (4, "Boss"), (5, "Boss")):
            io = ReplayInput(["ready"])
            with self.subTest(floor=floor, node=node), self.assertRaises(CheckpointRequired):
                slot_and_start(io, floor, node)
            self.assertFalse(io.actions)
        self.assertTrue(allowed_encounter(3, "Normal"))
        self.assertTrue(allowed_encounter(3, "Risky"))

    def test_mouse_is_released_when_hold_is_interrupted(self):
        io = object.__new__(DesktopInput)
        io.guard = Mock(side_effect=[None, CheckpointRequired("lost focus")])
        io.u = types.SimpleNamespace(win_moveTo=Mock(), gui=types.SimpleNamespace(
            mouseDown=Mock(), mouseUp=Mock()), time=types.SimpleNamespace(monotonic=lambda: 0, sleep=Mock()))
        with self.assertRaises(CheckpointRequired):
            io.hold((1180, 391), 1.5)
        io.u.gui.mouseUp.assert_called_once()

    def test_windows_release_precedes_stop_or_focus_exception(self):
        path = Path(__file__).resolve().parents[1] / "source/utils/os_windows_backend.py"
        tree = ast.parse(path.read_text())
        method = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "mouseUp")
        release = Mock()
        namespace = {"_get_bridge": lambda: types.SimpleNamespace(mouse_release=release),
                     "_fail_safe_check": Mock(side_effect=CheckpointRequired("stopped"))}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"), namespace)
        with self.assertRaises(CheckpointRequired):
            namespace['mouseUp']()
        release.assert_called_once_with(button="left")


# Original captures are not distributed. Set this directory to replay them locally.
CAPTURE_DIR = os.environ.get("RABBIT_CAPTURE_DIR")
CAPTURES = [
    "1b0de03f-70ce-46ce-820e-b6a8a3cd7b85", "9a1fe38f-cad5-40a1-b170-935058671e16",
    "96061767-3727-4883-9413-3e4b7bb9a481", "99578f6f-ce3d-4df9-816e-10d2b452c910",
    "b5e18d8c-f2d7-4846-9031-5d8008f22757",
]


@unittest.skipUnless(CAPTURE_DIR, "Set RABBIT_CAPTURE_DIR to replay original calibration screenshots")
class ScreenshotReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import cv2
        from source.rabbit_hole_vision import HollowVision
        cls.vision = HollowVision()
        cls.frames = [cv2.imread(str(Path(CAPTURE_DIR) / f"codex-clipboard-{name}.png")) for name in CAPTURES]
        if any(frame is None for frame in cls.frames):
            raise AssertionError("A requested calibration screenshot is missing")

    def test_five_real_screens_are_distinguished(self):
        self.assertEqual([self.vision.observe(frame) for frame in self.frames], STATES)

    def test_wrong_resolution_and_missing_portrait_are_rejected(self):
        self.assertEqual(self.vision.observe(self.frames[0][::2, ::2]), "unknown")
        frame = self.frames[4].copy()
        frame[959:1028, 865:954] = 0
        self.assertEqual(self.vision.observe(frame), "unknown")

    def test_turn_and_wave_must_be_confirmed(self):
        for region in ((86, 133, 66, 144), (30, 85, 65, 147)):
            frame = self.frames[4].copy()
            y1, y2, x1, x2 = region
            frame[y1:y2, x1:x2] = 0
            self.assertEqual(self.vision.observe(frame), "unknown")

    def test_start_marker_alone_cannot_start_normal_skill(self):
        frame = self.frames[0].copy()
        frame[722:781, 988:1090] = self.frames[4][722:781, 988:1090]
        self.assertEqual(self.vision.observe(frame), "unknown")

    def test_missing_overclock_warning_does_not_confirm_overclock(self):
        frame = self.frames[2].copy()
        frame[398:490, 1060:1295] = 0
        self.assertEqual(self.vision.observe(frame), "unknown")


if __name__ == "__main__":
    unittest.main()
