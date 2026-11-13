import csv
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tweaker.engine import Engine
from tweaker.platform import MockBackend, WindowsBackend
from tweaker.benchmark import analyze, load_csv, compare
from tweaker.diagnostics import network

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.backend=MockBackend(); self.engine=Engine(self.backend,self.tmp.name)
    def test_roundtrip(self):
        original=self.backend.read('power')
        self.engine.apply('power.high')
        self.assertEqual(self.engine.records[0]['status'],'applied')
        self.engine.restore_all(); self.assertEqual(self.backend.read('power'),original)
    def test_restart_recovery(self):
        self.engine.apply('service.fax')
        record=self.engine.records[0]; record['status']='pending'; self.engine.save()
        Engine(self.backend,self.tmp.name).restore_all()
        self.assertEqual(self.backend.read('fax'),'Manual')
    def test_duplicate_refused(self):
        self.engine.apply('power.high')
        with self.assertRaises(RuntimeError): self.engine.apply('power.high')
    def test_external_conflict_preserved(self):
        self.engine.apply('power.high'); self.backend.values['power']='external'
        with self.assertRaises(RuntimeError): self.engine.restore_all()
        self.assertEqual(self.backend.read('power'),'external')
    def test_failed_write_journaled(self):
        with patch.object(self.backend,'write',side_effect=PermissionError('Denied')):
            with self.assertRaises(PermissionError): self.engine.apply('service.fax')
        self.assertEqual(self.engine.records[0]['status'],'recovery_required')
        self.engine.restore_all()
    def test_write_after_mutation_failure_recoverable(self):
        def fail(target,value): self.backend.values[target]=value; raise OSError('interrupted')
        with patch.object(self.backend,'write',side_effect=fail):
            with self.assertRaises(OSError): self.engine.apply('service.fax')
        self.engine.restore_all(); self.assertEqual(self.backend.read('fax'),'Manual')
    def test_preconfigured_no_journal(self):
        self.backend.values['fax']='Disabled'; self.engine.apply('service.fax')
        self.assertFalse(self.engine.records)
    def test_backup_failure_prevents_write(self):
        with patch.object(self.backend,'backup',side_effect=OSError('Disk full')):
            with self.assertRaises(OSError): self.engine.apply('power.high')
        self.assertFalse(self.engine.records)
        self.assertEqual(self.backend.read('power'),'381b4222-f694-41f0-9685-ff5bb260df2e')
    def test_verification_failure(self):
        with patch.object(self.backend,'write',return_value=None):
            with self.assertRaises(RuntimeError): self.engine.apply('service.fax')
        self.assertEqual(self.engine.records[0]['status'],'recovery_required')
    def test_journal_before_write(self):
        def write(target,value):
            fresh=Engine(self.backend,self.tmp.name)
            self.assertEqual(fresh.records[0]['status'],'pending')
            self.backend.values[target]=value
        with patch.object(self.backend,'write',side_effect=write): self.engine.apply('service.fax')

class BenchmarkTests(unittest.TestCase):
    def test_constant(self):
        result=analyze([10]*1000)
        self.assertEqual(result['average_fps'],100); self.assertEqual(result['low_01'],100)
        self.assertEqual(sum(result['histogram']),1000)
    def test_lows(self):
        result=analyze([10]*990+[100]*10)
        self.assertEqual(result['low_1'],10)
    def test_invalid(self):
        for values in [[10]*999, [float('nan')]*1000, [0]*1000, [-1]*1000, [float('inf')]*1000]:
            with self.assertRaises(ValueError): analyze(values)
    def test_variation_requires_repeats(self): self.assertIn('three',compare([],[]))
    def test_comparison(self):
        self.assertIn('exceeds',compare([{'average_fps':100}]*3,[{'average_fps':110}]*3))
    def test_mixed_stream_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'data.csv'; p.write_text('frametime_ms,ProcessID\n10,1\n10,2\n')
            with self.assertRaises(ValueError): load_csv(p)
    def test_import(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'data.csv'; p.write_text('frametime_ms\n'+'10\n'*1000)
            self.assertEqual(load_csv(p)['average_fps'],100)

class SafetyTests(unittest.TestCase):
    def test_network_injection_rejected(self):
        for host in ["x'; Stop-Service WinDefend; '",'a b','$(whoami)','-bad']:
            with self.assertRaises(ValueError): network(host)
    @patch('tweaker.platform.WINDOWS',False)
    def test_linux_write_refused(self):
        with self.assertRaises(RuntimeError): WindowsBackend().write('fax','Disabled')

class AnalysisTests(unittest.TestCase):
    def test_empty_sample_does_not_claim_health(self):
        from tweaker.analysis import interpret
        self.assertIn('does not establish',interpret({})['interpretation'][0])
    def test_memory_and_core_candidates(self):
        from tweaker.analysis import interpret
        result=interpret({'memory':{'AvailableMBytes':512,'PagesInputPersec':50},
                          'cpu':[{'Name':'0','PercentProcessorTime':98}]})
        self.assertEqual(len(result['interpretation']),2)
        self.assertIn('no causal',result['confidence'])
    def test_high_gpu_candidate(self):
        from tweaker.analysis import interpret
        result=interpret({'gpu':[{'UtilizationPercentage':99}]})
        self.assertIn('does not prove',result['interpretation'][0])

if __name__=='__main__': unittest.main()
