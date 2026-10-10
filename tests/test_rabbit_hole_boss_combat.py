import os
from pathlib import Path
import unittest
from unittest.mock import Mock
from source.rabbit_hole import CheckpointRequired
from source.rabbit_hole_combat_policy import BattlePolicy, BattleState
from source.rabbit_hole_boss_combat import advance


class BattlePolicyTests(unittest.TestCase):
    def test_kod_turn_three_reset_precedes_all_fallbacks(self):
        for planning in (False,True):
            for used in (False,True):
                p=BattlePolicy('kod',boucher_used=used)
                self.assertEqual(p.decide(BattleState(3,planning=planning)),'reset')

    def test_kod_turn_two_still_uses_boucher(self):
        p=BattlePolicy('kod',le_trou_used=True)
        self.assertEqual(p.decide(BattleState(2)),'boucher')

    def test_finished_battle_does_not_retry(self):
        self.assertEqual(BattlePolicy('kod').decide(BattleState(3,alive=False)),'finished')

    def test_faelantern_le_trou_does_not_depend_on_corrosion_or_charm(self):
        for corroded in (False,True):
            p=BattlePolicy('faelantern')
            self.assertEqual(p.decide(BattleState(1,charmed=True,corroded=corroded)),'le_trou')

    def test_faelantern_can_emerge_on_turn_two_or_three(self):
        for turn in (2,3):
            p=BattlePolicy('faelantern',le_trou_used=True)
            self.assertEqual(p.decide(BattleState(turn,emerged=True)),'boucher')
            self.assertEqual(p.decide(BattleState(turn,emerged=False)),'wait_emergence')

    def test_unselectable_faust_waits_without_reset(self):
        p=BattlePolicy('faelantern',le_trou_used=True)
        self.assertEqual(p.decide(BattleState(2,emerged=True,charmed=True)),'wait_emergence')

    def test_damage_only_after_verified_boucher(self):
        p=BattlePolicy('faelantern',le_trou_used=True)
        io=Mock();state=BattleState(3,emerged=True)
        self.assertEqual(advance(p,state,io),'boucher')
        self.assertEqual(p.decide(BattleState(4,corroded=True)),'damage')
        self.assertNotEqual(p.decide(state),'damage')

    def test_ordinary_survivors_use_winrate_after_hollow_or_boucher(self):
        for attrs in ({'hollow_used':True},{'boucher_used':True}):
            self.assertEqual(BattlePolicy('ordinary',**attrs).decide(BattleState(3)),'winrate')

    def test_turn_number_does_not_invent_ego_history(self):
        with self.assertRaises(CheckpointRequired):
            BattlePolicy('ordinary').decide(BattleState(2))

    def test_start_failure_never_records_ego_use(self):
        p=BattlePolicy('kod');io=Mock();io.start.side_effect=CheckpointRequired('start failed')
        with self.assertRaises(CheckpointRequired):
            advance(p,BattleState(1),io)
        self.assertFalse(p.le_trou_used)
        self.assertFalse(p.started_turns)

    def test_duplicate_planning_frame_never_repeats_input(self):
        p=BattlePolicy('ordinary',hollow_used=True);io=Mock();s=BattleState(2)
        self.assertEqual(advance(p,s,io),'winrate')
        self.assertEqual(advance(p,s,io),'wait')
        io.auto_select.assert_called_once_with('winrate');io.start.assert_called_once()

    def test_damage_fallback_dispatches_damage_once(self):
        io=Mock();p=BattlePolicy('faelantern',boucher_used=True)
        advance(p,BattleState(4),io)
        io.auto_select.assert_called_once_with('damage');io.choose_ego.assert_not_called()

    def test_reset_requires_verified_turn_one(self):
        p=BattlePolicy('kod',le_trou_used=True,boucher_used=True,started_turns={1,2});io=Mock()
        io.reset.return_value=BattleState(3)
        with self.assertRaises(CheckpointRequired):
            advance(p,BattleState(3),io)
        self.assertTrue(p.boucher_used);io.start.assert_not_called()
        io.reset.return_value=BattleState(1)
        advance(p,BattleState(3),io)
        self.assertFalse(p.boucher_used);self.assertFalse(p.started_turns)

    def test_roses_does_not_start_without_verified_three_part_targeting(self):
        p=BattlePolicy('roses',le_trou_used=True);io=Mock()
        with self.assertRaises(CheckpointRequired):
            advance(p,BattleState(2),io)
        io.start.assert_not_called()


VIDEO_DIR=os.environ.get('RABBIT_COMBAT_VIDEO_DIR')
@unittest.skipUnless(VIDEO_DIR,'Set RABBIT_COMBAT_VIDEO_DIR to replay user combat recordings')
class CombatVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import cv2
        from source.rabbit_hole_boss_vision import BossVision
        cls.cv2=cv2;cls.v=BossVision()

    def frame(self,name,t):
        p=Path(VIDEO_DIR)/f'2026-10-10 {name}.mp4'
        c=self.cv2.VideoCapture(str(p));c.set(self.cv2.CAP_PROP_POS_MSEC,t*1000)
        ok,f=c.read();c.release();self.assertTrue(ok,str(p));return f

    def test_three_bosses_and_turn_counters(self):
        for name,t,boss,turn in [('11-06-36',1,'kod',1),('11-14-17',25,'faelantern',3),('11-17-41',28,'roses',2)]:
            with self.subTest(name=name):
                b,s=self.v.inspect(self.frame(name,t));self.assertEqual(b,boss);self.assertEqual(s.turn,turn);self.assertTrue(s.planning)

    def test_boucher_menu_is_not_a_planning_screen(self):
        f=self.frame('11-06-36',40);_,s=self.v.inspect(f)
        self.assertEqual(s.turn,2);self.assertFalse(s.planning)
        self.assertIsNotNone(self.v.locate(f,'boucher'));self.assertIsNotNone(self.v.locate(f,'mao_menu'))

    def test_emerged_both_timings_and_hold_overlay_is_not_charm(self):
        for name,t,turn,charmed in [('11-11-00',19,2,True),('11-14-17',25,3,False)]:
            b,s=self.v.inspect(self.frame(name,t))
            self.assertEqual(b,'faelantern');self.assertEqual(s.turn,turn)
            self.assertTrue(s.emerged);self.assertEqual(s.planning,not charmed);self.assertFalse(s.charmed)

    def test_normal_skills_do_not_confirm_ego_selection(self):
        self.assertFalse(self.v.ego_selected(self.frame('11-14-17',1)))
        for name,t in [('11-06-36',41.3),('11-06-36',5),('11-17-41',28)]:
            self.assertTrue(self.v.ego_selected(self.frame(name,t)),(name,t))

    def test_wrong_resolution_or_erased_counter_is_rejected(self):
        f=self.frame('11-17-41',28)
        self.assertEqual(self.v.inspect(f[::2,::2]),(None,None))
        f[86:133,66:144]=0;self.assertEqual(self.v.inspect(f),(None,None))
