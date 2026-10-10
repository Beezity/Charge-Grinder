"""Failure-injection and transaction-evidence tests; no desktop is imported."""
import unittest
from source.rabbit_hole import CheckpointRequired
from source.rabbit_hole_shop_adapter import WindowsShopAdapter
from source.rabbit_hole_shop_controller import _changed, run_shop
from source.rabbit_hole_shop_policy import Action, ShopState, Sale, PROTECTED, next_action
from source.rabbit_hole_shop_vision import Word, ShopVision, gift_name


class ShopAdapterTests(unittest.TestCase):
    def test_protected_sale_never_sends_input(self):
        for name in PROTECTED:
            a = WindowsShopAdapter(4, io=object(), vision=object())
            a.before = ShopState(0, {name: 0})
            with self.assertRaises(CheckpointRequired): a.execute(Action('sell', name))

    def test_protected_fusion_never_sends_input(self):
        a = WindowsShopAdapter(4, io=object(), vision=object())
        a.before = ShopState(0, {'Clear Mirror, Calm Water': 0, 'A': 0, 'B': 0})
        with self.assertRaises(CheckpointRequired):
            a.execute(Action('fuse', 'Artistic Sense', ingredients=tuple(a.before.owned), random_result=True))

    def test_unreadable_protected_name_is_not_saleable_alias(self):
        with self.assertRaises(CheckpointRequired): gift_name('Fragment of Conceil')
        self.assertEqual(gift_name('Clear Mirror, Calm Water++'), ('Clear Mirror, Calm Water', 2))

    def test_timeout_does_not_repeat_click(self):
        class IO:
            def __init__(self): self.clicks = []
            def click(self, p): self.clicks.append(p)
            def capture(self): return None
            def wait(self, n): pass
        class Vision:
            def state(self, f): return 'unknown'
        io = IO(); a = WindowsShopAdapter(4, io, Vision())
        with self.assertRaises(CheckpointRequired): a.click_wait((1, 2), 'shop')
        self.assertEqual(io.clicks, [(1, 2)])

    def test_sales_require_exact_currency_and_inventory(self):
        before = ShopState(0, {'Spare': 0, 'Keep': 0}, sales=(Sale('Spare', 96, True),))
        self.assertTrue(_changed(Action('sell', 'Spare'), before, ShopState(96, {'Keep': 0})))
        self.assertFalse(_changed(Action('sell', 'Spare'), before, ShopState(95, {'Keep': 0})))
        self.assertFalse(_changed(Action('sell', 'Spare'), before, ShopState(96, {})))

    def test_random_fusion_requires_receipt_and_all_ingredients_consumed(self):
        before = ShopState(100, {'A': 0, 'B': 0, 'C': 0, 'Keep': 0})
        action = Action('fuse', 'Artistic Sense', ingredients=('A', 'B', 'C'), random_result=True)
        after = ShopState(100, {'Different gift': 0, 'Keep': 0})
        self.assertTrue(_changed(action, before, after, fusion_result='Different gift'))
        self.assertFalse(_changed(action, before, after))
        self.assertFalse(_changed(action, before, ShopState(100, {'Different gift': 0, 'A': 0, 'Keep': 0}), fusion_result='Different gift'))
        self.assertFalse(_changed(action, before, ShopState(100, {'Different gift': 0}), fusion_result='Different gift'))

    def test_negative_sp_needs_two_verified_treatments(self):
        class Adapter:
            def __init__(self): self.state = ShopState(200, sp={'Faust': -40}); self.count = 0
            def observe(self): return self.state
            def execute(self, action):
                self.count += 1
                self.state = ShopState(self.state.currency-100, sp={'Faust': min(45, self.state.sp['Faust']+45)})
                return True
            def leave(self): pass
        a = Adapter(); run_shop(4, a)
        self.assertEqual(a.count, 2)
        self.assertEqual(a.state.sp['Faust'], 45)

    def test_known_random_result_failure_is_not_a_shop_abort(self):
        a = WindowsShopAdapter(2, io=object(), vision=object())
        a.inventory = {'A': 3, 'B': 3, 'C': 2, 'Fragment of Decay': 4}
        recipes = a.plan_fusions({n: 0 for n in a.inventory})
        self.assertTrue(recipes)
        self.assertTrue(recipes[0].random_result)
        self.assertNotIn('Fragment of Decay', recipes[0].ingredients)
        state = ShopState(0, {'Different gift': 0})
        self.assertEqual(next_action(2, state).kind, 'leave')

    def test_healing_rejected_outside_expected_floor(self):
        for floor in (1, 2, 3, 5):
            a = WindowsShopAdapter(floor, io=object(), vision=object()); a.before = ShopState(100)
            with self.assertRaises(CheckpointRequired): a.execute(Action('heal', 'Faust', 100))

    def test_confirmation_takes_precedence_over_background_shop(self):
        words = [Word(t, .99, 0, 0) for t in ('Shop', 'Refresh', 'Leave', 'Sell [Prejudice] for 76 Cost?')]
        self.assertEqual(ShopVision.classify(words), 'sale_confirm')
