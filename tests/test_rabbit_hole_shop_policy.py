import unittest
from source.rabbit_hole_shop_policy import (
    Action, Fusion, Offer, PROTECTED, Sale, ShopState, allowed_fusion,
    choose_sale, floor4_reserve, next_action, remaining_upgrade_cost,
)


class ShopPolicyTests(unittest.TestCase):
    def test_permanent_protection(self):
        self.assertEqual(len(PROTECTED), 5)
        for gift in PROTECTED:
            sales = (Sale(gift, 500, True),)
            self.assertIsNone(choose_sale(sales, 4, needed=100, currency=0))
            self.assertFalse(allowed_fusion(
                Fusion("Fragment of Conceit", (gift,), verified=True),
                ShopState(100, {gift: 0})))

    def test_only_sell_for_shortfall_and_keep_cigarette_holder_last(self):
        sales = (Sale("Cigarette Holder", 80, True, 3),
                 Sale("Unknown", 100, False, 1), Sale("Safe T2", 40, True, 2))
        self.assertIsNone(choose_sale(sales, 4, needed=100, currency=100))
        self.assertEqual(choose_sale(sales, 4, needed=100, currency=0).name, "Safe T2")
        self.assertIsNone(choose_sale((Sale("Unverified", 400),), 4,
                                       needed=100, currency=0))

    def test_no_grand_welcome_sale_on_first_floor(self):
        self.assertIsNone(choose_sale((Sale("Grand Welcome", 100, True),), 1,
                                       needed=100, currency=0))
        self.assertEqual(choose_sale((Sale("Grand Welcome", 100, True),), 2,
                                     needed=100, currency=0).name, "Grand Welcome")

    def test_heal_exact_floors(self):
        s = ShopState(200, sp={"Faust": 0, "Event ID": 0}, event_check_id="Event ID")
        self.assertEqual(next_action(1, s), Action("heal", "Event ID", 100))
        self.assertEqual(next_action(4, s), Action("heal", "Faust", 100))
        self.assertNotEqual(next_action(2, s).kind, "heal")
        self.assertNotEqual(next_action(3, s).kind, "heal")
        self.assertNotEqual(next_action(5, s).kind, "heal")

    def test_upgrade_total_and_resume_levels(self):
        self.assertEqual([remaining_upgrade_cost(x) for x in (0, 1, 2)], [300, 200, 0])
        s = ShopState(700, owned={"Clear Mirror, Calm Water": 0, "Artistic Sense": 0},
                      sp={"Faust": 45})
        self.assertEqual(floor4_reserve(s), 600)
        self.assertEqual(next_action(4, s), Action("upgrade", "Clear Mirror, Calm Water", 100))
        s2 = ShopState(700, owned={"Clear Mirror, Calm Water": 1, "Artistic Sense": 2},
                       sp={"Faust": 45})
        self.assertEqual(floor4_reserve(s2), 200)
        self.assertEqual(next_action(4, s2), Action("upgrade", "Clear Mirror, Calm Water", 200))
        self.assertEqual(floor4_reserve(ShopState(700)), 700)

    def test_insufficient_money_triggers_sale_only_for_action(self):
        s = ShopState(50, owned={"Clear Mirror, Calm Water": 0}, sp={"Faust": 45},
                      sales=(Sale("Spare Gift", 60, True),))
        self.assertEqual(next_action(4, s), Action("sell", "Spare Gift"))
        self.assertEqual(next_action(4, ShopState(50, owned=s.owned, sp=s.sp)), Action("leave"))

    def test_missing_gifts_continue_without_abort(self):
        self.assertEqual(next_action(4, ShopState(700, sp={"Faust": 45})), Action("leave"))
        self.assertEqual(next_action(5, ShopState(0)), Action("leave"))

    def test_requires_verified_fusion_and_nonprotected_ingredients(self):
        recipe = Fusion("Fragment of Conceit", ("T2 gift", "T3 gift"), 0, True)
        s = ShopState(100, owned={"T2 gift": 0, "T3 gift": 0}, fusions=(recipe,))
        self.assertEqual(next_action(2, s), Action("fuse", "Fragment of Conceit", 0,
                                                  ("T2 gift", "T3 gift")))
        self.assertEqual(next_action(2, ShopState(100, owned=s.owned,
                                      fusions=(Fusion(recipe.result, recipe.ingredients),))),
                         Action("leave"))

    def test_buy_only_verified_affordable_requirement(self):
        s = ShopState(400, sp={"Faust": 45},
                      offers=(Offer("Fragment of Decay", 4, 300, True),))
        self.assertEqual(next_action(4, s), Action("buy", "Fragment of Decay", 300))
        self.assertEqual(next_action(4, ShopState(200, sp=s.sp, offers=s.offers)), Action("leave"))

    def test_bounded_material_buying(self):
        s = ShopState(200, offers=(Offer("Tier3 sample", 3, 100, True),))
        self.assertEqual(next_action(1, s), Action("buy", "Tier3 sample", 100))
        self.assertEqual(next_action(1, s, materials_bought=2), Action("leave"))


if __name__ == "__main__":
    unittest.main()
