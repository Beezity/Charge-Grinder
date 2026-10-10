import ast
from pathlib import Path
import threading
from types import SimpleNamespace,ModuleType
import unittest
from unittest.mock import Mock,patch
import sys
from source.rabbit_hole import CheckpointRequired
from source.rabbit_hole_progression import configure_rewards,repeat_runs,recover_connection
from source.rabbit_hole_trials import lowest_hp_match


class ProgressionTests(unittest.TestCase):
    def params(self):
        return SimpleNamespace(stop_event=threading.Event(),RESTART=True,LVL=5,HARD=True,RABBIT_NODE='Boss',DEAD=1,MOVE_ANIMATION=True)

    def test_configure_reward_preferences_does_not_mutate_upstream(self):
        teams={k:{'buy':[]} for k in ('RUPTURE','POISE','SINKING')}
        p=self.params();configure_rewards(p,teams,{'other':1})
        p.GIFTS[0]['buy'].append('changed')
        self.assertEqual(teams['RUPTURE']['buy'],[])
        self.assertIn('clearmirror',p.KEYWORDLESS)
        self.assertIn('other',p.KEYWORDLESS)

    def test_repeats_exact_requested_success_count_and_resets_floor(self):
        p=self.params(); seen=[]
        def run():seen.append((p.LVL,p.RABBIT_NODE));return True
        check=Mock()
        self.assertEqual(repeat_runs(run,p,3,check),3)
        self.assertEqual(seen,[(5,'Boss'),(1,None),(1,None)])
        self.assertEqual(check.call_count,3)

    def test_final_run_still_converts_modules(self):
        p=self.params();check=Mock()
        self.assertEqual(repeat_runs(Mock(return_value=True),p,1,check),1)
        check.assert_called_once()

    def test_stop_after_run_prevents_module_conversion(self):
        p=self.params();check=Mock()
        def run():p.stop_event.set();return True
        self.assertEqual(repeat_runs(run,p,2,check),1)
        check.assert_not_called()

    def test_failure_retry_is_bounded_and_respects_restart(self):
        p=self.params();run=Mock(return_value=False)
        with self.assertRaises(CheckpointRequired):repeat_runs(run,p,10)
        self.assertEqual(run.call_count,3)
        p.RESTART=False;run.reset_mock()
        self.assertEqual(repeat_runs(run,p,10),0)
        run.assert_called_once()

    def test_stop_prevents_next_run(self):
        p=self.params();p.stop_event.set();run=Mock()
        self.assertEqual(repeat_runs(run,p,4),0);run.assert_not_called()

    def test_connection_retry_only_clicks_recognized_dialog_three_times(self):
        p=self.params();p.LIMBUS_NAME='Limbus'
        u=SimpleNamespace(p=p,StopExecution=RuntimeError,gui=SimpleNamespace(getActiveWindowTitle=lambda:'Limbus'),
                          now=SimpleNamespace(button=Mock(return_value=True)),now_click=SimpleNamespace(button=Mock()),
                          pause=Mock(),time=SimpleNamespace(sleep=Mock()))
        checkpoint=Mock(side_effect=CheckpointRequired())
        with self.assertRaises(CheckpointRequired):recover_connection(u,checkpoint)
        self.assertEqual(u.now_click.button.call_count,3)
        u.now.button.return_value=False;u.now_click.button.reset_mock()
        recover_connection(u,checkpoint);u.now_click.button.assert_not_called()

    def test_lowest_hp_percentage_rejects_unreadable_or_ambiguous_values(self):
        def row(x,text,confidence=.99):return ([[x,0],[x+100,0],[x+100,40],[x,40]],text,confidence)
        result=lowest_hp_match([row(0,'Max HP +30%'),row(300,'Max HP +10%'),row(600,'Defense Level +5%')])
        self.assertEqual(result,(150.,0.,50.,20.))
        self.assertIsNone(lowest_hp_match([row(0,'HP +10% and damage +20%'),row(300,'HP +5%',.8),row(600,'HP -10%')]))

    def test_shared_trial_priority_avoids_hp_and_preserves_normal_behavior(self):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'source/grab.py').read_text())
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='find_trial'
               or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='mounting_trials' for t in n.targets)]
        original=(20,0,80,40);fallback=(400,0,80,40)
        ns=dict(p=SimpleNamespace(RABBIT_HOLE=False),PTH={name:name for name in
            ['trial_'+n for n in ('DefenseSkillUp','DefenseLevelUp','Resilient','Growth','BodyUp','Keen','OffenseLevelUp','TakeLessDamage','ClashPower','FinalPower','BasePower','Brutality','Headstrong')]},
            cv2=SimpleNamespace(TM_SQDIFF_NORMED=1),LocateRGB=SimpleNamespace(locate_all=lambda path,*a,**kw:[original] if path=='trial_BodyUp' else []))
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'grab.py','exec'),ns)
        with patch('source.rabbit_hole_trials.read_lowest_hp',return_value=fallback) as read:
            self.assertEqual(ns['find_trial'](None),[original]);read.assert_not_called()
            ns['p'].RABBIT_HOLE=True
            self.assertEqual(ns['find_trial'](None),[fallback]);read.assert_called_once()

    def test_normal_floor_rabbit_trial_screen_uses_trial_handler(self):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'source/grab.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='grab_EGO')
        for rabbit in (False,True):
            with self.subTest(rabbit=rabbit):
                trial=Mock(return_value=('image',None))
                ns=dict(p=SimpleNamespace(HARD=False,RABBIT_HOLE=rabbit,EXTREME=False,BUFF=[0]*10),
                    now=SimpleNamespace(button=lambda name,*a:name in ('EGObin','trials')),
                    now_click=SimpleNamespace(button=Mock()),time=SimpleNamespace(sleep=Mock()),
                    gui=SimpleNamespace(press=Mock()),LocateRGB=SimpleNamespace(locate_all=lambda *a,**kw:[]),
                    PTH={'Owned':'Owned'},REG={'Owned':'Owned','EGO':'EGO','buffs':'buffs'},
                    screenshot=Mock(return_value='image'),get_trial=trial,get_gift=Mock(return_value='image'),
                    wait_while_condition=Mock())
                exec(compile(ast.Module(body=[node],type_ignores=[]),'grab.py','exec'),ns)
                self.assertTrue(ns['grab_EGO']())
                self.assertEqual(trial.call_count,int(rabbit))

    def test_runtime_dispatches_shared_events_rewards_confirmation_and_victory(self):
        import source.rabbit_hole_runtime as runtime
        states=['transition','event','EGObin','encounterreward','Confirm','victory'];calls=[]
        p=self.params();p.LIMBUS_NAME='Limbus';p.LVL=1
        def button(key):return bool(states and states[0]==key)
        def handler(key):
            def action():
                if not button(key):return False
                calls.append(key);states.pop(0);return True
            return action
        utils=ModuleType('source.utils.utils')
        utils.__dict__.update(p=p,now=SimpleNamespace(button=button),now_rgb=SimpleNamespace(button=button),
                             time=SimpleNamespace(sleep=lambda _:states.pop(0) if states and states[0]=='transition' else None,monotonic=lambda:0),gui=SimpleNamespace(getActiveWindowTitle=lambda:'Limbus'),pause=Mock(),StopExecution=RuntimeError)
        mods={'source.utils.utils':utils}
        for name,attrs in {
            'source.pack':{'pack':Mock()},'source.move':{'move':Mock()},
            'source.event':{'event':handler('event')},
            'source.grab':{'grab_EGO':handler('EGObin'),'grab_card':handler('encounterreward'),'confirm':handler('Confirm')},
            'Bot':{'dungeon_end':handler('victory'),'dungeon_fail':Mock()},
        }.items():
            m=ModuleType(name);m.__dict__.update(attrs);mods[name]=m
        with patch.dict(sys.modules,mods),patch.object(runtime,'try_first_turn',return_value=False):
            self.assertTrue(runtime.run())
        self.assertEqual(calls,['event','EGObin','encounterreward','Confirm','victory'])
        self.assertEqual(p.RABBIT_NODE,'Normal')
