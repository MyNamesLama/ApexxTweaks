import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tweaker.actions import ACTIONS, optional_action
from tweaker.engine import Engine
from tweaker.platform import MockBackend, WindowsBackend
from tweaker.session import GamingSession
from tweaker.targets import encode, executable, approved_image, classify_inventory
from tweaker.windows_controls import ABSENT, ProcessExpired, startup_read, startup_write, task_definition, task_read, literal
from tweaker.analysis import sustained
from tweaker.benchmark import analyze, advanced_compare
from tweaker.fortnite import recommendations


def task_xml(command=r'C:\Users\me\Spotify.exe', args='', sid='S-1-5-21-42', level='LeastPrivilege', enabled='true', action=None):
    from xml.sax.saxutils import escape
    return f'''<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"><Principals><Principal id="Author"><UserId>{sid}</UserId><LogonType>InteractiveToken</LogonType><RunLevel>{level}</RunLevel></Principal></Principals><Settings><Enabled>{enabled}</Enabled></Settings><Actions Context="Author">{action or '<Exec><Command>'+escape(command)+'</Command><Arguments>'+escape(args)+'</Arguments></Exec>'}</Actions></Task>'''

class TargetPolicyTests(unittest.TestCase):
    def test_approved_commands(self):
        for text in [r'"C:\Users\me\Spotify.exe" --minimized',r'C:\Apps\Discord.exe --start-minimized']:
            self.assertTrue(executable(text).endswith('.exe'))
    def test_unsafe_commands(self):
        for text in [r'C:\Program Files\Spotify\Spotify.exe',r'"C:\Apps\cmd.exe" /c Spotify.exe',r'"C:\Apps\Fortnite.exe"',r'"C:\Apps\Discord.exe" --update',r'"C:\Apps\Spotify.exe" --process-start-args cmd.exe',r'"\\server\Spotify.exe"',r'"C:\Apps\..\Spotify.exe"',r'"%APPDATA%\Spotify.exe"']:
            with self.subTest(text=text),self.assertRaises(ValueError): executable(text)
    def test_signatures(self):
        path=r'C:\Apps\Spotify.exe'
        self.assertTrue(approved_image(path,'Valid','CN=Spotify AB, O=Spotify AB, C=SE'))
        for status,subject in [('UnknownError','CN=Spotify AB'),('Valid','CN=Spotify AB Malware'),('Valid','O=Other, CN=Other')]:
            self.assertFalse(approved_image(path,status,subject))
        self.assertFalse(approved_image(r'C:\Apps\WinDefend.exe','Valid','CN=Spotify AB'))
    def test_powershell_literal(self):
        self.assertEqual(literal("a'; Stop-Service x; '"),"'a''; Stop-Service x; '''")
    @patch('tweaker.windows_controls.reg_read')
    def test_startup_conflict(self,read):
        target=encode('startup',name='Spotify',command=r'"C:\Apps\Spotify.exe"')
        read.return_value={'exists':True,'type':1,'value':'different'}
        with self.assertRaises(RuntimeError): startup_read(target)
    @patch('tweaker.windows_controls.signature',side_effect=RuntimeError('unsigned'))
    @patch('tweaker.windows_controls.reg_write')
    @patch('tweaker.windows_controls.reg_read',return_value=ABSENT)
    def test_restore_unsigned_not_written(self,read,write,signature):
        target=encode('startup',name='Spotify',command=r'"C:\Apps\Spotify.exe"')
        with self.assertRaises(RuntimeError): startup_write(target,{'exists':True,'type':1,'value':r'"C:\Apps\Spotify.exe"'})
        write.assert_not_called()
    def test_unknown_inventory_is_readonly(self):
        result=classify_inventory({'startup':[{'Command':'WinDefend.exe','Name':'Security'}],'tasks':[{'TaskName':'SecurityUpdate'}]})
        self.assertIn('not actionable',result['startup'][0]['recommendation'])
        self.assertIn('keep update',result['tasks'][0]['recommendation'])

class TaskPolicyTests(unittest.TestCase):
    def test_enabled_flag_does_not_change_fingerprint(self):
        a=task_definition(task_xml(enabled='true'),'S-1-5-21-42')
        b=task_definition(task_xml(enabled='false'),'S-1-5-21-42')
        self.assertEqual(a[2],b[2]); self.assertTrue(a[1]); self.assertFalse(b[1])
    def test_changed_task_fingerprint(self):
        self.assertNotEqual(task_definition(task_xml(),'S-1-5-21-42')[2],task_definition(task_xml(args='--minimized'),'S-1-5-21-42')[2])
    def test_protected_principal_and_actions(self):
        for xml in [task_xml(sid='S-1-5-18'),task_xml(level='HighestAvailable'),task_xml(command=r'C:\Windows\System32\cmd.exe'),task_xml(args='--update'),task_xml(action='<ComHandler><ClassId>x</ClassId></ComHandler>')]:
            with self.subTest(xml=xml),self.assertRaises((ValueError,RuntimeError)): task_definition(xml,'S-1-5-21-42')
    def test_outside_namespace(self):
        for path in ['\\Microsoft\\Windows\\','\\Google\\','\\','\\ApexxTweaksOptional\\Other\\']:
            target=encode('task',path=path,name='Updater',fingerprint='x')
            with self.assertRaises(ValueError): task_read(target)

class ExpandedEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.backend=MockBackend(); self.engine=Engine(self.backend,self.tmp.name)
    def add(self,kind,original,desired):
        target=encode(kind,name='fixture')
        action=optional_action(kind,target,'Fixture '+kind,copy.deepcopy(desired))
        self.engine.register([action]); self.backend.values[target]=copy.deepcopy(original)
        return action
    def test_every_builtin_roundtrip(self):
        for action in ACTIONS.values():
            with self.subTest(action=action.id):
                original=copy.deepcopy(self.backend.read(action.target))
                self.engine.apply(action.id); self.engine.restore_all()
                self.assertEqual(self.backend.read(action.target),original)
    def test_optional_roundtrips_after_restart(self):
        for kind,original,desired in [('startup',{'exists':True,'type':1,'value':'unicode ✓'},ABSENT),('task',{'enabled':True,'fingerprint':'abc'},{'enabled':False,'fingerprint':'abc'}),('eco',{'control':4,'state':4},{'control':5,'state':5})]:
            action=self.add(kind,original,desired); self.engine.apply(action.id)
            fresh=Engine(self.backend,self.tmp.name); fresh.restore_all()
            self.assertEqual(self.backend.read(action.target),original)
    def test_optional_external_changes_preserved(self):
        action=self.add('eco',{'control':0,'state':0},{'control':1,'state':1})
        self.engine.apply(action.id); self.backend.values[action.target]={'control':5,'state':5}
        with self.assertRaises(RuntimeError): self.engine.restore_all()
        self.assertEqual(self.backend.read(action.target),{'control':5,'state':5})
    def test_process_exit_is_safe_restore(self):
        action=self.add('eco',{'control':0,'state':0},{'control':1,'state':1})
        self.engine.apply(action.id)
        with patch.object(self.backend,'read',side_effect=ProcessExpired('PID reused')),patch.object(self.backend,'write') as write:
            self.engine.restore_all(); write.assert_not_called()
        self.assertEqual(self.engine.records[-1]['status'],'restored')
    def test_conflicting_power_methods(self):
        self.engine.apply('power.high')
        with self.assertRaises(RuntimeError): self.engine.apply('power.ac-performance')
    def test_target_alias_conflict(self):
        from dataclasses import replace
        self.engine.register([replace(ACTIONS['power.high'],id='power.alias')])
        self.engine.apply('power.high')
        with self.assertRaises(RuntimeError): self.engine.apply('power.alias')
    def test_change_during_backup_prevents_mutation(self):
        with patch.object(self.backend,'backup',side_effect=lambda target,folder:self.backend.values.update({target:'external'})),patch.object(self.backend,'write') as write:
            with self.assertRaises(RuntimeError): self.engine.apply('power.high')
            write.assert_not_called()
        self.assertEqual(self.engine.records[-1]['status'],'recovery_required')
    def test_session_does_not_own_preexisting_state(self):
        self.backend.values['power']=ACTIONS['power.high'].desired
        session=GamingSession(self.engine); session.start(['power.high']); session.end()
        self.assertEqual(self.backend.read('power'),ACTIONS['power.high'].desired)
        self.assertFalse(self.engine.records)
    def test_session_restores_only_owned_actions(self):
        self.engine.apply('service.fax')
        session=GamingSession(self.engine); session.start(['power.high']); session.end()
        self.assertEqual(self.backend.read('fax'),'Disabled')
        self.assertEqual(self.backend.read('power'),'381b4222-f694-41f0-9685-ff5bb260df2e')
    def test_session_failure_rolls_back_earlier_actions(self):
        action=self.add('task',{'enabled':True,'fingerprint':'x'},{'enabled':False,'fingerprint':'x'})
        orig=self.backend.write
        def write(target,value):
            if target==action.target: raise PermissionError('denied')
            orig(target,value)
        session=GamingSession(self.engine)
        with patch.object(self.backend,'write',side_effect=write):
            with self.assertRaises(PermissionError): session.start(['power.high',action.id])
        self.assertIsNone(session.active)
        self.assertTrue(all(r['status']=='restored' for r in self.engine.records))
    def test_session_two_absent_polls(self):
        session=GamingSession(self.engine); session.start(['power.high'])
        self.assertFalse(session.observe(False)); self.assertTrue(session.active)
        session.observe(True); self.assertFalse(session.observe(False))
        session.observe(True); session.observe(False); self.assertTrue(session.observe(False))
        self.assertIsNone(session.active)
    def test_persistent_actions_refused_by_session(self):
        session=GamingSession(self.engine)
        with self.assertRaises(ValueError): session.start(['service.fax'])
        self.assertFalse(self.engine.records)
    def test_session_rollback_conflict_keeps_recovery(self):
        session=GamingSession(self.engine); session.start(['power.high']); self.backend.values['power']='external'
        with self.assertRaises(RuntimeError): session.end()
        self.assertIsNotNone(session.active)
    @patch('tweaker.platform.WINDOWS',False)
    def test_all_builtin_writes_refused_on_linux(self):
        for a in ACTIONS.values():
            with self.subTest(a=a.id),self.assertRaises(RuntimeError): WindowsBackend().write(a.target,a.desired)

class SustainedTests(unittest.TestCase):
    def fixture(self):
        return {'timestamp':1,'logical_processors':8,'cpu':[{'Name':'0','PercentProcessorTime':96}],
                'processes':[{'IDProcess':10,'Name':'FortniteClient-Win64-Shipping','PercentProcessorTime':300},{'IDProcess':20,'Name':'Spotify','PercentProcessorTime':80}],
                'gpu':[{'Name':'pid_10_luid_0_engtype_3D','UtilizationPercentage':99}],
                'memory':[{'AvailableMBytes':500,'PagesInputPersec':30}]}
    def test_sustained_game_attribution(self):
        result=sustained([self.fixture() for _ in range(5)])
        self.assertTrue(result['gpu_busy_candidate']); self.assertTrue(result['memory_pressure_candidate'])
        self.assertEqual(result['background_cpu_mean_percent_of_machine'][0]['cpu_percent'],10)
    def test_unrelated_gpu_not_attributed(self):
        samples=[self.fixture() for _ in range(4)]
        for sample in samples: sample['gpu'][0]['Name']='pid_999_engtype_3D'
        result=sustained(samples)
        self.assertFalse(result['gpu_busy_candidate']); self.assertEqual(result['gpu_game_coverage'],0)
    def test_transient_core_not_sustained(self):
        samples=[self.fixture() for _ in range(5)]
        for sample in samples[1:]: sample['cpu'][0]['PercentProcessorTime']=10
        self.assertFalse(sustained(samples)['hot_logical_processors'])
    def test_insufficient_samples(self):
        with self.assertRaises(ValueError): sustained([])

class RecoveryAndAccessTests(unittest.TestCase):
    def test_unresolved_optional_action_reloaded_for_individual_undo(self):
        with tempfile.TemporaryDirectory() as folder:
            backend=MockBackend(); engine=Engine(backend,folder)
            target=encode('startup',name='Spotify',command='fixture')
            original={'exists':True,'type':1,'value':'fixture'}
            action=optional_action('startup',target,'Test startup',ABSENT)
            engine.register([action]); backend.values[target]=original
            engine.apply(action.id)
            fresh=Engine(backend,folder)
            self.assertEqual(fresh.actions[action.id],action)
            fresh.restore(fresh.records[-1]); self.assertEqual(backend.read(target),original)
    def test_query_identity_must_pass_before_write_handle(self):
        from contextlib import contextmanager
        from tweaker.windows_controls import process_handle
        calls=[]
        @contextmanager
        def checked(spec,write=False):
            calls.append(write)
            if not write: raise ProcessExpired('reused PID')
            yield None
        with patch('tweaker.windows_controls._checked_process_handle',checked):
            with self.assertRaises(ProcessExpired):
                with process_handle({},write=True): pass
        self.assertEqual(calls,[False])
    def test_write_handle_is_revalidated_with_query_handle_alive(self):
        from contextlib import contextmanager
        from tweaker.windows_controls import process_handle
        events=[]
        @contextmanager
        def checked(spec,write=False):
            events.append(('open',write))
            try: yield ('api','write' if write else 'query')
            finally: events.append(('close',write))
        with patch('tweaker.windows_controls._checked_process_handle',checked):
            with process_handle({},write=True) as pair: self.assertEqual(pair[1],'write')
        self.assertEqual(events,[('open',False),('open',True),('close',True),('close',False)])
    def test_missing_memory_is_unknown_not_pressure(self):
        result=sustained([{'memory':[{'PagesInputPersec':50}], 'timestamp':1} for _ in range(3)])
        self.assertEqual(result['memory_coverage'],0)
        self.assertFalse(result['memory_pressure_candidate'])
    def test_cim_game_pid_handles_truncated_counter_name(self):
        sample={'timestamp':1,'game_pids':[42],'processes':[{'Name':'FortniteClient','IDProcess':42}],
                'gpu':[{'Name':'pid_42_engtype_3D','UtilizationPercentage':99}]}
        self.assertTrue(sustained([sample]*3)['gpu_busy_candidate'])

class AdvancedBenchmarkTests(unittest.TestCase):
    def run_result(self,ms):
        result=analyze([ms]*1000); result['context']='same route / hardware'; return result
    def test_repeated_metrics_and_interval(self):
        report=advanced_compare([self.run_result(10)]*3,[self.run_result(8)]*3,100)
        self.assertEqual(report['metrics']['average_fps']['delta'],25)
        self.assertTrue(report['metrics']['low_01']['interval_excludes_zero'])
        self.assertEqual(report['metrics']['p99_ms']['direction'],'lower is better')
    def test_equal_results_include_zero(self):
        report=advanced_compare([self.run_result(10)]*3,[self.run_result(10)]*3,100)
        self.assertFalse(report['metrics']['average_fps']['interval_excludes_zero'])
    def test_mismatched_context_rejected(self):
        before=[self.run_result(10)]*3; after=[self.run_result(9) for _ in range(3)]; after[0]['context']='other route'
        with self.assertRaises(ValueError): advanced_compare(before,after)
    def test_missing_context_rejected(self):
        result=self.run_result(10); result.pop('context')
        with self.assertRaises(ValueError): advanced_compare([result]*3,[result]*3)
    def test_low_sample_refused(self):
        with self.assertRaises(ValueError): advanced_compare([],[])
    def test_hardware_specific_guidance(self):
        result=recommendations({'gpu':[{'Name':'NVIDIA RTX','CurrentRefreshRate':60},{'Name':'Intel Graphics'}],'memory':{'totalMB':8192}})
        text=' '.join(result['recommendations'])
        self.assertIn('Reflex',text); self.assertIn('Multiple GPU',text); self.assertIn('Under 16',text)

if __name__=='__main__': unittest.main()
