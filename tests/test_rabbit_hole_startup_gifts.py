import ast
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import cv2

from source.rabbit_hole import CheckpointRequired
from source.rabbit_hole_startup_gifts import StartupVision, select_starting_gifts

ROOT=Path(__file__).resolve().parents[1]
CAPTURES=Path(os.environ.get('RABBIT_STARTUP_CAPTURE_DIR','/missing'))
IDS=['7edfcf66-e888-41ce-9245-b66763c9bc70','2a13e3d4-9e07-47a5-80f1-cf27bc8409ee',
     '99cbaf58-a88e-4043-acb1-98d4e2dece02','e51c840f-c583-4578-b4d9-0ed21b4649a4',
     '5c34d78a-e6db-457a-9332-be5835575a5c','4f2cf71a-571e-4234-a285-0f5b2b9b25c7',
     'ff595928-659a-4942-a251-fc16688d878d','31239842-e3c7-4a6b-83a5-2a9fd96d3bcf']


class GiftIO:
    def __init__(self, stage='starter', missing=False, wrong=False):
        self.stage=stage
        self.missing=missing
        self.wrong=wrong
        self.clicks=[]
        self.vision=SimpleNamespace(has=lambda f,n:n in f,locate=self.locate)
        self.u=SimpleNamespace(now_click=SimpleNamespace(button=Mock()))
        self.entered=False

    def capture(self):
        states={
            'starter':{'starter','search_on','cigarette','cigarette_border','starter_selected'},
            'search':{'search','keywordless','count0'},
            'welcome':{'search','keywordless','welcome_name','count1'},
            'both':{'search','keywordless','welcome_name','needle_name','count2','cost160'},
            'confirm':{'search','confirm160'},
            'entered':set(),
        }
        f=states[self.stage].copy()
        if self.wrong and self.stage=='search':
            f.discard('count0'); f.add('count1')
        return f

    def locate(self,f,n):
        if self.missing and n=='needle_icon':return None
        return {'welcome_icon':(944,474),'needle_icon':(447,701)}.get(n)

    def guard(self):pass
    def click(self,point):
        self.clicks.append(point)
        self.stage={(1624,882):'search',(944,474):'welcome',(447,701):'both',
                    (1645,860):'confirm',(1149,743):'entered'}.get(point,self.stage)

    def wait_for(self,predicate,detail):
        if not predicate(self.capture()):raise CheckpointRequired(detail)
    def wait_search(self):self.stage='search'
    def wait_entered(self):self.entered=True


class GiftControllerTests(unittest.TestCase):
    def test_visible_singular_name_keeps_shop_protection(self):
        from source.rabbit_hole_shop_vision import gift_name
        self.assertEqual(gift_name('Sharp Needle & Thread'),('Sharp Needles & Threads',0))

    def test_free_starter_then_exact_two_searches_and_one_confirmation(self):
        io=GiftIO()
        select_starting_gifts(io)
        self.assertTrue(io.entered)
        self.assertNotIn((1239,395),io.clicks) # already selected, don't toggle off
        self.assertEqual(io.clicks,[(535,665),(1624,882),(985,286),(944,474),(447,701),(1645,860),(1149,743)])
        io.u.now_click.button.assert_called_once_with('giftSearch')

    def test_missing_needle_never_purchases(self):
        io=GiftIO(stage='search',missing=True)
        with self.assertRaises(CheckpointRequired):select_starting_gifts(io)
        self.assertNotIn((1645,860),io.clicks)

    def test_unexpected_existing_selection_never_adds_or_purchases(self):
        io=GiftIO(stage='search',wrong=True)
        with self.assertRaises(CheckpointRequired):select_starting_gifts(io)
        self.assertEqual(io.clicks,[(985,286)])

    def test_resume_verified_two_gifts_does_not_toggle_them_off(self):
        io=GiftIO(stage='both')
        select_starting_gifts(io)
        self.assertEqual(io.clicks,[(985,286),(1645,860),(1149,743)])

    def test_cost_mismatch_never_confirms(self):
        io=GiftIO(stage='both')
        capture=io.capture
        io.capture=lambda:capture()-{'cost160'}
        with self.assertRaises(CheckpointRequired):select_starting_gifts(io)
        self.assertNotIn((1645,860),io.clicks)

    def test_shared_warning_uses_existing_confirm_first_and_specific_fallback(self):
        tree=ast.parse((ROOT/'Bot.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='confirm_team_warning')
        for existing,warning in ((True,True),(False,True),(False,False)):
            with self.subTest(existing=existing,warning=warning):
                click=Mock()
                now=SimpleNamespace(button=Mock(return_value=warning))
                ns=dict(now_click=SimpleNamespace(button=Mock(return_value=existing)),now=now,
                        p=SimpleNamespace(LIMBUS_NAME='Limbus'),gui=SimpleNamespace(getActiveWindowTitle=lambda:'Limbus'),
                        pause=Mock(),win_click=click,wait_while_condition=Mock(return_value=True))
                exec(compile(ast.Module(body=[node],type_ignores=[]),'Bot.py','exec'),ns)
                ns['confirm_team_warning']()
                if not existing and warning:click.assert_called_once_with(1149,743)
                else:click.assert_not_called()
                if existing:now.button.assert_not_called()


@unittest.skipUnless((CAPTURES/('codex-clipboard-'+IDS[0]+'.png')).exists(),'Original startup captures not supplied')
class StartupReplayTests(unittest.TestCase):
    def setUp(self):
        self.v=StartupVision()
        self.frames=[cv2.imread(str(CAPTURES/('codex-clipboard-'+p+'.png'))) for p in IDS]

    def test_supplied_sequence_and_hover_is_not_selection(self):
        expected=[{'starter','cigarette','cigarette_border','starter_selected'},
                  {'search','count0'}, {'welcome_name','count1'}, {'welcome_name','count1'},
                  {'welcome_name','needle_name','count2','cost160'},
                  {'welcome_name','needle_name','count2','cost160'}, {'confirm160'}, set()]
        for frame,names in zip(self.frames,expected):
            for name in names:self.assertTrue(self.v.has(frame,name),name)
        self.assertFalse(self.v.has(self.frames[3],'needle_name')) # needle is only hovered
        self.assertFalse(self.v.has(self.frames[1],'welcome_name')) # welcome only hovered
        self.assertEqual(self.v.locate(self.frames[1],'welcome_icon'),(944,474))
        self.assertEqual(self.v.locate(self.frames[1],'needle_icon'),(447,701))
        self.assertFalse(self.v.has(self.frames[7],'starter'))
        self.assertFalse(self.v.has(self.frames[7],'confirm160'))

    def test_missing_cost_or_gift_text_fails_receipt(self):
        for rect,name in (((1705,245,68,60),'cost160'),((1375,475,365,55),'needle_name')):
            frame=self.frames[4].copy(); x,y,w,h=rect;frame[y:y+h,x:x+w]=0
            self.assertFalse(self.v.has(frame,name))

    def test_shared_underlevel_template_matches_popup_only(self):
        t=cv2.imread(str(ROOT/'ImageAssets/UI/start/underleveled.png'),0)
        for i in (6,7):
            f=cv2.cvtColor(self.frames[i],cv2.COLOR_BGR2GRAY)[330:480,620:1310]
            score=cv2.minMaxLoc(cv2.matchTemplate(f,t,cv2.TM_CCOEFF_NORMED))[1]
            self.assertEqual(score>=.9,i==7)
