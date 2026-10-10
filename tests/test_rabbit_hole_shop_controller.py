import unittest
from source.rabbit_hole import CheckpointRequired
from source.rabbit_hole_shop_policy import ShopState, Sale
from source.rabbit_hole_shop_controller import run_shop


class StubAdapter:
    def __init__(self, initial, after=None, success=True):
        self.current = initial
        self.after = after
        self.success = success
        self.executed = []
        self.left = False

    def observe(self):
        return self.current

    def execute(self, action):
        self.executed.append(action)
        if self.after is not None:
            self.current = self.after
        return self.success

    def leave(self):
        self.left = True


class ShopControllerTests(unittest.TestCase):
    def test_missing_gifts_continue_and_leave(self):
        a = StubAdapter(ShopState(100, sp={"Faust": 45}))
        result = run_shop(4, a)
        self.assertTrue(a.left)
        self.assertIn("Fragment of Conceit", result.missing)
        self.assertEqual(result.actions, ())

    def test_sale_requires_verified_inventory_change(self):
        a = StubAdapter(ShopState(0, owned={"Clear Mirror, Calm Water": 0, "Spare": 0},
                                  sp={"Faust": 45}, sales=(Sale("Spare", 30, True),)))
        with self.assertRaises(CheckpointRequired):
            run_shop(4, a)
        self.assertEqual(a.executed[0].kind, "sell")
        self.assertFalse(a.left)

    def test_successful_sale_then_upgrade(self):
        class Adaptive:
            def __init__(self):
                self.current = ShopState(0, owned={"Clear Mirror, Calm Water": 0, "Spare": 0},
                                         sp={"Faust": 45}, sales=(Sale("Spare", 100, True),))
                self.actions = []
                self.left = False
            def observe(self): return self.current
            def execute(self, action):
                self.actions.append(action)
                if action.kind == "sell":
                    self.current = ShopState(100, owned={"Clear Mirror, Calm Water": 0},
                                             sp={"Faust": 45})
                elif action.kind == "upgrade":
                    self.current = ShopState(0, owned={"Clear Mirror, Calm Water": 1},
                                             sp={"Faust": 45})
                return True
            def leave(self): self.left = True
        a = Adaptive()
        result = run_shop(4, a)
        self.assertTrue(a.left)
        self.assertEqual([x.kind for x in result.actions], ["sell", "upgrade"])


if __name__ == "__main__":
    unittest.main()
